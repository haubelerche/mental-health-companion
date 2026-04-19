"""
Chat gateway context: recent messages + mood today (BACKEND_PLAN §3.3).
Sequential reads on the same SQLAlchemy Session (thread-safe).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Message, MoodCheckin
from app.services.utils import local_date_utc7


@dataclass
class ChatTurnContext:
    recent_messages: list[dict[str, Any]]
    mood_today: dict[str, Any] | None


def _fetch_recent_messages_sync(db: Session, session_id: str, user_id: str, limit: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id, Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).all()
    rows = list(reversed(rows))
    return [
        {
            "role": m.role,
            "content": m.content,
            "sos_triggered": m.sos_triggered,
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in rows
    ]


def _fetch_mood_today_sync(db: Session, user_id: str) -> dict[str, Any] | None:
    today = local_date_utc7()
    row = db.scalar(
        select(MoodCheckin).where(MoodCheckin.user_id == user_id, MoodCheckin.logged_date == today)
    )
    if not row:
        return None
    return {"mood": row.mood, "emoji": row.emoji, "note": row.note}


def load_chat_context_sync(
    db: Session,
    *,
    session_id: str,
    user_id: str,
    message_limit: int = 8,
) -> ChatTurnContext:
    return ChatTurnContext(
        recent_messages=_fetch_recent_messages_sync(db, session_id, user_id, message_limit),
        mood_today=_fetch_mood_today_sync(db, user_id),
    )
