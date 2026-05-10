"""Tests for Plan 07 — Knowledge Unlocks.

Covers:
- Content review: approve safe content, reject diagnosis framing, SOS, oversized
- Catalog: get_all_packs, get_cards_for_pack, ordering
- Progress service: free pack access, paid pack requires inventory
- complete_card: +15 Tim granted once
- complete_card: idempotent — duplicate gives already_completed=True, no extra Tim
- complete_card: unknown card raises ValueError
- complete_card: no access raises ValueError
- get_user_progress: returns completed rows

Uses in-memory SQLite (same pattern as other test files).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.services.db.models import (
    HeartWallet,
    KnowledgeCard,
    KnowledgePack,
    RewardStoreItem,
    User,
    UserInventoryItem,
    UserKnowledgeProgress,
)
from app.services.db.session import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables_for_sqlite)
    with Session(engine) as session:
        user = User(
            user_id="usr_know_test",
            display_name="Knowledge Tester",
            email="know@test.com",
            password_hash="x",
            is_active=True,
        )
        session.add(user)

        # Free pack
        free_pack = KnowledgePack(
            pack_id="kp_free",
            title="Free Pack",
            description="No cost",
            category="stress",
            price_hearts=None,
            is_active=True,
        )
        # Paid pack — requires inventory item "item_paid_pack"
        paid_pack = KnowledgePack(
            pack_id="kp_paid",
            title="Paid Pack",
            description="Costs hearts",
            category="sleep",
            price_hearts=300,
            is_active=True,
        )
        session.add_all([free_pack, paid_pack])
        session.flush()

        card1 = KnowledgeCard(
            card_id="kc_free_01",
            pack_id="kp_free",
            title="Card 1",
            content_markdown="Some safe educational content.",
            order_index=1,
            estimated_read_seconds=60,
        )
        card2 = KnowledgeCard(
            card_id="kc_free_02",
            pack_id="kp_free",
            title="Card 2",
            content_markdown="More safe content.",
            order_index=2,
            estimated_read_seconds=45,
        )
        card_paid = KnowledgeCard(
            card_id="kc_paid_01",
            pack_id="kp_paid",
            title="Paid Card",
            content_markdown="Paid educational content.",
            order_index=1,
            estimated_read_seconds=70,
        )
        session.add_all([card1, card2, card_paid])
        session.commit()
        yield session
    Base.metadata.drop_all(engine, tables=tables_for_sqlite)


# ---------------------------------------------------------------------------
# Content review
# ---------------------------------------------------------------------------

class TestContentReview:
    def test_approves_safe_psychoeducation(self):
        from app.knowledge.content_review import review_knowledge_card

        result = review_knowledge_card(
            title="Hiểu về Căng thẳng",
            content_markdown=(
                "Căng thẳng là phản ứng tự nhiên. Nếu triệu chứng kéo dài, "
                "hãy tham khảo chuyên gia."
            ),
        )
        assert result["approved"] is True

    def test_rejects_diagnosis_framing(self):
        from app.knowledge.content_review import review_knowledge_card

        result = review_knowledge_card(
            title="Rối loạn lo âu",
            content_markdown="Bạn bị rối loạn lo âu theo mùa.",
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "diagnosis_framing"

    def test_rejects_sos_content(self):
        from app.knowledge.content_review import review_knowledge_card

        result = review_knowledge_card(
            title="Cảm xúc khó khăn",
            content_markdown="Nếu bạn muốn tự tử, hãy...",
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "sos_content_without_escalation"

    def test_rejects_empty_content(self):
        from app.knowledge.content_review import review_knowledge_card

        result = review_knowledge_card(title="Title", content_markdown="")
        assert result["approved"] is False
        assert result["rejection_reason"] == "empty_content"

    def test_rejects_content_too_long(self):
        from app.knowledge.content_review import review_knowledge_card

        result = review_knowledge_card(title="Title", content_markdown="x" * 5001)
        assert result["approved"] is False
        assert result["rejection_reason"] == "content_too_long"


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class TestCatalog:
    def test_get_all_packs_returns_list(self):
        from app.knowledge.catalog import get_all_packs

        packs = get_all_packs()
        assert len(packs) >= 1
        assert all("pack_id" in p for p in packs)

    def test_cards_sorted_by_order_index(self):
        from app.knowledge.catalog import get_cards_for_pack

        cards = get_cards_for_pack("kp_stress_basics")
        orders = [c["order_index"] for c in cards]
        assert orders == sorted(orders)

    def test_get_pack_returns_none_for_unknown(self):
        from app.knowledge.catalog import get_pack

        assert get_pack("kp_unknown_xyz") is None

    def test_get_card_returns_none_for_unknown(self):
        from app.knowledge.catalog import get_card

        assert get_card("kc_unknown_xyz") is None


# ---------------------------------------------------------------------------
# Pack access
# ---------------------------------------------------------------------------

class TestPackAccess:
    def test_free_pack_always_accessible(self, db):
        from app.knowledge.progress_service import has_pack_access

        assert has_pack_access(db, "usr_know_test", "kp_free") is True

    def test_paid_pack_not_accessible_without_inventory(self, db):
        from app.knowledge.progress_service import has_pack_access

        assert has_pack_access(db, "usr_know_test", "kp_paid") is False

    def test_paid_pack_accessible_with_inventory(self, db):
        from app.knowledge.progress_service import has_pack_access

        # Add a mock store item and inventory row to grant access to kp_paid
        item = RewardStoreItem(
            item_id="kp_paid",
            item_type="knowledge",
            title="Paid Pack",
            price_hearts=300,
            tier=1,
            metadata_json={},
            requirements={},
        )
        db.add(item)
        db.flush()

        inv = UserInventoryItem(
            inventory_id="inv_test_001",
            user_id="usr_know_test",
            item_id="kp_paid",
            acquired_source="purchase",
        )
        db.add(inv)
        db.commit()

        assert has_pack_access(db, "usr_know_test", "kp_paid") is True

    def test_unknown_pack_returns_false(self, db):
        from app.knowledge.progress_service import has_pack_access

        assert has_pack_access(db, "usr_know_test", "kp_nonexistent") is False


# ---------------------------------------------------------------------------
# Card completion
# ---------------------------------------------------------------------------

class TestCardCompletion:
    def test_complete_free_card_grants_hearts(self, db):
        from app.knowledge.progress_service import complete_card

        result = complete_card(db, "usr_know_test", "kc_free_01")
        db.commit()

        assert result["already_completed"] is False
        assert result["reward"]["granted"] is True
        assert result["reward"]["amount"] == 15

    def test_complete_same_card_twice_is_idempotent(self, db):
        from app.knowledge.progress_service import complete_card

        complete_card(db, "usr_know_test", "kc_free_01")
        db.commit()

        result2 = complete_card(db, "usr_know_test", "kc_free_01")
        db.commit()

        assert result2["already_completed"] is True
        assert result2["reward"] is None

    def test_second_card_in_same_pack_also_grants_hearts(self, db):
        from app.knowledge.progress_service import complete_card

        r1 = complete_card(db, "usr_know_test", "kc_free_01")
        db.commit()
        r2 = complete_card(db, "usr_know_test", "kc_free_02")
        db.commit()

        assert r1["reward"]["granted"] is True
        assert r2["reward"]["granted"] is True
        assert r2["reward"]["new_balance"] == 30

    def test_complete_unknown_card_raises(self, db):
        from app.knowledge.progress_service import complete_card

        with pytest.raises(ValueError, match="unknown card_id"):
            complete_card(db, "usr_know_test", "kc_nonexistent")

    def test_complete_paid_card_without_access_raises(self, db):
        from app.knowledge.progress_service import complete_card

        with pytest.raises(ValueError, match="does not have access"):
            complete_card(db, "usr_know_test", "kc_paid_01")


# ---------------------------------------------------------------------------
# Progress listing
# ---------------------------------------------------------------------------

class TestProgressListing:
    def test_progress_empty_initially(self, db):
        from app.knowledge.progress_service import get_user_progress

        rows = get_user_progress(db, "usr_know_test")
        assert rows == []

    def test_progress_includes_completed_cards(self, db):
        from app.knowledge.progress_service import complete_card, get_user_progress

        complete_card(db, "usr_know_test", "kc_free_01")
        db.commit()

        rows = get_user_progress(db, "usr_know_test")
        card_ids = [r["card_id"] for r in rows]
        assert "kc_free_01" in card_ids

    def test_progress_has_completed_at(self, db):
        from app.knowledge.progress_service import complete_card, get_user_progress

        complete_card(db, "usr_know_test", "kc_free_02")
        db.commit()

        rows = get_user_progress(db, "usr_know_test")
        match = next(r for r in rows if r["card_id"] == "kc_free_02")
        assert match["completed_at"] is not None
