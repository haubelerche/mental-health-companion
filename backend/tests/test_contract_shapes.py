"""Contract shape stability tests — Plan 10.

Verify that response shapes for persona registry, reward store, wallet,
TTS job, and memory cards remain stable so frontends can rely on them.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

# Module-level imports register models with Base.metadata before create_all.
from app.rewards.catalog import CATALOG
from app.services.db.models import (  # noqa: F401 — registers all tables with Base
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

    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables_for_sqlite)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine, tables=tables_for_sqlite)


def _seed_user(db: Session, user_id: str = "usr_contract") -> None:
    db.add(User(
        user_id=user_id,
        display_name="Contract",
        email=f"{user_id}@test.com",
        password_hash="x",
        is_active=True,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# Persona registry
# ---------------------------------------------------------------------------

def test_registry_has_exactly_five_personas():
    from app.personas.registry import PERSONA_REGISTRY
    assert len(PERSONA_REGISTRY) == 5


def test_registry_persona_shape():
    from app.personas.registry import PERSONA_REGISTRY
    # Verify critical attributes the router depends on are present
    required_attrs = {"persona_id", "display_name", "tts_style_id", "max_distress"}
    for persona in PERSONA_REGISTRY.values():
        for attr in required_attrs:
            assert hasattr(persona, attr), f"{persona.persona_id} missing attribute {attr!r}"


def test_persona_router_decision_shape():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id=None,
        distress=0.0,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert hasattr(decision, "target_persona_id")
    assert hasattr(decision, "action")
    assert hasattr(decision, "safety_override")


# ---------------------------------------------------------------------------
# Reward store catalog
# ---------------------------------------------------------------------------

def test_store_item_required_fields():
    required = {"item_id", "item_type", "title", "price_hearts", "tier"}
    for item in CATALOG:
        for key in required:
            assert key in item, f"Item {item.get('item_id')} missing field {key!r}"


def test_store_item_price_within_bounds():
    for item in CATALOG:
        assert 100 <= item["price_hearts"] <= 10_000, (
            f"Item {item['item_id']} price {item['price_hearts']} out of [100, 10000]"
        )


def test_store_item_tier_is_int():
    for item in CATALOG:
        assert isinstance(item["tier"], int), f"Item {item['item_id']} tier must be int"


# ---------------------------------------------------------------------------
# Heart wallet grant response shape
# ---------------------------------------------------------------------------

def test_grant_hearts_response_shape(db):
    _seed_user(db)
    from app.hearts.service import grant_hearts
    result = grant_hearts(
        db,
        user_id="usr_contract",
        amount=10,
        event_type="test_contract",
        source_tab="test",
        idempotency_key="contract:shape:001",
    )
    assert "granted" in result
    assert "amount" in result
    assert "new_balance" in result
    assert "event_id" in result


# ---------------------------------------------------------------------------
# Purchase result shape
# ---------------------------------------------------------------------------

def test_purchase_result_shape(db):
    from app.rewards.purchase_service import purchase_item
    from app.hearts.service import grant_hearts

    _seed_user(db)
    item = CATALOG[0]
    db.add(RewardStoreItem(
        item_id=item["item_id"],
        item_type=item["item_type"],
        title=item["title"],
        price_hearts=item["price_hearts"],
        tier=item["tier"],
        metadata_json=item.get("metadata", {}),
        requirements=item.get("requirements", {}),
    ))
    db.commit()

    grant_hearts(db, user_id="usr_contract", amount=item["price_hearts"] + 100,
                 event_type="fund", source_tab="test", idempotency_key="fund:contract")
    db.commit()

    result = purchase_item(db, user_id="usr_contract", item_id=item["item_id"])
    assert "inventory_id" in result
    assert "item_id" in result
    assert "idempotent" in result
    assert "new_balance" in result


# ---------------------------------------------------------------------------
# Memory card out schema
# ---------------------------------------------------------------------------

def test_memory_card_out_schema_fields():
    from app.memory.routes import MemoryCardOut
    fields = MemoryCardOut.model_fields
    required = {"card_id", "memory_type", "title", "content", "status",
                "safety_review_status", "personalization_disabled", "created_at", "updated_at"}
    for f in required:
        assert f in fields, f"MemoryCardOut missing field {f!r}"


# ---------------------------------------------------------------------------
# TTS status sets
# ---------------------------------------------------------------------------

def test_tts_terminal_statuses_contain_required_values():
    from app.voice.types import TTS_TERMINAL_STATUSES, TTS_REUSABLE_STATUSES
    # Terminal statuses — frontend polling stops here
    for status in ("ready", "failed", "skipped_duplicate", "cache_hit", "provider_disabled"):
        assert status in TTS_TERMINAL_STATUSES, f"{status!r} missing from TTS_TERMINAL_STATUSES"
    # Reusable — audio can be served from cache
    for status in ("ready", "cache_hit"):
        assert status in TTS_REUSABLE_STATUSES, f"{status!r} missing from TTS_REUSABLE_STATUSES"


def test_tts_queued_and_processing_are_not_terminal():
    from app.voice.types import TTS_TERMINAL_STATUSES
    assert "queued" not in TTS_TERMINAL_STATUSES
    assert "processing" not in TTS_TERMINAL_STATUSES
