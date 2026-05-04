"""Tests for reward store catalog and purchase service.

Uses in-memory SQLite; seeds catalog items needed for purchase.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.rewards.catalog import CATALOG, validate_catalog_item, validate_full_catalog
from app.services.db.models import (
    HeartWallet,
    RewardStoreItem,
    User,
    UserInventoryItem,
)
from app.services.db.session import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(user_id="usr_buy", display_name="Buyer", email="b@test.com",
                          password_hash="x", is_active=True))
        # Seed catalog items needed by purchase_service
        for item in CATALOG:
            session.merge(RewardStoreItem(
                item_id=item["item_id"],
                item_type=item["item_type"],
                title=item["title"],
                subtitle=item.get("subtitle"),
                price_hearts=item["price_hearts"],
                tier=item["tier"],
                icon_key=item.get("icon_key"),
                metadata_json=item.get("metadata", {}),
                requirements=item.get("requirements", {}),
            ))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


def _fund_wallet(db, user_id: str, balance: int):
    from app.hearts.service import grant_hearts
    grant_hearts(db, user_id=user_id, amount=balance, event_type="test_fund",
                 source_tab="test", idempotency_key=f"fund:{user_id}:{balance}:{id(db)}")
    db.commit()


# ---------------------------------------------------------------------------
# Catalog validation
# ---------------------------------------------------------------------------

def test_catalog_validates_cleanly():
    validate_full_catalog()


def test_catalog_item_price_out_of_range_fails():
    bad_item = {"item_id": "bad", "item_type": "x", "title": "Bad", "price_hearts": 50, "tier": 1}
    with pytest.raises(ValueError, match="price_hearts"):
        validate_catalog_item(bad_item)


def test_catalog_crush_forbidden_copy_raises():
    bad_item = {
        "item_id": "persona_crush",
        "item_type": "persona",
        "title": "Crush",
        "description": "người yêu AI đồng hành",
        "price_hearts": 5000,
        "tier": 3,
    }
    with pytest.raises(ValueError, match="forbidden crush copy"):
        validate_catalog_item(bad_item)


# ---------------------------------------------------------------------------
# Purchase service
# ---------------------------------------------------------------------------

def test_purchase_success(db):
    from app.rewards.purchase_service import purchase_item
    _fund_wallet(db, "usr_buy", 600)

    result = purchase_item(db, user_id="usr_buy", item_id="persona_cun")
    db.commit()

    assert result["idempotent"] is False
    assert result["item_id"] == "persona_cun"
    wallet = db.get(HeartWallet, "usr_buy")
    assert wallet.balance == 600 - 500  # 500 is price of persona_cun


def test_purchase_insufficient_balance(db):
    from app.rewards.purchase_service import PurchaseError, purchase_item

    with pytest.raises(PurchaseError) as exc_info:
        purchase_item(db, user_id="usr_buy", item_id="persona_cun")
    assert exc_info.value.code == "insufficient_hearts"


def test_purchase_creates_inventory_row(db):
    from app.rewards.purchase_service import purchase_item
    _fund_wallet(db, "usr_buy", 600)
    result = purchase_item(db, user_id="usr_buy", item_id="persona_cun")
    db.commit()

    inv = db.get(UserInventoryItem, result["inventory_id"])
    assert inv is not None
    assert inv.user_id == "usr_buy"
    assert inv.item_id == "persona_cun"


def test_purchase_double_spend_rejected(db):
    """Using a fresh idempotency key should hit the already_owned inventory check, not idempotent path."""
    from app.rewards.purchase_service import PurchaseError, purchase_item
    _fund_wallet(db, "usr_buy", 1200)

    purchase_item(db, user_id="usr_buy", item_id="persona_cun", idempotency_key="key_first_attempt")
    db.commit()

    with pytest.raises(PurchaseError) as exc_info:
        purchase_item(db, user_id="usr_buy", item_id="persona_cun", idempotency_key="key_second_attempt")
    assert exc_info.value.code == "already_owned"


def test_purchase_unknown_item_raises(db):
    from app.rewards.purchase_service import PurchaseError, purchase_item
    with pytest.raises(PurchaseError) as exc_info:
        purchase_item(db, user_id="usr_buy", item_id="ghost_item_xyz")
    assert exc_info.value.code == "item_not_found"


def test_purchase_idempotent_on_same_key(db):
    from app.rewards.purchase_service import purchase_item
    _fund_wallet(db, "usr_buy", 600)
    idem = "purchase:usr_buy:persona_cun:idem_test"
    r1 = purchase_item(db, user_id="usr_buy", item_id="persona_cun", idempotency_key=idem)
    db.commit()
    r2 = purchase_item(db, user_id="usr_buy", item_id="persona_cun", idempotency_key=idem)
    assert r2["idempotent"] is True
    wallet = db.get(HeartWallet, "usr_buy")
    assert wallet.balance == 100  # deducted only once
