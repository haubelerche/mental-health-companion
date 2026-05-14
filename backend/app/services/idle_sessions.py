"""Idle 30m session summarizer hook (BACKEND_PLAN §4.4)."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import Conversation
from app.services.db.session import get_session_factory
from app.services.session_lifecycle import SessionLifecycleService
from app.services.utils import get_now

logger = logging.getLogger(__name__)

IDLE_MINUTES = 30


def summarize_idle_sessions() -> int:
    """Return count of sessions summarized."""
    factory = get_session_factory()
    cutoff = get_now().replace(tzinfo=None) - timedelta(minutes=IDLE_MINUTES)
    db: Session = factory()
    try:
        rows = db.scalars(
            select(Conversation).where(
                Conversation.deleted_at.is_(None),
                Conversation.summarized_at.is_(None),
                Conversation.last_message_at < cutoff,
                Conversation.message_count > 0,
            )
        ).all()
        targets = [(r.session_id, r.user_id) for r in rows]
    finally:
        db.close()

    n = 0
    if targets:
        db2: Session = factory()
        try:
            for session_id, user_id in targets:
                try:
                    conv = db2.scalar(select(Conversation).where(Conversation.session_id == session_id))
                    if conv and conv.summarized_at is None:
                        SessionLifecycleService(db2).close_session(
                            user_id=user_id,
                            session_id=session_id,
                            reason="idle_timeout",
                        )
                        n += 1
                except Exception as exc:
                    db2.rollback()
                    logger.warning("idle summarize failed %s: %s", session_id, exc)
        finally:
            db2.close()
    return n
