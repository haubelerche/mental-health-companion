"""Session end: summary + profile FIFO + outbox (BACKEND_PLAN §6.2) — minimal implementation."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta

DEDUP_WINDOW_HOURS = 24

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.db.models import Conversation, Message, UserProfile
from app.services.mem0_service import MemoryManager
from app.services.memory_enrichment import StructuredExtract, apply_to_profile, extract_structured
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.analyst_writer import record_analyst_signal, upsert_insight_hypothesis
from app.services.utils import get_now

logger = logging.getLogger(__name__)


def _emit_memory_outbox_events(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    extract: StructuredExtract,
) -> None:
    _ = db, user_id, session_id, extract
    # MVP boundary: user-derived trigger/coping patterns stay in PostgreSQL
    # profile rollups and memory tables. Neo4j user-pattern sync is deferred
    # until a validator-backed aggregate graph is introduced.
    return None


def _enqueue_mem0_add(user_id: str, messages: list[dict[str, str]]) -> None:
    try:
        MemoryManager.instance().add_session(user_id=user_id, messages=messages)
    except Exception as exc:  # pragma: no cover
        logger.warning("mem0 background add failed for %s: %s", user_id, exc)


def _summarize_session_key_points(transcript: str) -> str:
    """Return a concise insight summary in Vietnamese (<=700 chars)."""
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
                            "Bạn tạo session summary chất lượng cao bằng tiếng Việt, ngắn gọn nhưng có insight. "
                            "Bắt buộc đúng 4 dòng, mỗi dòng bắt đầu bằng nhãn sau: "
                            "1) Tín hiệu cảm xúc:, 2) Tác nhân chính:, 3) Cơ chế đối phó hiện tại:, 4) Gợi ý hành động kế tiếp:. "
                            "Mỗi dòng tối đa 180 ký tự, không nêu thông tin định danh cá nhân."
                        ),
                    },
                    {"role": "user", "content": cleaned[:3000]},
                ],
            )
            summary = str(resp.choices[0].message.content or "").strip()
            if summary:
                return summary[:700]
        except Exception as exc:
            logger.warning("session summary llm failed: %s", exc)

    compact = cleaned.replace("\n", " ").strip()
    if not compact:
        return "Phiên trò chuyện đã kết thúc."
    snippet = (compact[:220] + "...") if len(compact) > 223 else compact
    return (
        f"Tín hiệu cảm xúc: {snippet}\n"
        "Tác nhân chính: Chưa tách được rõ từ dữ liệu hiện có.\n"
        "Cơ chế đối phó hiện tại: Người dùng đang thử chia sẻ và tìm điểm tựa hội thoại.\n"
        "Gợi ý hành động kế tiếp: Tiếp tục theo dõi mẫu căng thẳng và chốt 1 bước nhỏ có thể làm ngay."
    )[:700]


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

    _emit_memory_outbox_events(
        db,
        user_id=user_id,
        session_id=session.session_id,
        extract=extract,
    )
    try:
        sig_id = record_analyst_signal(
            db,
            user_id=user_id,
            session_id=session.session_id,
            extract=extract,
        )
        upsert_insight_hypothesis(
            db,
            user_id=user_id,
            extract=extract,
            signal_id=sig_id,
            session_id=session.session_id,
        )
    except Exception as exc:
        logger.warning("analyst pipeline at session close failed for %s: %s", user_id, exc)

    cache_delete(profile_cache_key(user_id))
    db.commit()
    mem0_messages = [{"role": str(m.role), "content": mask_pii(str(m.content))} for m in rows[-40:]]
    threading.Thread(target=_enqueue_mem0_add, args=(user_id, mem0_messages), daemon=True).start()
    return summary_text
