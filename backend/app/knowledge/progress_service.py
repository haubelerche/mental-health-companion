"""Knowledge unlock progress service — Plan 07.

Tracks which cards a user has completed and issues +15 Tim reward (once per card).
Pack access is determined by:
  1. pack.price_hearts is None → free for all users.
  2. pack.required_item_id is not None → user must have that item in inventory.
  3. pack.price_hearts is set and required_item_id is None → user must have purchased
     via reward store (inventory row present for the linked item or pack itself).

Completion reward: idempotency_key = "knowledge_card:{user_id}:{card_id}"
                   amount = 15 Tim, once per user per card.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hearts.service import grant_hearts
from app.services.db.models import (
    KnowledgeCard,
    KnowledgePack,
    UserInventoryItem,
    UserKnowledgeProgress,
)

CARD_COMPLETION_HEARTS = 15
_COMPLETION_EVENT_TYPE = "knowledge_card_completed"
_SOURCE_TAB = "knowledge"


def _idempotency_key(user_id: str, card_id: str) -> str:
    return f"knowledge_card:{user_id}:{card_id}"


def _get_pack_db(db: Session, pack_id: str) -> KnowledgePack | None:
    return db.scalar(select(KnowledgePack).where(KnowledgePack.pack_id == pack_id))


def _get_card_db(db: Session, card_id: str) -> KnowledgeCard | None:
    return db.scalar(select(KnowledgeCard).where(KnowledgeCard.card_id == card_id))


# ---------------------------------------------------------------------------
# Access check
# ---------------------------------------------------------------------------

def has_pack_access(db: Session, user_id: str, pack_id: str) -> bool:
    """Return True if the user may read this pack's cards.

    Checks DB for pack definition (not the static catalog).
    Free packs (price_hearts IS NULL) are always accessible.
    Paid packs require an inventory row for required_item_id or pack_id.
    """
    pack = _get_pack_db(db, pack_id)
    if pack is None:
        return False

    # Free pack — always accessible
    if pack.price_hearts is None:
        return True

    # Paid pack: check inventory for required_item_id or pack_id slug
    required_item_id = pack.required_item_id or pack_id
    row = db.scalar(
        select(UserInventoryItem).where(
            UserInventoryItem.user_id == user_id,
            UserInventoryItem.item_id == required_item_id,
        )
    )
    return row is not None


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def complete_card(
    db: Session,
    user_id: str,
    card_id: str,
) -> dict[str, Any]:
    """Mark a knowledge card as completed; grant +15 Tim once.

    Returns dict with: already_completed (bool), reward (grant_hearts result | None).
    Raises ValueError if card_id is not found in DB,
    or if user does not have access to the pack.
    """
    card = _get_card_db(db, card_id)
    if card is None:
        raise ValueError(f"unknown card_id: {card_id}")

    pack_id = card.pack_id
    if not has_pack_access(db, user_id, pack_id):
        raise ValueError(f"user does not have access to pack: {pack_id}")

    existing = db.scalar(
        select(UserKnowledgeProgress).where(
            UserKnowledgeProgress.user_id == user_id,
            UserKnowledgeProgress.card_id == card_id,
        )
    )
    if existing:
        return {"already_completed": True, "reward": None}

    reward = grant_hearts(
        db,
        user_id=user_id,
        amount=CARD_COMPLETION_HEARTS,
        event_type=_COMPLETION_EVENT_TYPE,
        source_tab=_SOURCE_TAB,
        idempotency_key=_idempotency_key(user_id, card_id),
        metadata={"card_id": card_id, "pack_id": pack_id},
    )

    progress = UserKnowledgeProgress(
        progress_id=f"kp_{uuid.uuid4().hex[:16]}",
        user_id=user_id,
        pack_id=pack_id,
        card_id=card_id,
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        reward_event_id=reward.get("event_id"),
    )
    db.add(progress)
    db.flush()

    return {"already_completed": False, "reward": reward}


# ---------------------------------------------------------------------------
# Progress listing
# ---------------------------------------------------------------------------

def get_user_progress(db: Session, user_id: str) -> list[dict[str, Any]]:
    """Return all completed cards for a user."""
    rows = db.scalars(
        select(UserKnowledgeProgress).where(UserKnowledgeProgress.user_id == user_id)
    ).all()
    return [
        {
            "pack_id": r.pack_id,
            "card_id": r.card_id,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]
