"""Test that CounselingAdvisorService forwards case_refs into evidence_refs."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.counseling_advisor_service import CounselingAdvisorService
from app.services.schemas.advisors import (
    AdvisorCase,
    AdvisorCaseRetrievalResult,
)


def _make_case(case_id: str) -> AdvisorCase:
    return AdvisorCase(
        case_id=case_id,
        user_context="Mình cảm thấy quá tải, không biết bắt đầu từ đâu.",
        topic_tags=["overload"],
        emotional_state_tags=["exhausted"],
        recommended_approach="validate + one small step",
        counseling_goal="giảm tải cảm giác bế tắc",
        intervention_steps=["Thở sâu 3 lần", "Chọn 1 việc làm được ngay"],
        reflection_questions=["Phần nào khó nhất lúc này?"],
        do_say=["Mình nghe cậu đang rất mệt."],
        do_not_say=["diagnosis", "Chắc bạn bị stress mãn tính"],
    )


def test_evidence_refs_forwarded_when_cases_retrieved():
    """evidence_refs must contain the retrieved case IDs, not be empty."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[_make_case("case_001"), _make_case("case_002")],
        approved_only=True,
        fallback_used=False,
    )

    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance = service.build_guidance(
        user_message="Mình quá tải, không biết bắt đầu từ đâu.",
        interaction_need="advice",
    )
    advice = service.as_advisor_advice(guidance=guidance)

    assert "case_001" in advice.evidence_refs, (
        "case_refs from retrieval must be forwarded to evidence_refs"
    )
    assert "case_002" in advice.evidence_refs


def test_evidence_refs_empty_on_fallback():
    """evidence_refs must be [] when fallback heuristic is used (no cases retrieved)."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[],
        approved_only=True,
        fallback_used=True,
    )

    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance = service.build_guidance(
        user_message="mình cũng không biết nữa",
        interaction_need=None,
    )
    advice = service.as_advisor_advice(guidance=guidance)

    assert advice.evidence_refs == [], (
        "Fallback guidance must produce empty evidence_refs (no retrieved cases)"
    )


def test_confidence_higher_when_cases_retrieved():
    """confidence must be 0.82 when case_refs exist, 0.68 when fallback."""
    mock_retriever = MagicMock()

    # With cases
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[_make_case("case_abc")],
        approved_only=True,
        fallback_used=False,
    )
    service = CounselingAdvisorService(retriever=mock_retriever)
    guidance_with = service.build_guidance(user_message="test", interaction_need=None)
    advice_with = service.as_advisor_advice(guidance=guidance_with)
    assert advice_with.confidence == 0.82

    # Without cases
    mock_retriever.retrieve.return_value = AdvisorCaseRetrievalResult(
        cases=[], approved_only=True, fallback_used=True
    )
    guidance_without = service.build_guidance(user_message="test", interaction_need=None)
    advice_without = service.as_advisor_advice(guidance=guidance_without)
    assert advice_without.confidence == 0.68
