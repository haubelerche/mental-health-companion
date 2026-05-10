"""Concurrency / idempotency tests — Plan 10.

Simulate concurrent requests by calling service functions twice with the
same idempotency key and asserting only one effect is applied.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

# Module-level imports register all models with Base.metadata before create_all.
from app.services.db.models import (  # noqa: F401
    HeartWallet,
    HeartRewardEvent,
    KnowledgeCard,
    KnowledgePack,
    RewardStoreItem,
    User,
    UserInventoryItem,
    UserKnowledgeProgress,
)
from app.services.db.session import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables_for_sqlite)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine, tables=tables_for_sqlite)


def _seed(db: Session, user_id: str = "usr_conc") -> None:
    db.add(User(
        user_id=user_id,
        display_name="Conc",
        email=f"{user_id}@test.com",
        password_hash="x",
        is_active=True,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# Heart economy idempotency
# ---------------------------------------------------------------------------

def test_two_mood_checkin_rewards_grant_once(db):
    _seed(db)
    from app.hearts.service import grant_hearts, get_balance
    key = "mood_checkin:usr_conc:2026-05-03"
    r1 = grant_hearts(db, user_id="usr_conc", amount=10, event_type="daily_mood_checkin_completed",
                      source_tab="checkin", idempotency_key=key)
    db.commit()
    r2 = grant_hearts(db, user_id="usr_conc", amount=10, event_type="daily_mood_checkin_completed",
                      source_tab="checkin", idempotency_key=key)
    db.commit()
    assert r1["granted"] is True
    assert r2["granted"] is False
    assert get_balance(db, "usr_conc") == 10


def test_7_day_streak_bonus_granted_at_day_7(db):
    _seed(db)
    from app.hearts.streaks import update_mood_streak
    from app.hearts.service import get_balance
    import datetime

    base = datetime.date(2026, 5, 3)
    for i in range(7):
        update_mood_streak(db, user_id="usr_conc", checkin_date=base + datetime.timedelta(days=i))
    db.commit()

    assert get_balance(db, "usr_conc") == 20


def test_7_day_streak_second_cycle_grants_again(db):
    _seed(db)
    from app.hearts.streaks import update_mood_streak
    from app.hearts.service import get_balance
    import datetime

    base = datetime.date(2026, 5, 3)
    for i in range(14):
        update_mood_streak(db, user_id="usr_conc", checkin_date=base + datetime.timedelta(days=i))
    db.commit()

    assert get_balance(db, "usr_conc") == 40


# ---------------------------------------------------------------------------
# Purchase idempotency
# ---------------------------------------------------------------------------

def _seed_store_item(db: Session, item_id: str = "persona_cun") -> dict:
    from app.rewards.catalog import CATALOG
    item = next(i for i in CATALOG if i["item_id"] == item_id)
    db.add(RewardStoreItem(
        item_id=item["item_id"], item_type=item["item_type"], title=item["title"],
        price_hearts=item["price_hearts"], tier=item["tier"],
        metadata_json=item.get("metadata", {}), requirements=item.get("requirements", {}),
    ))
    db.commit()
    return item


def test_two_purchase_requests_no_double_spend(db):
    _seed(db)
    from app.rewards.purchase_service import PurchaseError, purchase_item
    from app.hearts.service import grant_hearts, get_balance

    item = _seed_store_item(db)
    grant_hearts(db, user_id="usr_conc", amount=1200, event_type="fund",
                 source_tab="test", idempotency_key="fund:conc:ds")
    db.commit()

    purchase_item(db, user_id="usr_conc", item_id="persona_cun", idempotency_key="buy:01")
    db.commit()

    with pytest.raises(PurchaseError) as exc:
        purchase_item(db, user_id="usr_conc", item_id="persona_cun", idempotency_key="buy:02")
    assert exc.value.code == "already_owned"
    assert get_balance(db, "usr_conc") == 1200 - item["price_hearts"]


def test_idempotent_purchase_same_key_no_double_charge(db):
    _seed(db)
    from app.rewards.purchase_service import purchase_item
    from app.hearts.service import grant_hearts, get_balance

    item = _seed_store_item(db)
    grant_hearts(db, user_id="usr_conc", amount=1000, event_type="fund",
                 source_tab="test", idempotency_key="fund:conc:ic")
    db.commit()

    key = "idem:buy:cun"
    purchase_item(db, user_id="usr_conc", item_id="persona_cun", idempotency_key=key)
    db.commit()
    r2 = purchase_item(db, user_id="usr_conc", item_id="persona_cun", idempotency_key=key)
    assert r2["idempotent"] is True
    assert get_balance(db, "usr_conc") == 1000 - item["price_hearts"]


# ---------------------------------------------------------------------------
# Knowledge card completion idempotency
# ---------------------------------------------------------------------------

def test_knowledge_card_complete_grants_tim_once(db):
    _seed(db)
    from app.knowledge.progress_service import complete_card
    from app.hearts.service import get_balance

    db.add(KnowledgePack(
        pack_id="pack_free", title="Free Pack", description="desc",
        category="test", price_hearts=None,
    ))
    db.commit()  # commit pack before adding card (SQLite FK check at insert time)
    db.add(KnowledgeCard(
        card_id="card_free_01", pack_id="pack_free", title="Card",
        content_markdown="content", order_index=0,
    ))
    db.commit()

    r1 = complete_card(db, user_id="usr_conc", card_id="card_free_01")
    db.commit()
    r2 = complete_card(db, user_id="usr_conc", card_id="card_free_01")
    db.commit()

    assert r1["already_completed"] is False
    assert r1["reward"] is not None
    assert r2["already_completed"] is True
    assert r2["reward"] is None
    assert get_balance(db, "usr_conc") == 15
