"""Contract tests for FriendAgent.

Proves that:
- Advisor advice only influences response via suggested_response_moves — never by injecting raw text.
- must_avoid constraints are enforced (no diagnosis language).
- used_advisor_ids only reflects advisors with should_use=True.
- Output always conforms to FriendAgentOutput schema.
- Default responses contain at most one question mark.
"""

from __future__ import annotations

import pytest

from app.services.friend_agent import FriendAgent
from app.services.safety_output_validator import count_questions
from app.services.safety_policy import evaluate_safety_policy
from app.services.schemas.contracts import (
    AdvisorAdvice,
    ContextPack,
    FriendAgentOutput,
    SafetyPolicyDecision,
)


def _make_policy(
    policy_action: str = "allow",
    risk_level: int = 0,
    distress_score: float = 0.0,
    must_avoid: list[str] | None = None,
) -> SafetyPolicyDecision:
    return SafetyPolicyDecision(
        policy_action=policy_action,  # type: ignore[arg-type]
        risk_level=risk_level,
        distress_score=distress_score,
        must_include=[],
        must_avoid=must_avoid or [],
        persona_style_strength=1.0,
        ui_support_mode="none",
        audit_required=False,
        reason_codes=[],
    )


def _minimal_pack(
    policy: SafetyPolicyDecision | None = None,
    persona: str = "dung_luong",
) -> ContextPack:
    return ContextPack(
        recent_messages=[],
        active_memory=None,
        onboarding_summary=None,
        mood_context=None,
        nutrition_context=None,
        screening_summary=None,
        resource_candidates=[],
        persona_context={"selected": persona},
        safety_policy=policy or _make_policy(),
    )


def test_friend_agent_uses_suggested_moves_from_advisor() -> None:
    """An advisor with should_use=True and suggested_response_moves should produce a valid response."""
    advice = AdvisorAdvice(
        advisor_id="deadline_advisor",
        should_use=True,
        confidence=0.85,
        suggested_response_moves=["Hỏi về tiến độ deadline của người dùng."],
        advice_to_friend=["Focus on the deadline stress."],
        evidence_refs=[],
        forbidden_moves=[],
    )
    pack = _minimal_pack()

    output = FriendAgent().compose(
        user_message="deadline dí quá, không biết phải làm sao",
        context_pack=pack,
        advisor_advice=[advice],
    )

    assert isinstance(output, FriendAgentOutput)
    assert output.final_text, "final_text must be non-empty when advisor provides moves"
    assert len(output.final_text.strip()) > 0


def test_advisor_final_text_field_not_used() -> None:
    """AdvisorAdvice schema must NOT have a 'final_text' field — only suggested_response_moves."""
    # Pydantic v2 uses model_fields; v1 uses __fields__. Support both.
    try:
        fields = set(AdvisorAdvice.model_fields.keys())
    except AttributeError:
        fields = set(AdvisorAdvice.__fields__.keys())

    assert "final_text" not in fields, (
        "AdvisorAdvice must not expose a 'final_text' field — advisor text must come "
        "through suggested_response_moves only, never by direct text injection."
    )


def test_must_avoid_diagnosis_label_is_enforced() -> None:
    """When must_avoid contains 'diagnosis_or_disorder_probability', response must not contain diagnosis words."""
    policy = evaluate_safety_policy("tôi bị bệnh gì vậy, có phải trầm cảm không")
    pack = _minimal_pack(policy=policy)

    output = FriendAgent().compose(
        user_message="tôi bị bệnh gì vậy, có phải trầm cảm không",
        context_pack=pack,
        advisor_advice=[],
    )

    lowered = output.final_text.lower()
    forbidden_words = ("trầm cảm", "rối loạn", "tôi bị bệnh")
    for word in forbidden_words:
        assert word not in lowered, (
            f"Diagnosis word '{word}' leaked into final_text despite must_avoid constraint: {output.final_text!r}"
        )


def test_used_advisor_ids_only_includes_should_use_true() -> None:
    """Only advisors with should_use=True appear in used_advisor_ids."""
    active_advice = AdvisorAdvice(
        advisor_id="active_advisor",
        should_use=True,
        confidence=0.9,
        suggested_response_moves=["Help user decompress after a hard day."],
        advice_to_friend=[],
        evidence_refs=[],
        forbidden_moves=[],
    )
    inactive_advice = AdvisorAdvice(
        advisor_id="inactive_advisor",
        should_use=False,
        confidence=0.6,
        suggested_response_moves=["Some irrelevant move."],
        advice_to_friend=[],
        evidence_refs=[],
        forbidden_moves=[],
    )
    pack = _minimal_pack()

    output = FriendAgent().compose(
        user_message="hôm nay mệt quá",
        context_pack=pack,
        advisor_advice=[active_advice, inactive_advice],
    )

    assert "active_advisor" in output.used_advisor_ids, (
        f"'active_advisor' (should_use=True) should be in used_advisor_ids: {output.used_advisor_ids}"
    )
    assert "inactive_advisor" not in output.used_advisor_ids, (
        f"'inactive_advisor' (should_use=False) must NOT be in used_advisor_ids: {output.used_advisor_ids}"
    )


def test_friend_output_conforms_to_schema() -> None:
    """FriendAgent.compose() must return a valid FriendAgentOutput with non-empty final_text."""
    pack = _minimal_pack()

    output = FriendAgent().compose(
        user_message="hôm nay chán quá, không biết sao nữa",
        context_pack=pack,
        advisor_advice=[],
    )

    # Pydantic validation runs at construction time; just confirm types.
    assert isinstance(output, FriendAgentOutput), (
        "compose() must return a FriendAgentOutput instance"
    )
    assert isinstance(output.final_text, str), "final_text must be a string"
    assert len(output.final_text) > 0, "final_text must be non-empty"
    # Pydantic would have raised ValidationError at construction if invalid.


def test_max_one_question_in_default_response() -> None:
    """A plain venting message with no advisors must produce at most one question in the response."""
    pack = _minimal_pack()

    output = FriendAgent().compose(
        user_message="hôm nay chán quá, ngồi không biết làm gì",
        context_pack=pack,
        advisor_advice=[],
    )

    q_count = count_questions(output.final_text)
    assert q_count <= 1, (
        f"Expected at most 1 question mark, got {q_count}: {output.final_text!r}"
    )
