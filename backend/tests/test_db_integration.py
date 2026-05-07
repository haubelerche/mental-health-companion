"""
Integration tests against a real PostgreSQL/Supabase database.
Run with: DATABASE_URL=<supabase_url> pytest backend/tests/test_db_integration.py -v
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.services.db.models import (
    AnalystSignal,
    InsightHypothesis,
    MoodCheckin,
    SessionRiskSnapshot,
    User,
)


class TestSchemaConnectivity:
    def test_connection_alive(self, real_db) -> None:
        result = real_db.execute(text("SELECT 1"))
        assert result.scalar() == 1

    def test_search_path_is_app(self, real_db) -> None:
        result = real_db.execute(text("SHOW search_path"))
        path = str(result.scalar() or "")
        assert "app" in path, f"search_path does not include app: {path}"

    def test_core_tables_exist(self, real_db) -> None:
        required = [
            "users",
            "conversations",
            "messages",
            "mood_checkins",
            "conversation_memories",
            "session_summaries_archive",
            "analyst_signals",
            "insight_hypotheses",
            "crisis_logs",
            "session_risk_snapshots",
            "risk_inference_log",
            "sync_outbox",
            "admin_audit_log",
        ]
        result = real_db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'app' ORDER BY table_name"
            )
        )
        existing = {row[0] for row in result}
        missing = set(required) - existing
        assert not missing, f"Missing tables: {missing}"


class TestColumnConsistency:
    def test_messages_has_assistant_tone(self, real_db) -> None:
        result = real_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='messages' AND column_name='assistant_tone'"
            )
        )
        assert result.fetchone() is not None, "messages.assistant_tone is missing"

    def test_messages_no_old_vietnamese_column(self, real_db) -> None:
        result = real_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='messages' AND column_name='tone_cam_xuc'"
            )
        )
        assert result.fetchone() is None, "messages.tone_cam_xuc still exists"

    def test_crisis_logs_has_severity_level(self, real_db) -> None:
        result = real_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='crisis_logs' AND column_name='severity_level'"
            )
        )
        assert result.fetchone() is not None, "crisis_logs.severity_level is missing"

    def test_mood_checkins_has_source(self, real_db) -> None:
        result = real_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='mood_checkins' AND column_name='source'"
            )
        )
        assert result.fetchone() is not None, "mood_checkins.source is missing"

    def test_insight_hypotheses_columns(self, real_db) -> None:
        required_cols = {
            "insight_id",
            "user_id",
            "hypothesis_type",
            "title",
            "user_safe_summary",
            "status",
            "display_allowed",
            "confidence",
            "severity_band",
            "evidence_count",
            "created_at",
            "updated_at",
        }
        result = real_db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='app' AND table_name='insight_hypotheses'"
            )
        )
        existing = {row[0] for row in result}
        missing = required_cols - existing
        assert not missing, f"insight_hypotheses missing columns: {missing}"


class TestOrmRead:
    def test_orm_can_query_users(self, real_db) -> None:
        real_db.execute(select(User).limit(1))

    def test_orm_can_query_insight_hypotheses(self, real_db) -> None:
        rows = (
            real_db.execute(select(InsightHypothesis).where(InsightHypothesis.status == "active").limit(5))
            .scalars()
            .all()
        )
        assert isinstance(rows, list)

    def test_orm_can_query_analyst_signals(self, real_db) -> None:
        real_db.execute(select(AnalystSignal).limit(1))

    def test_orm_can_query_session_risk_snapshots(self, real_db) -> None:
        real_db.execute(select(SessionRiskSnapshot).limit(1))


class TestStreamingDataFlow:
    def test_checkin_write_and_read(self, real_db) -> None:
        user = real_db.execute(select(User).limit(1)).scalar_one_or_none()
        if user is None:
            pytest.skip("No user found in DB; seed data required")

        test_date = date(2026, 1, 1)
        existing = real_db.execute(
            select(MoodCheckin).where(
                MoodCheckin.user_id == user.user_id,
                MoodCheckin.logged_date == test_date,
                MoodCheckin.time_bucket == "test_bucket",
            )
        ).scalar_one_or_none()
        if existing:
            real_db.delete(existing)
            real_db.flush()

        checkin = MoodCheckin(
            checkin_id=f"it_{uuid4().hex[:20]}",
            user_id=user.user_id,
            mood="neutral",
            emotions=[],
            triggers=[],
            logged_date=test_date,
            time_bucket="test_bucket",
            source="self_report",
        )
        real_db.add(checkin)
        real_db.flush()

        fetched = real_db.execute(
            select(MoodCheckin).where(MoodCheckin.checkin_id == checkin.checkin_id)
        ).scalar_one()
        assert fetched.mood == "neutral"
        assert fetched.source == "self_report"

        real_db.rollback()
