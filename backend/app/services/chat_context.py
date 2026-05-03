"""
Chat gateway context: recent messages + mood today (BACKEND_PLAN §3.3).
Sequential reads on the same SQLAlchemy Session (thread-safe).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import Message, MoodCheckin
from app.services.utils import local_date_utc7


@dataclass
class ChatTurnContext:
    recent_messages: list[dict[str, Any]]
    mood_today: dict[str, Any] | None


def _estimate_tokens_fast(text: str) -> int:
    # Keep aligned with chat pipeline estimation (mixed vi/en).
    return max(1, int(len(text or "") / 2.5))


def _apply_recent_message_token_guard(
    messages: list[dict[str, Any]],
    *,
    token_budget: int,
    min_messages: int = 4,
) -> list[dict[str, Any]]:
    """Trim oldest turns when recent transcript exceeds token budget.

    Keeps newest messages first by importance for continuity.
    """
    if token_budget <= 0 or not messages:
        return messages

    total = 0
    kept_reversed: list[dict[str, Any]] = []
    # Iterate newest -> oldest so we always preserve latest context.
    for turn in reversed(messages):
        role = str(turn.get("role") or "")
        content = str(turn.get("content") or "")
        turn_tokens = _estimate_tokens_fast(role) + _estimate_tokens_fast(content)

        # Always keep a minimum tail window for continuity.
        if len(kept_reversed) < min_messages:
            kept_reversed.append(turn)
            total += turn_tokens
            continue

        if total + turn_tokens > token_budget:
            break
        kept_reversed.append(turn)
        total += turn_tokens

    return list(reversed(kept_reversed))


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
    message_token_budget: int = 1400,
) -> ChatTurnContext:
    recent_messages = _fetch_recent_messages_sync(db, session_id, user_id, message_limit)
    return ChatTurnContext(
        recent_messages=_apply_recent_message_token_guard(
            recent_messages,
            token_budget=message_token_budget,
        ),
        mood_today=_fetch_mood_today_sync(db, user_id),
    )
