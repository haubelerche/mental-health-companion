"""Tests for Plan 06 — Memory Cards.

Covers:
- Guardrail: approve, reject (diagnosis, SOS, too-long, invalid type)
- Extractor: produces correct typed candidates from session text
- Service: create from candidates, user actions (keep/edit/delete/disable_personalization)
- Service: audit events created on every action
- Service: deleted cards excluded from context retrieval
- Service: micro-memory rule — get_active_card_for_context returns at most one card

Uses in-memory SQLite (same pattern as other test files in this repo).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.services.db.models import MemoryCard, MemoryCardAuditEvent, User
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

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            user_id="usr_mem_test",
            display_name="Mem Tester",
            email="mem@test.com",
            password_hash="x",
            is_active=True,
        )
        session.add(user)
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Guardrail tests
# ---------------------------------------------------------------------------

class TestGuardrail:
    def test_approves_valid_preference(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="preference",
            title="Sở thích của bạn",
            content="Bạn thích câu trả lời ngắn gọn vào buổi tối.",
            confidence=0.75,
        )
        assert result["approved"] is True
        assert result["rejection_reason"] is None

    def test_rejects_diagnosis_language(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="emotional_pattern",
            title="Cảm xúc",
            content="Bạn bị trầm cảm theo mùa.",
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "diagnosis_language"

    def test_rejects_sos_content(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="emotional_pattern",
            title="Cảm xúc",
            content="Bạn đã từng nghĩ đến việc tự tử.",
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "sos_content"

    def test_rejects_content_too_long(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="preference",
            title="Title",
            content="x" * 301,
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "content_too_long"

    def test_rejects_invalid_memory_type(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="unknown_type",
            title="Title",
            content="Some content.",
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "invalid_memory_type"

    def test_rejects_invalid_confidence(self):
        from app.memory.guardrail import review_memory_candidate

        result = review_memory_candidate(
            memory_type="coping_history",
            title="Title",
            content="Đi bộ giúp bạn nhẹ hơn.",
            confidence=1.5,
        )
        assert result["approved"] is False
        assert result["rejection_reason"] == "invalid_confidence"


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class TestExtractor:
    def test_empty_text_returns_no_candidates(self):
        from app.memory.extractor import extract_memory_candidates

        result = extract_memory_candidates("")
        assert result["candidate_cards"] == []

    def test_detects_coping_history_signal(self):
        from app.memory.extractor import extract_memory_candidates

        result = extract_memory_candidates(
            "hôm qua đi bộ ngắn giúp tôi nhẹ hơn nhiều", session_id="sess_abc"
        )
        types = [c["memory_type"] for c in result["candidate_cards"]]
        assert "coping_history" in types

    def test_detects_stressor_signal(self):
        from app.memory.extractor import extract_memory_candidates

        result = extract_memory_candidates("deadline tuần này làm tôi stress lắm")
        types = [c["memory_type"] for c in result["candidate_cards"]]
        assert "current_stressor" in types

    def test_session_id_propagated(self):
        from app.memory.extractor import extract_memory_candidates

        result = extract_memory_candidates(
            "đi bộ ngắn giúp nhẹ hơn", session_id="sess_xyz"
        )
        for card in result["candidate_cards"]:
            assert card["source_session_id"] == "sess_xyz"

    def test_no_duplicate_types(self):
        from app.memory.extractor import extract_memory_candidates

        text = "đi bộ giúp nhẹ hơn, hít thở sâu bình tĩnh lại"
        result = extract_memory_candidates(text)
        types = [c["memory_type"] for c in result["candidate_cards"]]
        assert len(types) == len(set(types)), "duplicate memory_type extracted"


# ---------------------------------------------------------------------------
# Service: create_cards_from_candidates
# ---------------------------------------------------------------------------

class TestCreateCards:
    def test_approved_candidates_persisted(self, db):
        from app.memory.extractor import extract_memory_candidates
        from app.memory.service import create_cards_from_candidates

        extraction = extract_memory_candidates("đi bộ giúp nhẹ hơn", session_id="s1")
        cards = create_cards_from_candidates(db, "usr_mem_test", extraction)
        db.commit()

        assert len(cards) >= 1
        for card in cards:
            assert card.safety_review_status == "approved"
            assert card.status == "pending_user_review"

    def test_rejected_candidates_stored_with_rejected_status(self, db):
        from app.memory.extractor import ExtractionResult, MemoryCandidate
        from app.memory.service import create_cards_from_candidates

        bad_extraction = ExtractionResult(candidate_cards=[
            MemoryCandidate(
                memory_type="emotional_pattern",
                title="Bad card",
                content="Bạn bị trầm cảm nặng.",
                confidence=0.9,
                source_session_id=None,
                metadata={},
            )
        ])
        cards = create_cards_from_candidates(db, "usr_mem_test", bad_extraction)
        db.commit()

        assert len(cards) == 1
        assert cards[0].status == "rejected_by_guardrail"
        assert cards[0].safety_review_status == "rejected"


# ---------------------------------------------------------------------------
# Service: user actions
# ---------------------------------------------------------------------------

def _make_card(db: Session, status: str = "pending_user_review") -> MemoryCard:
    card = MemoryCard(
        card_id="mc_testcard001",
        user_id="usr_mem_test",
        memory_type="coping_history",
        title="Đi bộ giúp ích",
        content="Đi bộ ngắn từng giúp bạn nhẹ hơn.",
        confidence=0.75,
        status=status,
        safety_review_status="approved",
        personalization_disabled=False,
        metadata_json={},
    )
    db.add(card)
    db.commit()
    return card


class TestUserActions:
    def test_keep_sets_active(self, db):
        from app.memory.service import apply_user_action

        _make_card(db)
        card = apply_user_action(db, "usr_mem_test", "mc_testcard001", "keep")
        db.commit()
        assert card.status == "active"

    def test_keep_creates_audit_event(self, db):
        from app.memory.service import apply_user_action

        _make_card(db)
        apply_user_action(db, "usr_mem_test", "mc_testcard001", "keep")
        db.commit()

        events = db.query(MemoryCardAuditEvent).filter_by(memory_card_id="mc_testcard001").all()
        assert len(events) == 1
        assert events[0].action == "keep"

    def test_edit_updates_content_and_creates_audit(self, db):
        from app.memory.service import apply_user_action

        _make_card(db)
        card = apply_user_action(
            db,
            "usr_mem_test",
            "mc_testcard001",
            "edit",
            new_content="Đi bộ 10 phút giúp bạn nhẹ hơn nhiều.",
        )
        db.commit()

        assert card.status == "edited_by_user"
        assert "10 phút" in card.content

        events = db.query(MemoryCardAuditEvent).filter_by(memory_card_id="mc_testcard001").all()
        assert len(events) == 1
        assert events[0].action == "edit"
        assert events[0].old_value["content"] == "Đi bộ ngắn từng giúp bạn nhẹ hơn."

    def test_edit_rejected_by_guardrail_raises(self, db):
        from app.memory.service import apply_user_action

        _make_card(db)
        with pytest.raises(ValueError, match="guardrail"):
            apply_user_action(
                db,
                "usr_mem_test",
                "mc_testcard001",
                "edit",
                new_content="Bạn bị trầm cảm nặng vì áp lực.",
            )

    def test_delete_sets_deleted_status(self, db):
        from app.memory.service import apply_user_action

        _make_card(db)
        card = apply_user_action(db, "usr_mem_test", "mc_testcard001", "delete")
        db.commit()
        assert card.status == "deleted_by_user"

    def test_delete_then_action_raises(self, db):
        from app.memory.service import apply_user_action

        _make_card(db, status="deleted_by_user")
        with pytest.raises(ValueError, match="deleted"):
            apply_user_action(db, "usr_mem_test", "mc_testcard001", "keep")

    def test_disable_personalization(self, db):
        from app.memory.service import apply_user_action

        _make_card(db, status="active")
        card = apply_user_action(
            db, "usr_mem_test", "mc_testcard001", "disable_personalization"
        )
        db.commit()
        assert card.personalization_disabled is True

    def test_not_found_raises(self, db):
        from app.memory.service import apply_user_action

        with pytest.raises(ValueError, match="not found"):
            apply_user_action(db, "usr_mem_test", "mc_nonexistent", "keep")


# ---------------------------------------------------------------------------
# Service: get_user_cards — deleted / rejected excluded
# ---------------------------------------------------------------------------

class TestGetUserCards:
    def test_deleted_excluded_by_default(self, db):
        from app.memory.service import get_user_cards

        _make_card(db, status="deleted_by_user")
        cards = get_user_cards(db, "usr_mem_test")
        assert not any(c.card_id == "mc_testcard001" for c in cards)

    def test_include_deleted_param(self, db):
        from app.memory.service import get_user_cards

        _make_card(db, status="deleted_by_user")
        cards = get_user_cards(db, "usr_mem_test", include_deleted=True)
        assert any(c.card_id == "mc_testcard001" for c in cards)


# ---------------------------------------------------------------------------
# Service: micro-memory rule
# ---------------------------------------------------------------------------

class TestContextCard:
    def test_active_card_returned(self, db):
        from app.memory.service import apply_user_action, get_active_card_for_context

        _make_card(db)
        apply_user_action(db, "usr_mem_test", "mc_testcard001", "keep")
        db.commit()

        card = get_active_card_for_context(db, "usr_mem_test")
        assert card is not None
        assert card.card_id == "mc_testcard001"

    def test_deleted_card_excluded_from_context(self, db):
        from app.memory.service import apply_user_action, get_active_card_for_context

        _make_card(db, status="active")
        apply_user_action(db, "usr_mem_test", "mc_testcard001", "delete")
        db.commit()

        card = get_active_card_for_context(db, "usr_mem_test")
        assert card is None

    def test_personalization_disabled_excluded(self, db):
        from app.memory.service import apply_user_action, get_active_card_for_context

        _make_card(db, status="active")
        apply_user_action(db, "usr_mem_test", "mc_testcard001", "disable_personalization")
        db.commit()

        card = get_active_card_for_context(db, "usr_mem_test")
        assert card is None
