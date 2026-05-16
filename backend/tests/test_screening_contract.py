from __future__ import annotations

from datetime import datetime

from app.services.clinical_profile import (
    SCREENING_ANSWER_OPTIONS_VERSION,
    SCREENING_QUESTION_TEXT_VERSION,
    apply_screening_to_clinical_profile,
    build_screening_answer_payload,
    compute_screening_severity,
)
from app.services.db.models import ClinicalProfile


def test_screening_answer_payload_is_reconstructable() -> None:
    submitted_at = datetime(2026, 5, 11, 9, 30, 0)
    payload = build_screening_answer_payload(
        user_id="user_1",
        instrument_id="phq9",
        answers={"q0": 1, "q1": 3},
        submitted_at=submitted_at,
        session_id="sess_1",
        locale="vi-VN",
    )

    assert payload["user_id"] == "user_1"
    assert payload["screening_type"] == "phq9"
    assert payload["session_id"] == "sess_1"
    assert payload["locale"] == "vi-VN"
    assert payload["question_text_version"] == SCREENING_QUESTION_TEXT_VERSION["phq9"]
    assert payload["answer_options_version"] == SCREENING_ANSWER_OPTIONS_VERSION
    assert payload["submitted_answer_map"] == {"q0": 1, "q1": 3}
    assert payload["responses"][0]["question_key"] == "q0"
    assert payload["responses"][0]["question_text"]
    assert payload["responses"][0]["answer_value"] == 1
    assert payload["responses"][0]["answer_label"] == "Một chút / Vài ngày"


def test_clinical_profile_stores_derived_summary_only() -> None:
    profile = ClinicalProfile(profile_id="clin_1", user_id="user_1", crisis_level=0)
    scored_at = datetime(2026, 5, 11, 10, 0, 0)

    apply_screening_to_clinical_profile(
        profile=profile,
        instrument_id="gad7",
        raw_score=12,
        scored_at=scored_at,
    )

    assert profile.gad7_score == 12
    assert profile.gad7_coverage["covered"] is True
    assert profile.gad7_coverage["score_type"] == "questionnaire"
    assert profile.score_source == "questionnaire"
    assert profile.model_version == "questionnaire_v1"
    assert profile.last_scored_at == scored_at


def test_screening_severity_contract_matches_frontend_labels() -> None:
    assert compute_screening_severity(instrument_id="phq9", raw_score=2) == "minimal"
    assert compute_screening_severity(instrument_id="phq9", raw_score=7) == "mild"
    assert compute_screening_severity(instrument_id="phq9", raw_score=12) == "moderate"
    assert compute_screening_severity(instrument_id="phq9", raw_score=17) == "moderately_severe"
    assert compute_screening_severity(instrument_id="phq9", raw_score=22) == "severe"
    assert compute_screening_severity(instrument_id="gad7", raw_score=3) == "minimal"
    assert compute_screening_severity(instrument_id="gad7", raw_score=8) == "mild"
    assert compute_screening_severity(instrument_id="gad7", raw_score=13) == "moderate"
    assert compute_screening_severity(instrument_id="gad7", raw_score=18) == "severe"
