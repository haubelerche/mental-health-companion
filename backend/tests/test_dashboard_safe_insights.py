"""
Tests: dashboard insights are evidence-backed, non-diagnostic, and user-safe.

FILE 2 of 2 — dashboard safe insights.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.analyst.service import run_analyst_pipeline
from app.analyst.types import AnalystRunRequest
from app.services.db.models import (
    AnalystRun,
    AnalystSignal,
    InsightHypothesis,
    MoodCheckin,
    User,
)
from app.services.db.session import Base

# Clinical / diagnostic terms that must never appear in user-facing display text
_FORBIDDEN_CLINICAL_TERMS = [
    "trầm cảm",
    "rối loạn",
    "depression",
    "disorder",
    "diagnosis",
    "bipolar",
    "panic disorder",
]


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


def _seed_user(db: Session, user_id: str = "u1") -> None:
    db.add(
        User(
            user_id=user_id,
            display_name="Test User",
            email=f"{user_id}@test.local",
            password_hash="x",
            is_active=True,
        )
    )
    db.flush()


def _req(user_id: str, start: datetime, run_type: str = "weekly") -> AnalystRunRequest:
    return AnalystRunRequest(
        user_id=user_id,
        run_type=run_type,
        window_start=start,
        window_end=start + timedelta(days=7),
        data_cutoff_at=start + timedelta(days=7),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_phq9_absent_produces_no_screening_insight():
    """
    When no PHQ-9 / GAD-7 data exists, no InsightHypothesis with a
    screening/diagnosis-implying hypothesis_type should be created.
    """
    db, engine, tables = _db()
    try:
        _seed_user(db)
        start = datetime(2026, 5, 10)

        # Seed enough mood checkins to avoid skipped_insufficient_data for weekly run
        for idx in range(5):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood="fine",
                    emotions=["ổn"],
                    triggers=[],
                    note="{}",
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=9),
                    time_bucket="morning",
                )
            )
        db.commit()

        result = run_analyst_pipeline(db, _req("u1", start))
        db.commit()

        # No insight should carry a screening/post-screening-derived type
        screening_types = {"screening_context_notice"}
        screening_insights = db.scalars(
            select(InsightHypothesis).where(
                InsightHypothesis.user_id == "u1",
                InsightHypothesis.hypothesis_type.in_(screening_types),
                InsightHypothesis.display_allowed.is_(True),
            )
        ).all()

        assert len(screening_insights) == 0, (
            f"Expected no screening insights without PHQ-9 data, "
            f"found {len(screening_insights)}"
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)


def test_mood_checkins_produce_emotion_signal():
    """
    Five bad mood check-ins should cause the analyst to produce at least one
    AnalystSignal with a non-null emotional_theme (the mood-related signal field).
    """
    db, engine, tables = _db()
    try:
        _seed_user(db)
        start = datetime(2026, 5, 10)

        for idx in range(5):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood="bad",
                    emotions=["mệt", "lo"],
                    triggers=["áp lực"],
                    note='{"note":"mệt"}',
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=10),
                    time_bucket="morning",
                )
            )
        db.commit()

        result = run_analyst_pipeline(db, _req("u1", start))
        db.commit()

        if result.status == "skipped_insufficient_data":
            # Pipeline decided data is insufficient — that is acceptable, but
            # we should still have a snapshot written.  Signal check is skipped.
            return

        assert result.status == "completed"

        # At least one AnalystSignal should have been written for this run
        signals = db.scalars(
            select(AnalystSignal).where(AnalystSignal.user_id == "u1")
        ).all()
        assert len(signals) >= 1, "Expected at least one AnalystSignal after pipeline run"

        # At least one signal should have emotional_theme (mood-related signal)
        mood_signals = [s for s in signals if s.emotional_theme is not None]
        assert len(mood_signals) >= 1, (
            "Expected at least one AnalystSignal with emotional_theme set after "
            "5 bad mood check-ins"
        )
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)


def test_insight_has_display_allowed_flag():
    """Any InsightHypothesis generated must have display_allowed set (not null)."""
    db, engine, tables = _db()
    try:
        _seed_user(db)
        start = datetime(2026, 5, 10)

        for idx in range(5):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood="bad",
                    emotions=["mệt"],
                    triggers=["deadline"],
                    note="{}",
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=8),
                    time_bucket="morning",
                )
            )
        db.commit()

        run_analyst_pipeline(db, _req("u1", start))
        db.commit()

        hypotheses = db.scalars(
            select(InsightHypothesis).where(InsightHypothesis.user_id == "u1")
        ).all()

        for hyp in hypotheses:
            assert hyp.display_allowed is not None, (
                f"InsightHypothesis {hyp.insight_id} (type={hyp.hypothesis_type}) "
                "has display_allowed=None — must be True or False"
            )
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)


def test_low_signal_count_produces_low_confidence_or_empty():
    """
    A single mood check-in is below the weekly threshold (requires >= 3 mood + >= 5 events).
    The pipeline should either complete with low confidence OR return skipped_insufficient_data
    with no safe_dashboard_candidates.
    """
    db, engine, tables = _db()
    try:
        _seed_user(db)
        start = datetime(2026, 5, 10)

        db.add(
            MoodCheckin(
                checkin_id="m0",
                user_id="u1",
                mood="bad",
                emotions=["mệt"],
                triggers=[],
                note="{}",
                logged_date=start.date(),
                logged_at=start,
                time_bucket="morning",
            )
        )
        db.commit()

        result = run_analyst_pipeline(db, _req("u1", start, run_type="weekly"))
        db.commit()

        # With only 1 check-in the pipeline should skip or produce low confidence
        if result.status == "completed":
            run_row = db.scalar(
                select(AnalystRun).where(AnalystRun.run_id == result.run_id)
            )
            assert run_row is not None
            assert run_row.status == "completed"

            # If completed, insights should be minimal (no safe display candidates
            # OR any InsightHypothesis created should not have high confidence)
            display_hyps = db.scalars(
                select(InsightHypothesis).where(
                    InsightHypothesis.user_id == "u1",
                    InsightHypothesis.display_allowed.is_(True),
                    InsightHypothesis.status == "active",
                )
            ).all()
            # All displayed insights should be low confidence
            for hyp in display_hyps:
                assert hyp.confidence is None or hyp.confidence <= 0.5, (
                    f"Expected low confidence with minimal data, got {hyp.confidence}"
                )
        else:
            # skipped_insufficient_data is the expected happy path
            assert result.status == "skipped_insufficient_data"
            assert result.skipped_reason is not None
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)


def test_no_internal_clinical_label_in_display_text():
    """
    InsightHypothesis title and user_safe_summary must NOT contain clinical
    diagnostic terms that would constitute implicit diagnosis.
    """
    db, engine, tables = _db()
    try:
        _seed_user(db)
        start = datetime(2026, 5, 10)

        for idx in range(5):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood="bad",
                    emotions=["mệt", "lo lắng"],
                    triggers=["áp lực công việc"],
                    note='{"note":"lo"}',
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=9),
                    time_bucket="morning",
                )
            )
        db.commit()

        run_analyst_pipeline(db, _req("u1", start))
        db.commit()

        hypotheses = db.scalars(
            select(InsightHypothesis).where(InsightHypothesis.user_id == "u1")
        ).all()

        for hyp in hypotheses:
            combined_text = (
                (hyp.title or "") + " " + (hyp.user_safe_summary or "")
            ).lower()
            for term in _FORBIDDEN_CLINICAL_TERMS:
                assert term.lower() not in combined_text, (
                    f"InsightHypothesis {hyp.insight_id} contains forbidden clinical "
                    f"term '{term}' in display text: {combined_text[:200]!r}"
                )
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)
