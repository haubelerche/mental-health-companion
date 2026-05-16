"""Tests for the DistressRouter (distress_router function in langgraph_chat.py).

The DistressRouter is the first non-safety node in the LangGraph flow.
It routes each non-SOS turn to either 'analyst' (for structured analysis) or
'friend' (for direct FriendNode processing).

Threshold constants (from langgraph_chat.py):
  _ANALYST_DISTRESS_THRESHOLD     = 0.82   (distress >= this → analyst)
  _FAST_MODEL_DISTRESS_THRESHOLD  = 0.55   (distress < this + short msg → fast model)
  _FAST_MODEL_MSG_LEN_MAX         = 220    (max msg length for fast-model eligibility)

Note: SOS turns bypass distress_router entirely (handled by SafetyFinalizer).
  High-risk persona routing is tested via route_persona from app.personas.router.
"""

from __future__ import annotations

from typing import Any

import pytest

# ── Import the unit under test ───────────────────────────────────────────────
from app.services.langgraph_chat import (
    ChatGraphState,
    distress_router,
    route_after_distress_router,
    _ANALYST_DISTRESS_THRESHOLD,
    _FAST_MODEL_DISTRESS_THRESHOLD,
    _FAST_MODEL_MSG_LEN_MAX,
)
from app.personas.router import route_persona


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_state(**overrides: Any) -> ChatGraphState:
    """Return a minimal ChatGraphState dict with safe defaults."""
    base: ChatGraphState = {
        "correlation_id": "test-corr-001",
        "user_id": "test-user-001",
        "user_message": "hello",
        "distress_score": 0.0,
        "crisis_route_finalized": False,
        "mood_today": None,
        "routing_history": [],
        "recent_messages": [],
        "long_term_memories": [],
        "mem0_facts": [],
        "active_persona_id": "dung_luong",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


# ─────────────────────────────────────────────────────────────────────────────
# 1. Low distress → route to "friend" (allow_normal_flow / default)
# ─────────────────────────────────────────────────────────────────────────────

class TestLowDistressRouting:
    def test_empty_message_routes_friend(self):
        state = _make_state(user_message="", distress_score=0.0)
        result = distress_router(state)
        assert result["route_decision"] == "friend"

    def test_greeting_routes_friend(self):
        state = _make_state(user_message="hello", distress_score=0.0)
        result = distress_router(state)
        assert result["route_decision"] == "friend"
        assert result["route_reason"] in {"short_greeting", "default"}

    def test_low_distress_short_message_uses_fast_model(self):
        """Distress < _FAST_MODEL_DISTRESS_THRESHOLD and short msg → use_fast_friend_model=True."""
        state = _make_state(
            user_message="hôm nay mình ổn",
            distress_score=_FAST_MODEL_DISTRESS_THRESHOLD - 0.01,
        )
        result = distress_router(state)
        assert result["use_fast_friend_model"] is True

    def test_zero_distress_default_routes_friend(self):
        state = _make_state(user_message="mình muốn nói chuyện", distress_score=0.0)
        result = distress_router(state)
        assert result["route_decision"] == "friend"
        assert result["route_reason"] == "default"

    def test_short_greeting_vi_routes_friend(self):
        # _GREETING_RE matches unaccented "chao", "hi", "hello" — use ASCII form
        state = _make_state(user_message="chao", distress_score=0.1)
        result = distress_router(state)
        assert result["route_decision"] == "friend"
        assert result["route_reason"] in {"short_greeting", "default"}


# ─────────────────────────────────────────────────────────────────────────────
# 2. High distress → route to "analyst"
# ─────────────────────────────────────────────────────────────────────────────

class TestHighDistressRouting:
    def test_high_distress_routes_analyst(self):
        """distress_score >= _ANALYST_DISTRESS_THRESHOLD → analyst."""
        state = _make_state(
            user_message="mình không biết phải làm gì nữa",
            distress_score=_ANALYST_DISTRESS_THRESHOLD,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "high_distress"

    def test_above_threshold_routes_analyst(self):
        state = _make_state(
            user_message="mình cảm thấy rất tệ",
            distress_score=0.95,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "high_distress"

    def test_high_distress_disables_fast_model(self):
        """High distress should not qualify for fast model."""
        state = _make_state(
            user_message="mình cảm thấy rất tệ",
            distress_score=0.90,
        )
        result = distress_router(state)
        assert result["use_fast_friend_model"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Threshold boundary behavior
# ─────────────────────────────────────────────────────────────────────────────

class TestThresholdBoundary:
    def test_just_below_analyst_threshold_routes_friend(self):
        """Score just below _ANALYST_DISTRESS_THRESHOLD does NOT route to analyst."""
        just_below = _ANALYST_DISTRESS_THRESHOLD - 0.01
        state = _make_state(
            user_message="mình hơi lo lắng một chút",
            distress_score=just_below,
        )
        result = distress_router(state)
        assert result["route_decision"] == "friend"

    def test_exactly_at_analyst_threshold_routes_analyst(self):
        """Score == _ANALYST_DISTRESS_THRESHOLD triggers analyst route."""
        state = _make_state(
            user_message="mình không biết phải làm gì",
            distress_score=_ANALYST_DISTRESS_THRESHOLD,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"

    def test_fast_model_threshold_boundary(self):
        """Score == _FAST_MODEL_DISTRESS_THRESHOLD: NOT eligible for fast model."""
        state = _make_state(
            user_message="hello",
            distress_score=_FAST_MODEL_DISTRESS_THRESHOLD,
        )
        result = distress_router(state)
        # At exactly the threshold, use_fast requires STRICTLY less-than
        assert result["use_fast_friend_model"] is False

    def test_just_below_fast_model_threshold_qualifies(self):
        just_below = _FAST_MODEL_DISTRESS_THRESHOLD - 0.01
        state = _make_state(
            user_message="ok",
            distress_score=just_below,
        )
        result = distress_router(state)
        assert result["use_fast_friend_model"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Explicit analysis/planning triggers analyst route regardless of distress
# ─────────────────────────────────────────────────────────────────────────────

class TestExplicitAnalysisIntent:
    def test_explicit_plan_keyword_routes_analyst(self):
        # _ANALYST_TRIGGER_RE matches "phan\s+tich" (unaccented).
        # Use ASCII form since the regex does not strip Vietnamese diacritics.
        state = _make_state(
            user_message="ban co the phan tich tinh huong nay giup minh khong?",
            distress_score=0.2,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "explicit_analysis"

    def test_ke_hoach_keyword_routes_analyst(self):
        # _ANALYST_TRIGGER_RE matches "ke\s+hoach" (unaccented).
        # Use ASCII form since the regex does not strip Vietnamese diacritics.
        state = _make_state(
            user_message="minh can mot ke hoach cho tuan nay",
            distress_score=0.1,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "explicit_analysis"

    def test_english_plan_keyword_routes_analyst(self):
        state = _make_state(
            user_message="can you help me make a plan for this situation?",
            distress_score=0.0,
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "explicit_analysis"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Mood + distress combo routing
# ─────────────────────────────────────────────────────────────────────────────

class TestMoodDistressCombo:
    def test_stressed_mood_with_mid_distress_routes_analyst(self):
        """mood=stressed + distress >= 0.58 → analyst via mood_distress_combo."""
        state = _make_state(
            user_message="hôm nay mình cảm thấy không tốt",
            distress_score=0.60,
            mood_today={"mood": "stressed"},
        )
        result = distress_router(state)
        assert result["route_decision"] == "analyst"
        assert result["route_reason"] == "mood_distress_combo"

    def test_stressed_mood_below_combo_threshold_routes_friend(self):
        """mood=stressed but distress < 0.58 → NOT mood_distress_combo."""
        state = _make_state(
            user_message="hôm nay hơi stress nhẹ",
            distress_score=0.50,
            mood_today={"mood": "stressed"},
        )
        result = distress_router(state)
        # Should not get mood_distress_combo reason
        assert result.get("route_reason") != "mood_distress_combo"

    def test_neutral_mood_does_not_trigger_combo(self):
        state = _make_state(
            user_message="hôm nay bình thường",
            distress_score=0.60,
            mood_today={"mood": "neutral"},
        )
        result = distress_router(state)
        assert result.get("route_reason") != "mood_distress_combo"


# ─────────────────────────────────────────────────────────────────────────────
# 6. crisis_route_finalized override
# ─────────────────────────────────────────────────────────────────────────────

class TestCrisisRouteFinalizedOverride:
    def test_crisis_finalized_always_routes_friend(self):
        """When crisis_route_finalized=True, even high distress stays on friend path."""
        state = _make_state(
            user_message="mình cần trợ giúp",
            distress_score=0.95,
            crisis_route_finalized=True,
        )
        result = distress_router(state)
        assert result["route_decision"] == "friend"
        assert result["route_reason"] == "crisis_route_finalized"

    def test_crisis_finalized_overrides_explicit_analysis(self):
        state = _make_state(
            user_message="phân tích tình huống này đi",
            distress_score=0.90,
            crisis_route_finalized=True,
        )
        result = distress_router(state)
        assert result["route_decision"] == "friend"
        assert result["route_reason"] == "crisis_route_finalized"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Route metadata correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteMetadata:
    def test_routing_history_updated(self):
        """distress_router must append itself to routing_history."""
        state = _make_state(
            user_message="hello",
            distress_score=0.0,
            routing_history=["safety_gate"],
        )
        result = distress_router(state)
        assert "distress_router" in result["routing_history"]
        assert "safety_gate" in result["routing_history"]

    def test_result_has_required_keys(self):
        """All expected output keys must be present."""
        state = _make_state(user_message="mình cảm thấy khó chịu", distress_score=0.3)
        result = distress_router(state)
        assert "route_decision" in result
        assert "route_reason" in result
        assert "use_fast_friend_model" in result
        assert "routing_history" in result

    def test_route_decision_is_valid_literal(self):
        """route_decision must be one of 'analyst' | 'friend'."""
        for distress in (0.0, 0.5, 0.82, 0.95):
            state = _make_state(user_message="test message for routing", distress_score=distress)
            result = distress_router(state)
            assert result["route_decision"] in {"analyst", "friend"}, (
                f"Unexpected route_decision={result['route_decision']!r} for distress={distress}"
            )

    def test_use_fast_friend_model_is_bool(self):
        state = _make_state(user_message="mình ổn", distress_score=0.2)
        result = distress_router(state)
        assert isinstance(result["use_fast_friend_model"], bool)

    def test_long_message_disqualifies_fast_model(self):
        """Message longer than _FAST_MODEL_MSG_LEN_MAX should not get fast model."""
        long_msg = "a" * (_FAST_MODEL_MSG_LEN_MAX + 1)
        state = _make_state(
            user_message=long_msg,
            distress_score=0.2,
        )
        result = distress_router(state)
        assert result["use_fast_friend_model"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 8. route_after_distress_router conditional edge
# ─────────────────────────────────────────────────────────────────────────────

class TestRouteAfterDistressRouter:
    def test_analyst_route_returns_analyst(self):
        state = _make_state(route_decision="analyst")
        assert route_after_distress_router(state) == "analyst"

    def test_friend_route_returns_friend(self):
        state = _make_state(route_decision="friend")
        assert route_after_distress_router(state) == "friend"

    def test_missing_route_decision_defaults_friend(self):
        state = _make_state()
        # No route_decision set; should default to friend
        assert route_after_distress_router(state) == "friend"


# ─────────────────────────────────────────────────────────────────────────────
# 9. SOS / high-risk persona routing — persona is blocked during SOS
# ─────────────────────────────────────────────────────────────────────────────

class TestPersonaRoutingBlockedDuringSOS:
    """
    SOS turns bypass distress_router entirely.
    Persona routing during SOS is handled by route_persona from app.personas.router.
    These tests verify that persona stylization is disabled when sos_triggered=True.
    """

    def test_sos_forces_default_persona(self):
        decision = route_persona(
            current_persona_id="hau_luong",
            requested_persona_id="hau_luong",
            distress=0.95,
            sos_triggered=True,
            is_unlocked=True,
        )
        assert decision.target_persona_id == "dung_luong"
        assert decision.safety_override is True

    def test_sos_deactivates_non_default_persona(self):
        decision = route_persona(
            current_persona_id="hau_luong",
            requested_persona_id=None,
            distress=0.90,
            sos_triggered=True,
            is_unlocked=True,
        )
        assert decision.action == "deactivate"
        assert decision.safety_override is True
        assert decision.blocked_reason == "safety_crisis_bypass"

    def test_sos_keeps_default_persona_without_deactivate(self):
        decision = route_persona(
            current_persona_id="dung_luong",
            requested_persona_id=None,
            distress=0.90,
            sos_triggered=True,
            is_unlocked=True,
        )
        # Already at default — action should be "keep" not "deactivate"
        assert decision.action == "keep"
        assert decision.target_persona_id == "dung_luong"
        assert decision.safety_override is True

    def test_sos_blocks_persona_switch_request(self):
        """User cannot switch persona during SOS."""
        decision = route_persona(
            current_persona_id="dung_luong",
            requested_persona_id="hau_luong",
            distress=0.95,
            sos_triggered=True,
            is_unlocked=True,
        )
        # Should not switch to requested persona
        assert decision.target_persona_id == "dung_luong"
        assert decision.safety_override is True


# ─────────────────────────────────────────────────────────────────────────────
# 10. FastNeedRouter — integration with distress_router context
#     (FastNeedRouter handles FastAPI-level routing before LangGraph)
# ─────────────────────────────────────────────────────────────────────────────

class TestFastNeedRouterComplement:
    """
    FastNeedRouter is a separate router that determines advisor_assisted vs fast vs service_only.
    These tests cover behaviors not already in test_fast_need_router.py, focusing on
    the interplay relevant to the distress routing pipeline.
    """

    def test_emotional_load_repeated_in_history_upgrades_to_advisor(self):
        from app.services.fast_need_router import FastNeedRouter
        d = FastNeedRouter().route(
            user_message="mình vẫn vậy thôi",
            recent_user_messages=["mình quá tải rồi", "mình kiệt sức không chịu nổi"],
        )
        assert d.route_tier == "advisor_assisted"
        assert d.should_call_advisors is True
        assert "repeated_emotional_load" in d.reason_codes

    def test_escalating_recent_complexity_upgrades_route(self):
        from app.services.fast_need_router import FastNeedRouter
        # Each message has increasing domain signal count
        msg1 = "mình hơi buồn"
        msg2 = "mình buồn và stress vì deadline; không ngủ được; lại còn cãi nhau với bạn bè"
        msg3 = (
            "mình không biết làm sao; vừa trễ deadline vừa cãi nhau với gia đình "
            "vừa không ngủ được; lại lỗi tại mình hết; lúc nào cũng lo lắng như vậy"
        )
        d = FastNeedRouter().route(
            user_message=msg3,
            recent_user_messages=[msg1, msg2],
        )
        assert d.route_tier == "advisor_assisted"
        assert d.should_call_advisors is True
