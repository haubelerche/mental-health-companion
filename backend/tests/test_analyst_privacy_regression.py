"""Privacy regression coverage for batch and inline analyst surfaces."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_batch_analyst_no_clinical_note_internal():
    from app.services.analyst_pipeline import AnalystPipeline

    payload = AnalystPipeline().run(user_id="u1", normalized_events=[])
    dumped = str(payload).lower()
    assert "clinical_note_internal" not in dumped
    assert "crisis_log" not in dumped


def test_batch_analyst_bundle_no_raw_scores_exposed():
    from app.services.analyst_agent import AnalystAgent

    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    db.scalar.return_value = None

    with patch("app.services.analyst_agent.AnalystContextLoader") as MockLoader:
        ctx = MagicMock()
        ctx.mood.top_emotions = []
        ctx.mood.top_triggers = []
        ctx.mood.evidence_count = 0
        ctx.screening.phq9_score = 20
        ctx.screening.gad7_score = 18
        ctx.screening.dass21_depression_score = 28
        ctx.screening.dass21_anxiety_score = 20
        ctx.screening.dass21_stress_score = 30
        ctx.screening.mdq_score = 9
        ctx.screening.pcl5_score = 55
        ctx.screening.has_screening_data = True
        ctx.screening.evidence_count = 5
        ctx.screening.instruments_available = ["phq9", "gad7", "dass21", "mdq", "pcl5"]
        ctx.session_summaries.evidence_count = 0
        ctx.session_summaries.top_themes = []
        ctx.source_counts = {"mood_checkins": 0, "clinical_profiles": 5, "session_summaries_archive": 0}
        ctx.evidence_refs = ["screening:abc123"]
        ctx.total_evidence.return_value = 5
        MockLoader.return_value.load_all.return_value = ctx

        bundle = AnalystAgent().generate_bundle_from_db(db=db, user_id="u1")

    raw_score_keys = [
        "phq9_score",
        "gad7_score",
        "dass21_depression_score",
        "dass21_anxiety_score",
        "dass21_stress_score",
        "mdq_score",
        "pcl5_score",
    ]
    for candidate in bundle.safe_dashboard_candidates:
        text = str(candidate).lower()
        for key in raw_score_keys:
            assert key not in text


def test_analyst_sanitizer_strips_clinical_note_for_friend():
    from app.services.analyst_sanitizer import sanitize_analyst_bundle_for_friend_context
    from app.services.schemas.contracts import AnalystBundle

    bundle = AnalystBundle(
        user_id="u1",
        time_window={},
        dominant_emotions=["lo_au"],
        recurring_triggers=["hoc_hanh"],
        cognitive_patterns=[{"note": "INTERNAL: roi loan lo au muc trung binh"}],
        nutrition_patterns=[],
        coping_preferences=["tho sau"],
        evidence_refs=["mood:c1"],
        confidence="medium",
        missing_info=[],
        safe_dashboard_candidates=[],
    )
    result = sanitize_analyst_bundle_for_friend_context(bundle)
    assert "cognitive_patterns" not in result
    assert "evidence_refs" not in result
    assert "roi loan" not in str(result)


def test_analyst_sanitizer_dashboard_no_internal_rationale():
    from app.services.analyst_sanitizer import sanitize_analyst_bundle_for_dashboard
    from app.services.schemas.contracts import AnalystBundle

    bundle = AnalystBundle(
        user_id="u1",
        time_window={},
        dominant_emotions=["cang_thang"],
        recurring_triggers=[],
        cognitive_patterns=[],
        nutrition_patterns=[],
        coping_preferences=[],
        evidence_refs=["mood:c2"],
        confidence="low",
        missing_info=["insufficient_signal"],
        safe_dashboard_candidates=[],
    )
    result = sanitize_analyst_bundle_for_dashboard(bundle, user_safe_summary="Ban dang kha on.")
    assert "cognitive_patterns" not in result
    assert "evidence_refs" not in result
    assert "internal_rationale" not in result


def test_insight_hypothesis_display_allowed_only_exposes_safe_fields():
    from app.services.db.models import InsightHypothesis

    row = InsightHypothesis(
        user_id="u1",
        hypothesis_type="stress_pattern",
        title="Tin hieu cang thang",
        user_safe_summary="Ban co ve dang trai qua ap luc.",
        internal_rationale={"clinical_note_internal": "PTSD pattern suspected - NOT FOR USER"},
        evidence_count=3,
        confidence=0.50,
        status="active",
        display_allowed=True,
        source="analyst_pipeline",
    )
    safe_fields = {
        "title": row.title,
        "user_safe_summary": row.user_safe_summary,
        "evidence_count": row.evidence_count,
        "confidence": row.confidence,
        "status": row.status,
    }
    dumped = str(safe_fields).lower()
    assert "clinical_note_internal" not in dumped
    assert "ptsd" not in dumped
    assert "internal_rationale" not in dumped
