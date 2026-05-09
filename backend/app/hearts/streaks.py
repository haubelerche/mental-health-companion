"""Mood check-in streak engine. Updates streak state and triggers 7-day bonus.

PRD §10.2: 7-day mood check-in streak → +20 Tim, once per completed 7-day block.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hearts.service import grant_hearts
from app.services.db.models import StreakState
from app.services.utils import get_now

logger = logging.getLogger(__name__)

_STREAK_BONUS_HEARTS = 20
_STREAK_BONUS_INTERVAL = 7


def _get_or_create_streak(db: Session, user_id: str) -> StreakState:
    streak = db.scalar(select(StreakState).where(StreakState.user_id == user_id))
    if streak is None:
        streak = StreakState(user_id=user_id)
        db.add(streak)
        db.flush()
    return streak


def update_mood_streak(db: Session, *, user_id: str, checkin_date: date) -> dict[str, Any]:
    """Update streak counter for a mood check-in. Returns streak + bonus info.

    A streak is maintained when consecutive daily check-ins occur (no gap > 1 day).
    The 7-day bonus fires once per completed 7-day block.
    """
    streak = _get_or_create_streak(db, user_id)

    if streak.last_mood_checkin_date == checkin_date:
        return {
            "current": streak.current_mood_checkin_streak,
            "bonus_granted": False,
            "bonus_amount": 0,
        }

    yesterday = checkin_date - timedelta(days=1)
    if streak.last_mood_checkin_date == yesterday:
        streak.current_mood_checkin_streak += 1
    else:
        streak.current_mood_checkin_streak = 1

    streak.last_mood_checkin_date = checkin_date
    if streak.current_mood_checkin_streak > streak.longest_mood_checkin_streak:
        streak.longest_mood_checkin_streak = streak.current_mood_checkin_streak
    streak.updated_at = get_now().replace(tzinfo=None)
    db.flush()

    bonus_granted = False
    bonus_amount = 0
    if streak.current_mood_checkin_streak % _STREAK_BONUS_INTERVAL == 0:
        block_number = streak.current_mood_checkin_streak // _STREAK_BONUS_INTERVAL
        idem_key = f"streak_7d:{user_id}:{checkin_date.isoformat()}:block{block_number}"
        result = grant_hearts(
            db,
            user_id=user_id,
            amount=_STREAK_BONUS_HEARTS,
            event_type="mood_streak_7day_bonus",
            source_tab="checkin",
            idempotency_key=idem_key,
            metadata={"streak_block": block_number, "streak_length": streak.current_mood_checkin_streak},
        )
        bonus_granted = result["granted"]
        bonus_amount = _STREAK_BONUS_HEARTS if bonus_granted else 0
        logger.info(
            "[StreakEngine] 7-day bonus user=%s block=%d granted=%s",
            user_id, block_number, bonus_granted,
        )

    return {
        "current": streak.current_mood_checkin_streak,
        "bonus_granted": bonus_granted,
        "bonus_amount": bonus_amount,
    }
