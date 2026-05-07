"""Persona unlock state persistence (canonical module).

`PersonaUnlockState` rows are created lazily per user per unlockable persona.
Reward purchase flow imports from here so it does not depend on `app.personas.*`
package wiring. `app.personas.unlocks` re-exports the same API for persona code.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import PersonaUnlockState
from app.services.utils import utc_now

logger = logging.getLogger(__name__)

UNLOCKABLE_PERSONAS = ("cun", "meo", "crush")


def get_persona_unlock_state(
    db: Session, *, user_id: str, persona_id: str
) -> PersonaUnlockState | None:
    return db.scalar(
        select(PersonaUnlockState).where(
            PersonaUnlockState.user_id == user_id,
            PersonaUnlockState.persona_id == persona_id,
        )
    )


def is_persona_unlocked(db: Session, *, user_id: str, persona_id: str) -> bool:
    """Return True if the user has unlocked this persona (or it's a core persona)."""
    if persona_id not in UNLOCKABLE_PERSONAS:
        return True
    state = get_persona_unlock_state(db, user_id=user_id, persona_id=persona_id)
    return bool(state and state.unlocked)


def mark_persona_unlocked(
    db: Session,
    *,
    user_id: str,
    persona_id: str,
    source: str = "purchase",
    extra: dict[str, Any] | None = None,
) -> PersonaUnlockState:
    state = get_persona_unlock_state(db, user_id=user_id, persona_id=persona_id)
    now = utc_now().replace(tzinfo=None)
    if state is None:
        state = PersonaUnlockState(
            user_id=user_id,
            persona_id=persona_id,
            unlocked=True,
            unlocked_at=now,
            unlock_source=source,
            progress=extra or {},
        )
        db.add(state)
    else:
        state.unlocked = True
        state.unlocked_at = now
        state.unlock_source = source
        state.updated_at = now
    db.flush()
    logger.info("[Unlocks] user=%s persona=%s source=%s", user_id, persona_id, source)
    # Push real-time notification
    try:
        from app.services.notification_service import enqueue_notification
        enqueue_notification(
            db,
            user_id=user_id,
            event_type="persona.unlocked",
            payload={
                "persona_id": persona_id,
                "message": f"Chúc mừng! Bạn đã mở khóa thành công nhân vật mới: {persona_id.upper()}",
                "source": source
            }
        )
    except Exception:
        pass
    return state


def accept_crush_boundary(db: Session, *, user_id: str) -> PersonaUnlockState:
    """Record boundary intro acceptance for Crush. Required before Crush can activate."""
    state = get_persona_unlock_state(db, user_id=user_id, persona_id="crush")
    now = utc_now().replace(tzinfo=None)
    if state is None:
        state = PersonaUnlockState(
            user_id=user_id,
            persona_id="crush",
            unlocked=False,
            boundary_accepted=True,
            updated_at=now,
        )
        db.add(state)
    else:
        state.boundary_accepted = True
        state.updated_at = now
    db.flush()
    logger.info("[Unlocks] Crush boundary accepted user=%s", user_id)
    return state
