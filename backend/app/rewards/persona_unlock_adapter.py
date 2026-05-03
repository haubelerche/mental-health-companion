"""Bridge between reward store purchase and persona unlock state.

Called by purchase_service after a successful purchase. If the purchased item
carries an `unlocks_persona_id` metadata key, we upsert PersonaUnlockState.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.personas.unlocks import mark_persona_unlocked

logger = logging.getLogger(__name__)


def maybe_unlock_persona(
    db: Session,
    *,
    user_id: str,
    item_def: dict[str, Any],
) -> str | None:
    """If item unlocks a persona, record the unlock and return the persona_id."""
    persona_id = (item_def.get("metadata") or {}).get("unlocks_persona_id")
    if not persona_id:
        return None
    mark_persona_unlocked(db, user_id=user_id, persona_id=persona_id, source="purchase")
    logger.info("[PersonaUnlockAdapter] user=%s persona=%s unlocked via purchase", user_id, persona_id)
    return persona_id
