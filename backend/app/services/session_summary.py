"""Session end: summary + profile FIFO + outbox (BACKEND_PLAN §6.2) — minimal implementation."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta

DEDUP_WINDOW_HOURS = 24

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.db.models import Conversation, Message, SyncOutbox, UserProfile
from app.services.mem0_service import MemoryManager
from app.memory.extractor import extract_memory_candidates
from app.memory.service import create_cards_from_candidates
from app.services.memory_enrichment import StructuredExtract, apply_to_profile, extract_structured
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.utils import get_now

logger = logging.getLogger(__name__)


def _emit_memory_outbox_events(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    extract: StructuredExtract,
) -> None:
    for trigger in extract.key_triggers:
        db.add(
            SyncOutbox(
                user_id=user_id,
                event_type="trigger.observed",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "trigger_label": trigger,
                    "emotion_label": extract.dominant_emotion,
                },
                status="pending",
            )
        )
    for action in extract.coping_attempts:
        db.add(
            SyncOutbox(
                user_id=user_id,
                event_type="coping.attempted",
                payload={
                    "user_id": user_id,
                    "session_id": session_id,
                    "coping_action": action,
                },
                status="pending",
            )
        )


def _enqueue_mem0_add(user_id: str, messages: list[dict[str, str]]) -> None:
    try:
        MemoryManager.instance().add_session(user_id=user_id, messages=messages)
    except Exception as exc:  # pragma: no cover
        logger.warning("mem0 background add failed for %s: %s", user_id, exc)


def _summarize_session_key_points(transcript: str) -> str:
    """Return a concise Vietnamese summary (<=500 chars), fallback to truncation."""
    cleaned = str(transcript or "").strip()
    if not cleaned:
        return "Phiên trò chuyện đã kết thúc."

    settings = get_settings()
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 8.0))
            resp = client.chat.completions.create(
                model=settings.openai_model_analyst,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn tóm tắt cuộc trò chuyện trị liệu bằng tiếng Việt, tối đa 500 ký tự. "
                            "Chỉ nêu ý chính: cảm xúc nổi bật, tác nhân gây căng thẳng, và bước đối phó đã nói tới. "
                            "Không nêu thông tin định danh."
                        ),
                    },
                    {"role": "user", "content": cleaned[:3000]},
                ],
            )
            summary = str(resp.choices[0].message.content or "").strip()
            if summary:
                return summary[:500]
        except Exception as exc:
            logger.warning("session summary llm failed: %s", exc)

    fallback = cleaned[:500]
    return (fallback[:497] + "...") if len(fallback) > 500 else fallback


def close_session_summary(db: Session, *, session: Conversation, user_id: str) -> str:
    """Mark session summarized, append profile + outbox + optional memory row."""
    if session.summarized_at is not None:
        return ""

    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session.session_id)
        .order_by(Message.created_at.asc())
    ).all()
    parts = [f"{m.role}: {m.content}" for m in rows[-40:]]
    blob = mask_pii("\n".join(parts))[:3500]
    summary_text = _summarize_session_key_points(blob)
    if not summary_text.strip():
        summary_text = "Phiên trò chuyện đã kết thúc."
    had_sos = any(bool(m.sos_triggered) for m in rows)
    turn_count = len(rows)

    now = get_now().replace(tzinfo=None)
    cutoff = (get_now() - timedelta(hours=DEDUP_WINDOW_HOURS)).replace(tzinfo=None)
    session.summarized_at = now

    prof = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not prof:
        prof = UserProfile(user_id=user_id, profile={})
        db.add(prof)
        db.flush()
    data = dict(prof.profile or {})
    settings = get_settings()
    extract = extract_structured(blob, settings, sos_triggered=had_sos)
    data = apply_to_profile(
        data,
        extract=extract,
        session_meta={
            "session_id": session.session_id,
            "started_at": session.started_at.isoformat() if session.started_at else now.isoformat(),
            "ended_at": now.isoformat(),
            "turn_count": turn_count,
            "crisis_level_peak": 5 if had_sos else 0,
        },
        summary_text=summary_text,
    )
    meta = dict(data.get("meta") or {})
    meta["weekly_note_generated_at"] = None
    meta["weekly_note_content"] = None
    data["meta"] = meta
    prof.profile = data
    prof.updated_at = now

    db.add(
        SyncOutbox(
            user_id=user_id,
            event_type="session.ended",
            payload={
                "user_id": user_id,
                "session_id": session.session_id,
                "ended_at": now.isoformat(),
                "dominant_emotion": extract.dominant_emotion,
                "key_triggers": extract.key_triggers,
                "sos_triggered": had_sos,
            },
            status="pending",
        )
    )
    _emit_memory_outbox_events(
        db,
        user_id=user_id,
        session_id=session.session_id,
        extract=extract,
    )
    try:
        card_extraction = extract_memory_candidates(blob, session_id=session.session_id)
        create_cards_from_candidates(db, user_id, card_extraction)
    except Exception as exc:
        logger.warning("memory card extraction at session close failed for %s: %s", user_id, exc)
    cache_delete(profile_cache_key(user_id))
    db.commit()
    mem0_messages = [{"role": str(m.role), "content": str(m.content)} for m in rows[-40:]]
    threading.Thread(target=_enqueue_mem0_add, args=(user_id, mem0_messages), daemon=True).start()
    return summary_text
