"""Unlock requirement progress aggregation.

Reads from mood_checkins and persona_unlock_states to compute how close a user
is to meeting the unlock requirements for each persona.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.personas.unlocks import UNLOCKABLE_PERSONAS, get_persona_unlock_state
from app.rewards.catalog import CATALOG_BY_ID
from app.services.db.models import MoodCheckin

# Core personas are always available; this module historically only listed UNLOCKABLE_PERSONAS.
CORE_PERSONA_IDS: tuple[str, ...] = ("ban_than", "nguoi_thay")


def _count_mood_checkins(db: Session, user_id: str) -> int:
    return (
        db.scalar(
            select(func.count(MoodCheckin.checkin_id)).where(
                MoodCheckin.user_id == user_id
            )
        )
        or 0
    )


def get_unlock_progress(
    db: Session, *, user_id: str, persona_id: str
) -> dict[str, Any]:
    """Return progress and requirements for a locked persona card."""
    item_id = f"persona_{persona_id}"
    item_def = CATALOG_BY_ID.get(item_id)
    if not item_def:
        return {
            "persona_id": persona_id,
            "unlocked": False,
            "is_core": False,
            "price_hearts": 0,
            "progress": {},
            "requirements": {},
        }

    requirements: dict[str, Any] = item_def.get("requirements", {})
    state = get_persona_unlock_state(db, user_id=user_id, persona_id=persona_id)
    unlocked = bool(state and state.unlocked)
    boundary_accepted = bool(state and state.boundary_accepted)

    mood_count = _count_mood_checkins(db, user_id) if requirements.get("mood_checkins_min") else 0

    progress: dict[str, Any] = {}
    if "mood_checkins_min" in requirements:
        progress["mood_checkins"] = {
            "current": mood_count,
            "required": requirements["mood_checkins_min"],
            "met": mood_count >= requirements["mood_checkins_min"],
        }
    if requirements.get("boundary_intro_accepted"):
        progress["boundary_accepted"] = {
            "current": boundary_accepted,
            "required": True,
            "met": boundary_accepted,
        }

    return {
        "persona_id": persona_id,
        "unlocked": unlocked,
        "is_core": False,
        "price_hearts": item_def.get("price_hearts"),
        "progress": progress,
        "requirements": requirements,
    }


def _core_persona_row(persona_id: str) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "unlocked": True,
        "is_core": True,
        "price_hearts": 0,
        "progress": {},
        "requirements": {},
    }


def get_all_unlock_progress(db: Session, *, user_id: str) -> list[dict[str, Any]]:
    core_rows = [_core_persona_row(pid) for pid in CORE_PERSONA_IDS]
    unlock_rows = [
        get_unlock_progress(db, user_id=user_id, persona_id=pid) for pid in UNLOCKABLE_PERSONAS
    ]
    return core_rows + unlock_rows
