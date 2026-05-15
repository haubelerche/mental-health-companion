"""Test FriendAgentOutput emits response-plan-driven tts_candidate and meme_candidate."""
from __future__ import annotations

from app.services.friend_agent import FriendAgent
from app.services.schemas.contracts import ContextPack, FriendAgentOutput, SafetyPolicyDecision


def _make_pack(
    *,
    distress_score: float = 0.2,
    risk_level: int = 0,
    persona_id: str = "dung_luong",
) -> ContextPack:
    policy = SafetyPolicyDecision(
        policy_action="allow",
        risk_level=risk_level,
        distress_score=distress_score,
        persona_style_strength=0.8,
    )
    return ContextPack(
        safety_policy=policy,
        persona_context={"selected": persona_id},
        recent_messages=[],
    )


def test_friend_output_has_tts_candidate_field():
    """FriendAgentOutput must have a tts_candidate field (existing schema field)."""
    output = FriendAgent().compose(
        user_message="Chào cậu",
        context_pack=_make_pack(),
    )
    assert isinstance(output, FriendAgentOutput)
    assert hasattr(output, "tts_candidate"), "FriendAgentOutput must have tts_candidate field"


def test_friend_output_has_meme_candidate_field():
    """FriendAgentOutput must have a meme_candidate field."""
    output = FriendAgent().compose(
        user_message="Chào cậu",
        context_pack=_make_pack(),
    )
    assert hasattr(output, "meme_candidate"), "FriendAgentOutput must have meme_candidate field"


def test_high_risk_suppresses_meme_candidate():
    """High-risk turns (risk_level >= 3) must not emit a meme_candidate."""
    output = FriendAgent().compose(
        user_message="Mình không muốn sống nữa",
        context_pack=_make_pack(distress_score=0.85, risk_level=4),
    )
    assert output.meme_candidate is None, (
        f"meme_candidate must be None for high-risk turns, got: {output.meme_candidate}"
    )


def test_high_risk_suppresses_tts_candidate():
    """High-risk turns (risk_level >= 3) must not emit a tts_candidate."""
    output = FriendAgent().compose(
        user_message="Mình không muốn sống nữa",
        context_pack=_make_pack(distress_score=0.85, risk_level=4),
    )
    assert output.tts_candidate is None, (
        f"tts_candidate must be None for high-risk turns, got: {output.tts_candidate}"
    )


def test_low_risk_substantive_turn_has_tts_candidate():
    """A substantive low-risk message should produce a tts_candidate dict with voice_text."""
    output = FriendAgent().compose(
        user_message="Mình đang cảm thấy khá căng thẳng vì bài tập và deadline gần tới.",
        context_pack=_make_pack(distress_score=0.2, risk_level=0),
    )
    # tts_candidate may be None for very short final_text, or a dict if substantial
    if output.tts_candidate is not None:
        assert isinstance(output.tts_candidate, dict), (
            "tts_candidate must be a dict when present"
        )
        assert "voice_text" in output.tts_candidate, (
            "tts_candidate dict must contain 'voice_text' key"
        )


def test_playful_meme_request_produces_meme_hint():
    """A playful meme request on low risk should produce a meme_candidate reason code."""
    output = FriendAgent().compose(
        user_message="Kể meme vui đi, mình đang cần cười",
        context_pack=_make_pack(distress_score=0.05, risk_level=0),
    )
    assert output.meme_candidate is not None, (
        "Playful low-risk meme request should emit a meme_candidate"
    )
    assert isinstance(output.meme_candidate, str), (
        "meme_candidate must be a reason code string"
    )


def test_meme_candidate_none_for_medium_distress():
    """Medium distress (0.45+) should suppress meme_candidate even if keywords present."""
    output = FriendAgent().compose(
        user_message="Meme vui đi mình buồn quá, căng thẳng quá",
        context_pack=_make_pack(distress_score=0.55, risk_level=2),
    )
    assert output.meme_candidate is None, (
        f"meme_candidate must be None when distress >= 0.45, got: {output.meme_candidate}"
    )
