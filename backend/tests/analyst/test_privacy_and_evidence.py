from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.analyst.evidence_builder import create_evidence_rows
from app.analyst.privacy_filter import filter_user_safe_insight
from app.analyst.source_events import make_event
from app.services.db.models import InsightEvidence, InsightHypothesis, User
from app.services.db.session import Base


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables)
    return Session(engine), engine, tables


def test_privacy_filter_blocks_diagnosis_and_risk_language():
    assert not filter_user_safe_insight(summary="Bạn bị depression.", confidence=0.8, evidence_count=4).allowed
    assert not filter_user_safe_insight(summary="Bạn có nguy cơ tự hại cao.", confidence=0.8, evidence_count=4).allowed
    assert not filter_user_safe_insight(summary="PHQ-9 của bạn chứng minh điều này.", confidence=0.8, evidence_count=4).allowed


def test_evidence_builder_only_displays_low_medium_excerpts():
    db, engine, tables = _db()
    try:
        db.add(User(user_id="u1", display_name="U1", email="u1@test.local", password_hash="x", is_active=True))
        db.flush()
        insight = InsightHypothesis(
            insight_id="i1",
            user_id="u1",
            hypothesis_type="trigger_pattern",
            title="Trigger lặp lại",
            user_safe_summary="Deadline xuất hiện vài lần trong check-in gần đây.",
            internal_rationale={},
            evidence_window_start=datetime(2026, 5, 1),
            evidence_window_end=datetime(2026, 5, 14),
            evidence_count=2,
            confidence=0.6,
            severity_band="low",
            status="active",
            display_allowed=True,
            source="analyst_pipeline",
        )
        db.add(insight)
        db.flush()
        event = make_event(
            user_id="u1",
            source_table="mood_checkins",
            source_id="m1",
            event_type="mood_checkin",
            occurred_at=datetime(2026, 5, 14),
            text_for_llm="mệt vì deadline",
            sensitivity="medium",
        )
        ids = create_evidence_rows(db, insight_id="i1", user_id="u1", evidence_events=[event], evidence_type="trigger_pattern")
        db.commit()
        assert len(ids) == 1
        row = db.get(InsightEvidence, ids[0])
        assert row is not None
        assert row.display_allowed is True
        assert row.user_safe_excerpt == "mệt vì deadline"
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)
