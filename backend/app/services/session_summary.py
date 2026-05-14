"""Session summary compatibility layer.

The canonical implementation lives in SessionLifecycleService, but several
runtime and regression paths still patch the historical functions in this
module. Keep those symbols available while preserving the current PostgreSQL
boundary: no user graph events are emitted from session close.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.analyst_writer import record_analyst_signal, upsert_insight_hypothesis
from app.services.db.models import Conversation, Message, UserProfile
from app.services.mem0_service import MemoryManager
from app.services.memory_enrichment import apply_to_profile, extract_structured
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.session_lifecycle import SessionLifecycleService
from app.services.utils import get_now

logger = logging.getLogger(__name__)


def _summarize_session_key_points(transcript: str) -> str:
    cleaned = " ".join(str(transcript or "").split()).strip()
    if not cleaned:
        return "Phiên trò chuyện đã kết thúc."
    snippet = (cleaned[:220] + "...") if len(cleaned) > 223 else cleaned
    return (
        f"Tín hiệu cảm xúc: {snippet}\n"
        "Tác nhân chính: Chưa tách được rõ từ dữ liệu hiện có.\n"
        "Cơ chế đối phó hiện tại: Người dùng đang thử chia sẻ và tìm điểm tựa hội thoại.\n"
        "Gợi ý hành động kế tiếp: Tiếp tục theo dõi mẫu căng thẳng và chốt 1 bước nhỏ có thể làm ngay."
    )[:700]


def ensure_session_summary_memory(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    summary_text: str,
    created_at,
) -> str:
    """Compatibility hook for session-summary-to-memory backfill.

    Tests and older integrations monkeypatch this function. The default
    implementation intentionally does not create graph/outbox data; canonical
    user-visible cards are handled by SessionLifecycleService.
    """
    _ = db, summary_text, created_at
    return f"session-summary:{user_id}:{session_id}"


def _summary_from_profile(profile: dict | None, session_id: str) -> str:
    for item in reversed(list((profile or {}).get("session_summaries") or [])):
        if not isinstance(item, dict):
            continue
        if str(item.get("session_id") or "") != session_id:
            continue
        summary = str(item.get("summary") or item.get("text") or "").strip()
        if summary:
            return summary[:700]
    return ""


def _enqueue_mem0_add(user_id: str, messages: list[dict[str, str]]) -> None:
    try:
        MemoryManager.instance().add_session(user_id=user_id, messages=messages)
    except Exception as exc:  # pragma: no cover
        logger.warning("mem0 background add failed for %s: %s", user_id, exc)


def close_session_summary(db: Session, *, session: Conversation, user_id: str) -> str:
    """Close a chat session and return its summary text.

    Canonical persistence is handled by SessionLifecycleService:
    session_summaries_archive for durable summary and memory_cards for
    user-facing reviewable memories. Mem0 is only an optional derived cache.
    """
    try:
        result = SessionLifecycleService(db).close_session(
            user_id=user_id,
            session_id=session.session_id,
            reason="explicit_end",
        )
        return result.summary
    except Exception as exc:
        logger.debug("canonical session close unavailable, using compatibility path: %s", exc)

    rows = list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session.session_id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    prof = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data = dict(prof.profile or {}) if prof else {}
    blob = mask_pii("\n".join(f"{m.role}: {m.content}" for m in rows[-40:]))[:3500]
    summary_text = _summary_from_profile(profile_data, session.session_id) or _summarize_session_key_points(blob)
    if not summary_text.strip():
        summary_text = "Phiên trò chuyện đã kết thúc."

    now = get_now().replace(tzinfo=None)
    if session.summarized_at is None:
        session.summarized_at = now
        if prof is None:
            prof = UserProfile(user_id=user_id, profile={})
            db.add(prof)
            db.flush()
        settings = get_settings()
        extract = extract_structured(blob, settings, sos_triggered=any(bool(m.sos_triggered) for m in rows))
        try:
            prof.profile = apply_to_profile(
                dict(prof.profile or {}),
                extract=extract,
                session_meta={
                    "session_id": session.session_id,
                    "started_at": session.started_at.isoformat() if session.started_at else now.isoformat(),
                    "ended_at": now.isoformat(),
                    "turn_count": len(rows),
                    "crisis_level_peak": 5 if any(bool(m.sos_triggered) for m in rows) else 0,
                },
                summary_text=summary_text,
            )
            prof.updated_at = now
            sig_id = record_analyst_signal(db, user_id=user_id, session_id=session.session_id, extract=extract)
            upsert_insight_hypothesis(db, user_id=user_id, extract=extract, signal_id=sig_id, session_id=session.session_id)
        except Exception as profile_exc:
            logger.debug("compat session enrichment skipped: %s", profile_exc)
        cache_delete(profile_cache_key(user_id))
        db.commit()

    ensure_session_summary_memory(
        db,
        user_id=user_id,
        session_id=session.session_id,
        summary_text=summary_text,
        created_at=now,
    )
    mem0_messages = [{"role": str(m.role), "content": mask_pii(str(m.content))} for m in rows[-40:]]
    threading.Thread(target=_enqueue_mem0_add, args=(user_id, mem0_messages), daemon=True).start()
    return summary_text
