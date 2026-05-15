"""Integration tests: prove both direct and advisor-assisted paths call the same Friend finalizer.

Both ChatOrchestrator.compose_friend_final_text() calls must:
- Return a FriendComposerResult with non-empty final_text.
- Never leak internal field names into the response text.
"""

from __future__ import annotations

import pytest

from app.services.chat_orchestrator import ChatOrchestrator, FriendComposerResult
from app.services.safety_policy import evaluate_safety_policy
from app.services.schemas.contracts import AdvisorAdvice, ContextPack

_INTERNAL_FIELD_NAMES = (
    "advisor_id",
    "evidence_refs",
    "distress_score",
    "risk_level",
    "safety_tier",
    "reason_codes",
)


def _minimal_pack(user_message: str = "hôm nay chán quá") -> ContextPack:
    policy = evaluate_safety_policy(user_message)
    return ContextPack(
        recent_messages=[],
        active_memory=None,
        onboarding_summary=None,
        mood_context=None,
        nutrition_context=None,
        screening_summary=None,
        resource_candidates=[],
        persona_context={"selected": "dung_luong"},
        safety_policy=policy,
    )


def test_direct_path_calls_friend_agent_compose() -> None:
    """Direct path (no advisors) must return a non-empty FriendComposerResult."""
    pack = _minimal_pack("hôm nay chán quá")
    result = ChatOrchestrator.compose_friend_final_text(
        user_message="hôm nay chán quá",
        context_pack=pack,
        advisor_advice=[],
    )

    assert isinstance(result, FriendComposerResult)
    assert result.final_text, "final_text must be non-empty"
    assert len(result.final_text.strip()) > 0


def test_advisor_assisted_path_calls_same_finalizer() -> None:
    """Advisor-assisted path must return a non-empty text and track the used advisor id."""
    pack = _minimal_pack("hôm nay mệt quá, không muốn làm gì hết")
    advice = AdvisorAdvice(
        advisor_id="empathy_advisor",
        should_use=True,
        confidence=0.8,
        suggested_response_moves=["Reflect on the user's feeling of tiredness."],
        advice_to_friend=["Validate the exhaustion first."],
        evidence_refs=[],
        forbidden_moves=[],
    )

    result = ChatOrchestrator.compose_friend_final_text(
        user_message="hôm nay mệt quá, không muốn làm gì hết",
        context_pack=pack,
        advisor_advice=[advice],
    )

    assert isinstance(result, FriendComposerResult)
    assert result.final_text, "final_text must be non-empty"
    assert "empathy_advisor" in result.used_advisor_ids, (
        f"used_advisor_ids should contain 'empathy_advisor', got {result.used_advisor_ids}"
    )


def test_advisor_advice_with_should_use_false_is_ignored() -> None:
    """Advice with should_use=False must NOT appear in used_advisor_ids."""
    pack = _minimal_pack("hôm nay chán quá")
    advice = AdvisorAdvice(
        advisor_id="ignored_advisor",
        should_use=False,
        confidence=0.9,
        suggested_response_moves=["Do something strange."],
        advice_to_friend=[],
        evidence_refs=[],
        forbidden_moves=[],
    )

    result = ChatOrchestrator.compose_friend_final_text(
        user_message="hôm nay chán quá",
        context_pack=pack,
        advisor_advice=[advice],
    )

    assert isinstance(result, FriendComposerResult)
    assert result.final_text, "final_text must be non-empty"
    assert result.used_advisor_ids == [], (
        f"used_advisor_ids should be empty when all advisors have should_use=False, got {result.used_advisor_ids}"
    )


def test_all_advisors_timeout_still_produces_response() -> None:
    """Empty advisor list (simulating all timeouts) must still produce a valid response."""
    pack = _minimal_pack("hôm nay chán quá")

    result = ChatOrchestrator.compose_friend_final_text(
        user_message="hôm nay chán quá",
        context_pack=pack,
        advisor_advice=[],
    )

    assert isinstance(result, FriendComposerResult)
    assert result.final_text, "final_text must be non-empty even when no advisors provide advice"
    assert len(result.final_text.strip()) > 0


def test_final_text_never_contains_internal_field_names() -> None:
    """The final response must not expose any internal system field names."""
    pack = _minimal_pack("hôm nay chán quá, deadline dí mà não đứng hình")
    advice = AdvisorAdvice(
        advisor_id="cbt_pattern_advisor",
        should_use=True,
        confidence=0.75,
        suggested_response_moves=["Help user identify cognitive distortions around deadline pressure."],
        evidence_refs=["case_001"],
        advice_to_friend=["Focus on one small step."],
        forbidden_moves=[],
    )

    result = ChatOrchestrator.compose_friend_final_text(
        user_message="hôm nay chán quá, deadline dí mà não đứng hình",
        context_pack=pack,
        advisor_advice=[advice],
    )

    lowered = result.final_text.lower()
    for field in _INTERNAL_FIELD_NAMES:
        assert field not in lowered, (
            f"Internal field '{field}' leaked into final_text: {result.final_text!r}"
        )
