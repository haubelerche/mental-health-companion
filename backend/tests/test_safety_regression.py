"""Safety regression tests — Plan 10.

Verify:
- SOS triggers bypass persona stylization (safety_override=True)
- Crush cannot activate during elevated distress or with dependency signal
- Cún/Mèo deactivate at their configured thresholds
- Knowledge content that implies diagnosis fails content review
- Unsafe memory candidates are rejected by guardrail
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Persona router — safety gate ordering
# ---------------------------------------------------------------------------

def test_sos_trigger_forces_ban_than_with_safety_override():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="cun",
        requested_persona_id="cun",
        distress=0.9,
        sos_triggered=True,
        is_unlocked=True,
    )
    assert decision.target_persona_id == "ban_than"
    assert decision.safety_override is True


def test_crush_blocked_at_distress_060():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="crush",
        distress=0.60,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert decision.target_persona_id != "crush"


def test_crush_blocked_with_dependency_signal():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="crush",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=True,
        dependency_signal=True,
    )
    assert decision.target_persona_id != "crush"


def test_cun_blocked_at_distress_050():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="cun",
        distress=0.50,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert decision.target_persona_id != "cun"


def test_meo_blocked_at_distress_056():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="meo",
        distress=0.56,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert decision.target_persona_id != "meo"


def test_cun_accessible_below_threshold():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="cun",
        distress=0.30,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert decision.target_persona_id == "cun"


def test_crush_requires_unlock_reason_is_locked():
    from app.personas.router import route_persona
    decision = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="crush",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=False,
    )
    assert decision.target_persona_id != "crush"
    # The blocked_reason or reason should indicate progression lock
    reason = (decision.blocked_reason or decision.reason or "").lower()
    assert "lock" in reason or "progress" in reason


def test_alias_nguoi_yeu_resolves_to_crush():
    from app.personas.aliases import resolve_alias
    assert resolve_alias("nguoi_yeu") == "crush"


def test_unknown_alias_returns_original():
    """resolve_alias returns original string for unknown aliases (no silent default)."""
    from app.personas.aliases import resolve_alias
    result = resolve_alias("nguoi_la")
    assert isinstance(result, str)
    assert result == "nguoi_la"


# ---------------------------------------------------------------------------
# Knowledge content review
# ---------------------------------------------------------------------------

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
        content_markdown=(
            "Thở sâu có thể giúp giảm căng thẳng. "
            "Hít vào 4 giây, nín thở 4 giây, thở ra 4 giây."
        ),
    )
    assert result["approved"] is True


def test_knowledge_sos_content_fails():
    from app.knowledge.content_review import review_knowledge_card
    result = review_knowledge_card(
        title="Khủng hoảng",
        content_markdown="Nếu bạn đang nghĩ đến việc tự tử hãy gọi ngay đường dây hỗ trợ.",
    )
    assert result["approved"] is False


# ---------------------------------------------------------------------------
# Memory card guardrail
# ---------------------------------------------------------------------------

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
        memory_type="personal_insight",  # not in VALID_TYPES
        title="Title",
        content="Some valid content here.",
    )
    assert result["approved"] is False
    assert result["rejection_reason"] == "invalid_memory_type"
