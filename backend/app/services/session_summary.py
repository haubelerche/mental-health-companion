"""Session end: summary + profile FIFO + outbox (BACKEND_PLAN §6.2) — minimal implementation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, SyncOutbox, UserProfile
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.utils import make_id, utc_now


def _trim_fifo_summaries(profile: dict, text: str, max_items: int = 50) -> None:
    summaries = list(profile.get("session_summaries") or [])
    summaries.append({"text": text, "at": utc_now().isoformat()})
    profile["session_summaries"] = summaries[-max_items:]


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
    blob = mask_pii("\n".join(parts))[:2000]
    summary_text = (blob[:497] + "...") if len(blob) > 500 else blob
    if not summary_text.strip():
        summary_text = "Phiên trò chuyện đã kết thúc."

    now = utc_now().replace(tzinfo=None)
    session.summarized_at = now

    prof = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not prof:
        prof = UserProfile(user_id=user_id, profile={})
        db.add(prof)
        db.flush()
    data = dict(prof.profile or {})
    _trim_fifo_summaries(data, summary_text)
    prof.profile = data
    prof.updated_at = now

    db.add(
        SyncOutbox(
            event_type="session.ended",
            payload={"user_id": user_id, "session_id": session.session_id},
            status="pending",
        )
    )
    cache_delete(profile_cache_key(user_id))
    db.commit()
    return summary_text
