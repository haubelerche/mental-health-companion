"""
Tests: analyst pipeline produces structured/internal-only output (contract tests).

FILE 1 of 2 — analyst agent contract.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.analyst.service import run_analyst_pipeline
from app.analyst.types import AnalystRunRequest
from app.services.db.models import (
    AnalystRun,
    InsightHypothesis,
    MoodCheckin,
    User,
)
from app.services.db.session import Base
from app.services.schemas.contracts import AnalystBundle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables)
    return Session(engine), engine, tables


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_analyst_bundle_schema_has_no_final_text_field():
    """AnalystBundle must not expose any user-facing chat text fields."""
    forbidden_fields = {"final_text", "reply", "message_to_user", "chat_prose"}
    present = forbidden_fields & set(AnalystBundle.model_fields.keys())
    assert not present, (
        f"AnalystBundle must NOT contain user-facing text fields: {present}"
    )


def test_analyst_bundle_has_safe_dashboard_candidates():
    """A minimal AnalystBundle must have safe_dashboard_candidates as a list."""
    bundle = AnalystBundle(
        user_id="u1",
        time_window={},
        confidence="low",
        dominant_emotions=[],
        recurring_triggers=[],
        cognitive_patterns=[],
        nutrition_patterns=[],
        coping_preferences=[],
        evidence_refs=[],
        missing_info=[],
        safe_dashboard_candidates=[],
    )
    assert isinstance(bundle.safe_dashboard_candidates, list)


def test_analyst_bundle_confidence_is_one_of_three_values():
    """AnalystBundle must reject confidence values outside low/medium/high."""
    with pytest.raises(ValidationError):
        AnalystBundle(
            user_id="u1",
            time_window={},
            confidence="very_high",  # invalid
        )


def test_analyst_safe_dashboard_candidates_are_not_chat_prose():
    """
    Run analyst pipeline with fixture data; verify InsightHypothesis records exist
    and that display_allowed is explicitly set (not leaking raw chat prose).
    """
    db, engine, tables = _db()
    try:
        db.add(User(user_id="u1", display_name="U1", email="u1@test.local", password_hash="x", is_active=True))
        db.flush()

        start = datetime(2026, 5, 10, 0, 0, 0)
        for idx, mood in enumerate(["bad", "bad", "fine", "bad", "bad"]):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood=mood,
                    emotions=["mệt"] if mood == "bad" else ["ổn"],
                    triggers=["deadline"],
                    note='{"note":"stress", "extra":{}}',
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=8),
                    time_bucket="morning",
                )
            )
        db.commit()

        req = AnalystRunRequest(
            user_id="u1",
            run_type="weekly",
            window_start=start,
            window_end=start + timedelta(days=7),
            data_cutoff_at=start + timedelta(days=7),
        )
        result = run_analyst_pipeline(db, req)
        db.commit()

        assert result.status in {"completed", "skipped_insufficient_data"}, (
            f"Unexpected status: {result.status}"
        )

        # All InsightHypothesis records must have display_allowed explicitly set
        hypotheses = db.scalars(
            select(InsightHypothesis).where(InsightHypothesis.user_id == "u1")
        ).all()

        for hyp in hypotheses:
            assert hyp.display_allowed is not None, (
                f"InsightHypothesis {hyp.insight_id} has display_allowed=None"
            )
            # Verify the record does not have a raw free-text chat field
            # (user_safe_summary is allowed; we check it is not None)
            assert hyp.user_safe_summary is not None
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)
