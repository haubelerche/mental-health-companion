"""Safety regression tests."""

from __future__ import annotations

from app.services.output_policy_validator import validate_final_response
from app.services.schemas.contracts import SafetyPolicyDecision


def test_sos_trigger_forces_default_with_safety_override():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="hau_luong",
        requested_persona_id="hau_luong",
        distress=0.9,
        sos_triggered=True,
        is_unlocked=True,
    )
    assert decision.target_persona_id == "dung_luong"
    assert decision.safety_override is True


def test_hau_blocked_at_distress_060():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="dung_luong",
        requested_persona_id="hau_luong",
        distress=0.60,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert decision.target_persona_id != "hau_luong"


def test_hau_blocked_with_dependency_signal():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="dung_luong",
        requested_persona_id="hau_luong",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=True,
        dependency_signal=True,
    )
    assert decision.target_persona_id != "hau_luong"


def test_hau_accessible_below_threshold_when_unlocked():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="dung_luong",
        requested_persona_id="hau_luong",
        distress=0.30,
        sos_triggered=False,
        is_unlocked=True,
        user_explicit=True,
    )
    assert decision.target_persona_id == "hau_luong"


def test_hau_requires_unlock_reason_is_locked():
    from app.personas.router import route_persona

    decision = route_persona(
        current_persona_id="dung_luong",
        requested_persona_id="hau_luong",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=False,
    )
    assert decision.target_persona_id != "hau_luong"
    reason = (decision.blocked_reason or decision.reason or "").lower()
    assert "lock" in reason or "progress" in reason


def test_romantic_framing_aliases_never_resolve_to_hau():
    """Romantic-framing inputs (crush, persona_crush, nguoi_yeu, lover) must
    not silently route into Hậu — Hậu is an introverted quiet persona, not a
    romantic one."""
    from app.personas.aliases import is_known_persona, resolve_alias

    for romantic in ("crush", "persona_crush", "nguoi_yeu", "lover", "Crush", "CRUSH"):
        resolved = resolve_alias(romantic)
        assert resolved != "hau_luong", f"{romantic} must not alias to hau_luong"
        assert not is_known_persona(romantic), (
            f"{romantic} must be treated as unknown and rejected by the router"
        )


def test_unknown_alias_returns_original():
    from app.personas.aliases import resolve_alias

    result = resolve_alias("nguoi_la")
    assert isinstance(result, str)
    assert result == "nguoi_la"


def test_knowledge_content_with_diagnosis_fails():
    from app.knowledge.content_review import review_knowledge_card

    result = review_knowledge_card(
        title="Rối loạn lo âu",
        content_markdown="Bạn bị rối loạn lo âu lan tỏa. Đây là chẩn đoán chính thức.",
    )
    assert result["approved"] is False
    assert result["rejection_reason"] is not None


def test_knowledge_safe_content_passes():
    from app.knowledge.content_review import review_knowledge_card

    result = review_knowledge_card(
        title="Kỹ thuật thở",
        content_markdown="Thở sâu có thể giúp giảm căng thẳng. Hít vào 4 giây, nín thở 4 giây, thở ra 4 giây.",
    )
    assert result["approved"] is True


def test_knowledge_sos_content_fails():
    from app.knowledge.content_review import review_knowledge_card

    result = review_knowledge_card(
        title="Khủng hoảng",
        content_markdown="Nếu bạn đang nghĩ đến việc tự tử hãy gọi ngay đường dây hỗ trợ.",
    )
    assert result["approved"] is False


def test_memory_guardrail_rejects_diagnosis_claim():
    from app.memory.guardrail import review_memory_candidate

    result = review_memory_candidate(
        memory_type="emotional_pattern",
        title="Chẩn đoán",
        content="Serene nói tôi bị trầm cảm.",
    )
    assert result["approved"] is False


def test_memory_guardrail_rejects_sos_content():
    from app.memory.guardrail import review_memory_candidate

    result = review_memory_candidate(
        memory_type="current_stressor",
        title="Cảm xúc",
        content="Tôi không muốn sống nữa và đang nghĩ đến việc tự làm hại bản thân.",
    )
    assert result["approved"] is False


def test_memory_guardrail_approves_safe_content():
    from app.memory.guardrail import review_memory_candidate

    result = review_memory_candidate(
        memory_type="preference",
        title="Thói quen",
        content="Tôi thích đọc sách vào buổi tối.",
    )
    assert result["approved"] is True


def test_memory_guardrail_rejects_empty_content():
    from app.memory.guardrail import review_memory_candidate

    result = review_memory_candidate(
        memory_type="preference",
        title="Empty",
        content="",
    )
    assert result["approved"] is False
    assert result["rejection_reason"] == "empty_content"


def test_memory_guardrail_rejects_invalid_type():
    from app.memory.guardrail import review_memory_candidate

    result = review_memory_candidate(
        memory_type="personal_insight",
        title="Title",
        content="Some valid content here.",
    )
    assert result["approved"] is False
    assert result["rejection_reason"] == "invalid_memory_type"


def test_output_policy_validator_blocks_harmful_method_detail() -> None:
    verdict = validate_final_response("Use pills, then mix alcohol, then lie down alone.")
    assert verdict.verdict == "block"
    assert "harmful_method_detail" in verdict.reason_codes


def test_output_policy_validator_rewrite_required_for_too_many_questions() -> None:
    policy = SafetyPolicyDecision(
        policy_action="supportive_continuation",
        risk_level=3,
        distress_score=0.6,
        must_include=["short_validation"],
        must_avoid=["multiple_questions"],
        persona_style_strength=0.2,
        ui_support_mode="optional_sheet",
        audit_required=False,
        reason_codes=["distress_disclosure"],
    )
    verdict = validate_final_response(
        "Minh nghe ban dang rat met. Dieu gi xay ra? Ban muon ke them khong?",
        policy_decision=policy,
    )
    assert verdict.verdict == "rewrite_required"
    assert "too_many_questions" in verdict.reason_codes
