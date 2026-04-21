"""Session end: summary + profile FIFO + outbox (BACKEND_PLAN §6.2) — minimal implementation."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Conversation, Message, SyncOutbox, UserProfile
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.utils import make_id, utc_now

logger = logging.getLogger(__name__)


def _trim_fifo_summaries(profile: dict, text: str, max_items: int = 50) -> None:
    summaries = list(profile.get("session_summaries") or [])
    summaries.append({"text": text, "at": utc_now().isoformat()})
    profile["session_summaries"] = summaries[-max_items:]


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
