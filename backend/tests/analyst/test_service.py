from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.analyst.service import run_analyst_pipeline
from app.analyst.types import AnalystRunRequest
from app.services.db.models import AnalystFeatureSnapshot, AnalystRun, AnalystSignal, InsightEvidence, InsightHypothesis, MoodCheckin, User
from app.services.db.session import Base


def _db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables)
    return Session(engine), engine, tables


def test_daily_analyst_run_writes_core_records_and_is_idempotent():
    db, engine, tables = _db()
    try:
        db.add(User(user_id="u1", display_name="U1", email="u1@test.local", password_hash="x", is_active=True))
        db.flush()
        start = datetime(2026, 5, 10, 0, 0, 0)
        for idx, mood in enumerate(["good", "bad", "fine", "good", "bad"]):
            db.add(
                MoodCheckin(
                    checkin_id=f"m{idx}",
                    user_id="u1",
                    mood=mood,
                    emotions=["mệt"] if mood == "bad" else ["ổn"],
                    triggers=["deadline"],
                    note='{"note":"deadline", "extra":{}}',
                    logged_date=(start + timedelta(days=idx)).date(),
                    logged_at=start + timedelta(days=idx, hours=8 if idx % 2 else 20),
                    time_bucket="evening" if idx % 2 == 0 else "morning",
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
        assert result.status == "completed"
        assert db.scalar(select(AnalystRun).where(AnalystRun.run_id == result.run_id)) is not None
        assert db.scalars(select(AnalystFeatureSnapshot)).first() is not None
        assert db.scalars(select(AnalystSignal)).first() is not None
        assert db.scalars(select(InsightHypothesis).where(InsightHypothesis.display_allowed.is_(True))).first() is not None
        assert db.scalars(select(InsightEvidence)).first() is not None

        again = run_analyst_pipeline(db, req)
        assert again.run_id == result.run_id
        assert again.skipped_reason == "idempotent_existing_run"
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=tables)
