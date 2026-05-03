"""Atomic purchase transaction service.

Algorithm (plan §11.5):
  1. Authenticate (handled by caller via Depends)
  2. Load catalog item — reject if inactive or unknown
  3. Validate requirements and safety pre-checks
  4. Lock wallet row (SELECT ... FOR UPDATE equivalent)
  5. Reject if insufficient balance
  6. Reject if inventory already owned
  7. Insert spend event (idempotency key)
  8. Decrement wallet balance
  9. Create user_inventory_items row
  10. Update persona_unlock_states if item unlocks a persona
  11. Return result
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.rewards.catalog import CATALOG_BY_ID
from app.services.db.models import HeartSpendEvent, HeartWallet, UserInventoryItem
from app.services.utils import make_id, utc_now

logger = logging.getLogger(__name__)


class PurchaseError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = status


def purchase_item(
    db: Session,
    *,
    user_id: str,
    item_id: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Purchase an item atomically. Raises PurchaseError on business-rule violations."""
    item_def = CATALOG_BY_ID.get(item_id)
    if not item_def:
        raise PurchaseError("item_not_found", f"Unknown item: {item_id}", 404)

    idem_key = idempotency_key or f"purchase:{user_id}:{item_id}"

    existing_spend = db.scalar(
        select(HeartSpendEvent).where(HeartSpendEvent.idempotency_key == idem_key)
    )
    if existing_spend:
        inv = db.scalar(
            select(UserInventoryItem).where(
                UserInventoryItem.user_id == user_id,
                UserInventoryItem.item_id == item_id,
            )
        )
        wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
        return {
            "idempotent": True,
            "item_id": item_id,
            "new_balance": wallet.balance if wallet else 0,
            "inventory_id": inv.inventory_id if inv else None,
        }

    wallet = db.scalar(
        select(HeartWallet).where(HeartWallet.user_id == user_id).with_for_update()
    )
    if wallet is None:
        raise PurchaseError("insufficient_hearts", "Không đủ Tim để mua", 402)

    price = item_def["price_hearts"]
    if wallet.balance < price:
        raise PurchaseError(
            "insufficient_hearts",
            f"Không đủ Tim. Cần {price}, hiện có {wallet.balance}.",
            402,
        )

    existing_inv = db.scalar(
        select(UserInventoryItem).where(
            UserInventoryItem.user_id == user_id,
            UserInventoryItem.item_id == item_id,
        )
    )
    if existing_inv:
        raise PurchaseError("already_owned", "Bạn đã sở hữu item này rồi.", 409)

    spend = HeartSpendEvent(
        event_id=make_id("hse"),
        user_id=user_id,
        item_id=item_id,
        amount=price,
        idempotency_key=idem_key,
        status="spent",
        metadata_json={"item_type": item_def.get("item_type")},
    )
    db.add(spend)
    db.flush()

    wallet.balance -= price
    wallet.lifetime_spent += price
    wallet.updated_at = utc_now().replace(tzinfo=None)

    inv = UserInventoryItem(
        inventory_id=make_id("inv"),
        user_id=user_id,
        item_id=item_id,
        acquired_source="purchase",
        spend_event_id=spend.event_id,
        metadata_json={},
    )
    db.add(inv)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise PurchaseError("already_owned", "Bạn đã sở hữu item này rồi.", 409)

    logger.info(
        "[PurchaseService] user=%s item=%s price=%d new_balance=%d",
        user_id, item_id, price, wallet.balance,
    )

    from app.rewards.persona_unlock_adapter import maybe_unlock_persona
    persona_unlocked = maybe_unlock_persona(db, user_id=user_id, item_def=item_def)

    return {
        "idempotent": False,
        "item_id": item_id,
        "new_balance": wallet.balance,
        "inventory_id": inv.inventory_id,
        "persona_unlocked": persona_unlocked,
    }
