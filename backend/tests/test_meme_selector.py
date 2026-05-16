"""Tests for meme_selector.maybe_select_meme_suggestion() safety gates and selection logic."""

from __future__ import annotations

import pytest

from app.services.meme_selector import MemeSuggestion, maybe_select_meme_suggestion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_KWARGS = dict(
    persona_id="dung_luong",
    safety_tier="normal",
    distress_score=0.1,
    session_id="test-session-abc",
    assistant_turn_index=2,
    cooldown_turns=1,
    user_message="hôm nay vui quá",
    assistant_text="",
)


def _call(**overrides) -> MemeSuggestion | None:
    kwargs = {**_BASE_KWARGS, **overrides}
    return maybe_select_meme_suggestion(**kwargs)


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


def test_low_risk_dung_luong_returns_meme_candidate():
    result = _call()
    assert result is not None, "Expected a MemeSuggestion for eligible dung_luong turn"


# ---------------------------------------------------------------------------
# 2–3. Distress gate
# ---------------------------------------------------------------------------


def test_high_distress_suppresses_meme():
    result = _call(distress_score=0.7)
    assert result is None


def test_high_distress_boundary_suppresses():
    """Boundary value 0.5 must be suppressed (>= 0.5)."""
    result = _call(distress_score=0.5)
    assert result is None


# ---------------------------------------------------------------------------
# 4. Low distress boundary still allows
# ---------------------------------------------------------------------------


def test_low_distress_boundary_allows():
    result = _call(distress_score=0.49)
    assert result is not None


# ---------------------------------------------------------------------------
# 5–6. Persona gate
# ---------------------------------------------------------------------------


def test_non_dung_persona_suppresses_meme():
    result = _call(persona_id="dat_le")
    assert result is None


def test_hau_persona_suppresses_meme():
    result = _call(persona_id="hau_luong")
    assert result is None


# ---------------------------------------------------------------------------
# 7. Safety-tier gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tier", ["elevated", "high"])
def test_non_normal_safety_tier_suppresses(tier: str):
    result = _call(safety_tier=tier)
    assert result is None


# ---------------------------------------------------------------------------
# 8. Crisis hint in message suppresses
# The _HOLD_MEME_HINTS set contains: "tu tu" (tự tử), "chet" (chết), etc.
# We pick "tu tu" and "chet" which are ASCII-normalized forms of Vietnamese
# crisis words stored in the hints set.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("crisis_token", ["tu tu", "chet"])
def test_crisis_hint_in_message_suppresses_meme(crisis_token: str):
    result = _call(user_message=crisis_token)
    assert result is None


# ---------------------------------------------------------------------------
# 9. Required fields on MemeSuggestion
# ---------------------------------------------------------------------------


def test_meme_suggestion_has_required_fields():
    result = _call()
    assert result is not None
    assert "id" in result, "MemeSuggestion must have an 'id' field"
    assert "image_path" in result, "MemeSuggestion must have an 'image_path' field"
    assert result["image_path"].endswith(".jpg"), "image_path should be a .jpg filename"


# ---------------------------------------------------------------------------
# 10. Consistency: same inputs → same meme
# ---------------------------------------------------------------------------


def test_consistent_selection_same_inputs():
    result_a = _call(session_id="stable-session", assistant_turn_index=4)
    result_b = _call(session_id="stable-session", assistant_turn_index=4)
    assert result_a is not None and result_b is not None
    assert result_a == result_b, "Same inputs must deterministically return the same meme"


def test_previous_meme_image_is_not_repeated_when_assets_remain():
    first = _call(session_id="no-repeat-session", assistant_turn_index=3, user_message="hello", assistant_text="")
    assert first is not None

    second = _call(
        session_id="no-repeat-session",
        assistant_turn_index=3,
        user_message="hello",
        assistant_text="",
        previous_meme_image_paths=[first["image_path"]],
    )

    assert second is not None
    assert second["image_path"] != first["image_path"]


def test_contextual_repeat_uses_alternate_when_already_used():
    result = _call(
        user_message="met qua",
        previous_meme_image_paths=["user-is-tired.jpg"],
    )

    assert result is not None
    assert result["image_path"] != "user-is-tired.jpg"
