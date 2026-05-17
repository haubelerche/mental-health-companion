"""Tests for AnalystContextLoader load coverage and source counts."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from app.services.analyst_context_loader import (
    AnalystContext,
    AnalystContextLoader,
)


def _fake_db():
    return MagicMock()


def test_mood_context_bundle_empty_db():
    db = _fake_db()
    db.scalars.return_value.all.return_value = []
    loader = AnalystContextLoader(db=db)
    bundle = loader.load_mood_context(user_id="u1", window_days=14)
    assert bundle.evidence_count == 0
    assert bundle.source_table == "mood_checkins"
    assert bundle.record_ids == []


def test_mood_context_bundle_counts_records():
    from app.services.db.models import MoodCheckin

    db = _fake_db()
    row1 = MagicMock(spec=MoodCheckin)
    row1.checkin_id = "c1"
    row1.mood = "lo_au"
    row1.triggers = ["hoc_hanh"]
    row1.logged_date = date.today()

    row2 = MagicMock(spec=MoodCheckin)
    row2.checkin_id = "c2"
    row2.mood = "cang_thang"
    row2.triggers = []
    row2.logged_date = date.today() - timedelta(days=1)

    db.scalars.return_value.all.return_value = [row1, row2]
    loader = AnalystContextLoader(db=db)
    bundle = loader.load_mood_context(user_id="u1", window_days=14)
    assert bundle.evidence_count == 2
    assert "mood:c1" in bundle.record_ids
    assert "lo_au" in bundle.emotion_counts


def test_screening_context_returns_no_data_when_no_profile():
    db = _fake_db()
    db.scalar.return_value = None
    loader = AnalystContextLoader(db=db)
    bundle = loader.load_screening_context(user_id="u1")
    assert bundle.evidence_count == 0
    assert bundle.phq9_score is None
    assert "no_clinical_profile" in bundle.limitations


def test_screening_context_loads_all_five_instruments():
    from app.services.db.models import ClinicalProfile

    db = _fake_db()
    profile = MagicMock(spec=ClinicalProfile)
    profile.phq9_score = 8
    profile.gad7_score = 6
    profile.dass21_depression_score = 14
    profile.dass21_anxiety_score = 10
    profile.dass21_stress_score = 18
    profile.mdq_score = 5
    profile.pcl5_score = 22
    db.scalar.return_value = profile

    loader = AnalystContextLoader(db=db)
    bundle = loader.load_screening_context(user_id="u1")
    assert bundle.phq9_score == 8
    assert bundle.gad7_score == 6
    assert bundle.dass21_depression_score == 14
    assert bundle.dass21_anxiety_score == 10
    assert bundle.dass21_stress_score == 18
    assert bundle.mdq_score == 5
    assert bundle.pcl5_score == 22
    assert bundle.has_screening_data is True
    assert set(bundle.instruments_available) == {"phq9", "gad7", "dass21", "mdq", "pcl5"}
    assert bundle.evidence_count == 5


def test_screening_context_partial_instruments():
    from app.services.db.models import ClinicalProfile

    db = _fake_db()
    profile = MagicMock(spec=ClinicalProfile)
    profile.phq9_score = 12
    profile.gad7_score = 9
    profile.dass21_depression_score = None
    profile.dass21_anxiety_score = None
    profile.dass21_stress_score = None
    profile.mdq_score = None
    profile.pcl5_score = None
    db.scalar.return_value = profile

    loader = AnalystContextLoader(db=db)
    bundle = loader.load_screening_context(user_id="u1")
    assert bundle.evidence_count == 2
    assert bundle.instruments_available == ["phq9", "gad7"]


def test_session_summary_bundle_empty():
    db = _fake_db()
    db.scalars.return_value.all.return_value = []
    loader = AnalystContextLoader(db=db)
    bundle = loader.load_session_summaries(user_id="u1", limit=5)
    assert bundle.evidence_count == 0
    assert bundle.record_ids == []


def test_load_all_returns_source_counts():
    db = _fake_db()
    db.scalars.return_value.all.return_value = []
    db.scalar.return_value = None
    loader = AnalystContextLoader(db=db)
    ctx = loader.load_all(user_id="u1", window_days=14)
    assert isinstance(ctx, AnalystContext)
    assert "mood_checkins" in ctx.source_counts
    assert "clinical_profiles" in ctx.source_counts
    assert "session_summaries_archive" in ctx.source_counts


def test_load_all_evidence_refs_include_record_ids():
    from app.services.db.models import MoodCheckin

    db = _fake_db()
    row = MagicMock(spec=MoodCheckin)
    row.checkin_id = "moodXYZ"
    row.mood = "buon_ba"
    row.triggers = []
    row.logged_date = date.today()
    db.scalars.return_value.all.return_value = [row]
    db.scalar.return_value = None
    loader = AnalystContextLoader(db=db)
    ctx = loader.load_all(user_id="u1", window_days=14)
    assert any("moodXYZ" in ref for ref in ctx.evidence_refs)


def test_context_loader_does_not_include_clinical_note_internal():
    db = _fake_db()
    db.scalars.return_value.all.return_value = []
    db.scalar.return_value = None
    loader = AnalystContextLoader(db=db)
    ctx = loader.load_all(user_id="u1", window_days=14)
    dumped = str(ctx)
    assert "clinical_note_internal" not in dumped
    assert "crisis_log" not in dumped


def test_batch_analyst_loads_clinical_profile():
    from app.services.analyst_agent import AnalystAgent

    with patch("app.services.analyst_agent.AnalystContextLoader") as MockLoader:
        mock_ctx = MagicMock()
        mock_ctx.mood.evidence_count = 0
        mock_ctx.mood.top_emotions = []
        mock_ctx.mood.top_triggers = []
        mock_ctx.screening.phq9_score = None
        mock_ctx.screening.gad7_score = None
        mock_ctx.screening.evidence_count = 0
        mock_ctx.screening.has_screening_data = False
        mock_ctx.screening.limitations = ["no_clinical_profile"]
        mock_ctx.session_summaries.evidence_count = 0
        mock_ctx.session_summaries.top_themes = []
        mock_ctx.source_counts = {"mood_checkins": 0, "clinical_profiles": 0, "session_summaries_archive": 0}
        mock_ctx.evidence_refs = []
        mock_ctx.total_evidence.return_value = 0
        MockLoader.return_value.load_all.return_value = mock_ctx

        db = MagicMock()
        AnalystAgent().generate_bundle_from_db(db=db, user_id="u1")
        MockLoader.assert_called_once_with(db=db)
        MockLoader.return_value.load_all.assert_called_once_with(user_id="u1", window_days=14)
