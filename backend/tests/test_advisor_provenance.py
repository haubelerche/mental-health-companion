"""Unit tests for advisor evidence provenance (no DB, no network).

Verifies that:
- EmpathyAdvisor and CBTPatternAdvisor populate evidence_refs from JSONL records.
- AdvisorAdvice schema has no user-facing text field.
- CounselingAdvisorService.as_advisor_advice() propagates case_refs to evidence_refs.
- All evidence_refs items are strings.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.advisors.cbt_pattern import CBTPatternAdvisor
from app.advisors.empathy import EmpathyAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.advisors.nutrition_support import NutritionSupportAdvisor
from app.advisors.reflection import ReflectionAdvisor
from app.advisors.strategy_resource import StrategyResourceAdvisor
from app.services.counseling_advisor_service import CounselingAdvisorService
from app.services.schemas.advisors import CounselingGuidance
from app.services.schemas.contracts import AdvisorAdvice

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_MESSAGES = {
    "empathy": "mình cảm thấy rất mệt mỏi và kiệt sức, không biết phải làm sao",
    "cbt": "lỗi tại mình, mình thật vô dụng, do mình mà mọi chuyện hỏng hết",
    "simple": "hôm nay mình không biết phải làm gì",
}


# ---------------------------------------------------------------------------
# Test 1: EmpathyAdvisor populates evidence_refs
# ---------------------------------------------------------------------------


class TestEmpathyAdvisorEvidenceRefsPopulatedWhenRecordsFound:
    def test_empathy_advisor_evidence_refs_populated_when_records_found(self) -> None:
        advisor = EmpathyAdvisor()
        result = advisor.run(user_message=_USER_MESSAGES["empathy"])
        # If no JSONL records matched, evidence_refs may be empty — skip rather than fail.
        if not result.should_use:
            pytest.skip("No JSONL records matched the query — JSONL data may be empty in this env")
        assert isinstance(result.evidence_refs, list), "evidence_refs must be a list"
        assert len(result.evidence_refs) > 0, "evidence_refs must be non-empty when records are found"
        for ref in result.evidence_refs:
            assert isinstance(ref, str) and ref, "each evidence_ref must be a non-empty string"


# ---------------------------------------------------------------------------
# Test 2: CBTPatternAdvisor populates evidence_refs
# ---------------------------------------------------------------------------


class TestCBTPatternAdvisorEvidenceRefsPopulated:
    def test_cbt_pattern_advisor_evidence_refs_populated(self) -> None:
        advisor = CBTPatternAdvisor()
        result = advisor.run(user_message=_USER_MESSAGES["cbt"])
        if not result.should_use:
            pytest.skip("CBTPatternAdvisor did not match — JSONL data may be empty in this env")
        assert isinstance(result.evidence_refs, list), "evidence_refs must be a list"
        assert len(result.evidence_refs) > 0, "evidence_refs must be non-empty when records are found"
        for ref in result.evidence_refs:
            assert isinstance(ref, str) and ref, "each evidence_ref must be a non-empty string"


# ---------------------------------------------------------------------------
# Test 3: AdvisorAdvice model_fields has no user-facing text field
# ---------------------------------------------------------------------------

_FORBIDDEN_FIELD_NAMES = {"final_text", "reply", "message_to_user"}


class TestAdvisorAdviceNeverHasFinalTextField:
    def _all_advisor_instances(self) -> list:
        # Use a shared real store so JSONL is loaded once for all advisors.
        store = AdvisorKnowledgeStore()
        return [
            EmpathyAdvisor(knowledge_store=store),
            CBTPatternAdvisor(knowledge_store=store),
            ReflectionAdvisor(knowledge_store=store),
            NutritionSupportAdvisor(knowledge_store=store),
            StrategyResourceAdvisor(knowledge_store=store),
        ]

    def test_advisor_advice_never_has_final_text_field(self) -> None:
        defined_fields = set(AdvisorAdvice.model_fields.keys())
        forbidden_present = _FORBIDDEN_FIELD_NAMES & defined_fields
        assert not forbidden_present, (
            f"AdvisorAdvice schema must not contain user-facing fields: {sorted(forbidden_present)}"
        )

    def test_advisor_run_results_have_no_final_text_field(self) -> None:
        """Verify that actual AdvisorAdvice instances returned by each advisor have no forbidden attrs."""
        for advisor in self._all_advisor_instances():
            result = advisor.run(user_message=_USER_MESSAGES["simple"])
            for field_name in _FORBIDDEN_FIELD_NAMES:
                assert not hasattr(result, field_name), (
                    f"{advisor.__class__.__name__} returned AdvisorAdvice with forbidden field '{field_name}'"
                )


# ---------------------------------------------------------------------------
# Test 4: CounselingAdvisorService.as_advisor_advice() propagates case_refs
# ---------------------------------------------------------------------------


class TestCounselingAdvisorServicePropagatesCaseRefs:
    def test_counseling_advisor_service_propagates_case_refs(self) -> None:
        mock_guidance = CounselingGuidance(
            case_understanding="Test case understanding",
            likely_patterns=["self_blame"],
            response_goal="help user",
            recommended_moves=["validate briefly", "offer one small step"],
            one_reflection_question="What specifically happened?",
            one_practical_step="Pick one small task",
            avoid=["diagnosis"],
            case_refs=["case_001", "case_002"],
            metadata={"source": "test"},
        )
        # Construct service without hitting DB (retriever not called here).
        mock_retriever = MagicMock()
        service = CounselingAdvisorService(retriever=mock_retriever)
        result = service.as_advisor_advice(guidance=mock_guidance)

        assert isinstance(result, AdvisorAdvice)
        assert result.evidence_refs == ["case_001", "case_002"], (
            f"evidence_refs should propagate case_refs; got {result.evidence_refs!r}"
        )

    def test_counseling_advisor_service_empty_case_refs_yields_empty_evidence_refs(self) -> None:
        mock_guidance = CounselingGuidance(
            case_understanding="Heuristic fallback",
            likely_patterns=[],
            response_goal="help user",
            recommended_moves=[],
            avoid=[],
            case_refs=[],
            metadata={"source": "heuristic"},
        )
        mock_retriever = MagicMock()
        service = CounselingAdvisorService(retriever=mock_retriever)
        result = service.as_advisor_advice(guidance=mock_guidance)

        assert result.evidence_refs == [], (
            f"evidence_refs should be empty when case_refs is empty; got {result.evidence_refs!r}"
        )


# ---------------------------------------------------------------------------
# Test 5: evidence_refs are strings
# ---------------------------------------------------------------------------


class TestAdvisorEvidenceRefsAreStrings:
    def test_advisor_evidence_refs_are_strings(self) -> None:
        """For any advisor that returns evidence, all items in evidence_refs are strings."""
        store = AdvisorKnowledgeStore()
        advisors = [
            EmpathyAdvisor(knowledge_store=store),
            CBTPatternAdvisor(knowledge_store=store),
            ReflectionAdvisor(knowledge_store=store),
            NutritionSupportAdvisor(knowledge_store=store),
            StrategyResourceAdvisor(knowledge_store=store),
        ]
        messages = [
            _USER_MESSAGES["empathy"],
            _USER_MESSAGES["cbt"],
            _USER_MESSAGES["simple"],
        ]
        for advisor in advisors:
            for msg in messages:
                result = advisor.run(user_message=msg)
                assert isinstance(result.evidence_refs, list), (
                    f"{advisor.__class__.__name__}.evidence_refs is not a list"
                )
                for ref in result.evidence_refs:
                    assert isinstance(ref, str), (
                        f"{advisor.__class__.__name__} returned non-string evidence_ref: {ref!r} (type {type(ref).__name__})"
                    )
                    assert ref, (
                        f"{advisor.__class__.__name__} returned empty-string evidence_ref"
                    )

    def test_counseling_advisor_case_refs_propagated_as_strings(self) -> None:
        """Verify as_advisor_advice() coerces case_refs to strings."""
        mock_guidance = CounselingGuidance(
            case_understanding="Test",
            likely_patterns=[],
            response_goal="test",
            recommended_moves=[],
            avoid=[],
            case_refs=["alpha", "beta", "gamma"],
            metadata={},
        )
        mock_retriever = MagicMock()
        service = CounselingAdvisorService(retriever=mock_retriever)
        result = service.as_advisor_advice(guidance=mock_guidance)
        for ref in result.evidence_refs:
            assert isinstance(ref, str), f"evidence_ref {ref!r} is not a string"
