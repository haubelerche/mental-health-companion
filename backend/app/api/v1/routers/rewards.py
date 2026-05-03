"""Reward store routes.

GET  /rewards/store           → backend-driven catalog grouped by shelf
GET  /rewards/balance         → current heart balance
POST /rewards/items/{item_id}/purchase  → atomic purchase
GET  /rewards/inventory       → user's owned items
GET  /rewards/personas/progress → unlock progress for locked personas
POST /rewards/personas/crush/boundary-accept → accept Crush boundary intro
PRD §11.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.hearts.service import get_balance
from app.personas.boundary_intro import build_boundary_intro_response
from app.personas.progression import get_all_unlock_progress
from app.personas.unlocks import accept_crush_boundary
from app.rewards.catalog import CATALOG, get_catalog_item
from app.rewards.purchase_service import PurchaseError, purchase_item
from app.services.db.models import User, UserInventoryItem
from app.services.db.session import get_db

router = APIRouter(prefix="/rewards", tags=["rewards"])

logger = logging.getLogger(__name__)

_SHELF_ORDER = ["persona", "knowledge", "mood_room", "micro_style", "badge", "special"]


def _build_store_shelves() -> list[dict]:
    shelves: dict[str, list] = {shelf: [] for shelf in _SHELF_ORDER}
    for item in CATALOG:
        shelf = item.get("item_type", "special")
        shelves.setdefault(shelf, []).append({
            "item_id": item["item_id"],
            "title": item["title"],
            "subtitle": item.get("subtitle"),
            "description": item.get("description"),
            "price_hearts": item["price_hearts"],
            "tier": item["tier"],
            "icon_key": item.get("icon_key"),
            "requirements": item.get("requirements", {}),
        })
    return [
        {"shelf": shelf, "items": items}
        for shelf in _SHELF_ORDER
        if (items := shelves.get(shelf))
    ]


@router.get("/store")
def get_store(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    balance = get_balance(db, current_user.user_id)
    return ok({"shelves": _build_store_shelves(), "balance": balance})


@router.get("/balance")
def get_heart_balance(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    return ok({"balance": get_balance(db, current_user.user_id)})


@router.post("/items/{item_id}/purchase")
def purchase(
    item_id: str = Path(..., max_length=100),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    try:
        result = purchase_item(db, user_id=current_user.user_id, item_id=item_id)
        db.commit()
        return ok(result, status_code=201 if not result.get("idempotent") else 200)
    except PurchaseError as exc:
        raise AppError(exc.code, str(exc), exc.http_status) from exc


@router.get("/inventory")
def get_inventory(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(UserInventoryItem).where(UserInventoryItem.user_id == current_user.user_id)
    ).all()
    return ok({
        "items": [
            {
                "inventory_id": i.inventory_id,
                "item_id": i.item_id,
                "acquired_source": i.acquired_source,
                "acquired_at": i.acquired_at.isoformat() + "Z",
            }
            for i in items
        ]
    })


@router.get("/personas/progress")
def persona_unlock_progress(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    return ok({"personas": get_all_unlock_progress(db, user_id=current_user.user_id)})


@router.get("/personas/crush/boundary-intro")
def crush_boundary_intro(current_user: User = Depends(ensure_policy_acknowledged)):
    return ok(build_boundary_intro_response())


@router.post("/personas/crush/boundary-accept")
def crush_boundary_accept(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    accept_crush_boundary(db, user_id=current_user.user_id)
    db.commit()
    return ok({"accepted": True})
