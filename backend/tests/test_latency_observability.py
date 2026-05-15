"""Tests for ChatOrchestrator latency trace fields and observability contracts.

Verifies:
- generate_normal_turn() returns a valid route_tier and interaction_need
- finalize_normal_chat_response() surfaces latency_trace correctly
- route_tier is normalized for unknown values
- used_advisor_ids is capped at 2
- enqueue_async_side_effects() returns expected outcome keys
"""

from __future__ import annotations

import pytest

from app.services.chat_orchestrator import ChatOrchestrator, GeneratedNormalTurn
from app.services.safety_policy import evaluate_safety_policy
from app.services.schemas.contracts import ContextPack, SafetyPolicyDecision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_context_pack() -> ContextPack:
    policy = evaluate_safety_policy("hôm nay chán", [])
    return ContextPack(safety_policy=policy)


def _minimal_policy() -> SafetyPolicyDecision:
    return evaluate_safety_policy("hôm nay chán", [])


# ---------------------------------------------------------------------------
# Test 1
# ---------------------------------------------------------------------------

def test_generate_normal_turn_returns_route_tier():
    context_pack = _minimal_context_pack()
    policy_decision = _minimal_policy()

    result = ChatOrchestrator.generate_normal_turn(
        user_message="hôm nay chán",
        context_pack=context_pack,
        route_tier="fast",
        planned_advisor_ids=[],
        apply_output_policy_or_fallback=lambda text, policy_decision, audit: text,
        policy_decision=policy_decision,
    )

    assert result.route_tier in {"fast", "service_only", "advisor_assisted"}


# ---------------------------------------------------------------------------
# Test 2
# ---------------------------------------------------------------------------

def test_finalize_response_includes_latency_trace_key():
    data = {
        "assistant_text": "test",
        "route_tier": "fast",
        "used_advisor_ids": [],
    }
    result = ChatOrchestrator.finalize_normal_chat_response(
        data,
        latency_trace={"total_ms": 120},
    )

    assert "latency_trace" in result
    assert result["latency_trace"]["total_ms"] == 120


# ---------------------------------------------------------------------------
# Test 3
# ---------------------------------------------------------------------------

def test_finalize_response_latency_trace_defaults_to_empty_dict():
    data = {
        "assistant_text": "test",
        "route_tier": "fast",
        "used_advisor_ids": [],
    }
    result = ChatOrchestrator.finalize_normal_chat_response(data)

    assert "latency_trace" in result
    assert result["latency_trace"] == {}
    assert result["latency_trace"] is not None


# ---------------------------------------------------------------------------
# Test 4
# ---------------------------------------------------------------------------

def test_route_tier_is_normalized_in_final_response():
    data = {
        "assistant_text": "test",
        "route_tier": "unknown_tier",
        "used_advisor_ids": [],
    }
    result = ChatOrchestrator.finalize_normal_chat_response(data, latency_trace=None)

    assert result["route_tier"] == "fast"


# ---------------------------------------------------------------------------
# Test 5
# ---------------------------------------------------------------------------

def test_used_advisor_ids_capped_at_two():
    data = {
        "assistant_text": "test",
        "route_tier": "fast",
        "used_advisor_ids": ["a", "b", "c", "d"],
    }
    result = ChatOrchestrator.finalize_normal_chat_response(data)

    assert len(result["used_advisor_ids"]) <= 2


# ---------------------------------------------------------------------------
# Test 6
# ---------------------------------------------------------------------------

def test_interaction_need_in_generated_turn():
    context_pack = _minimal_context_pack()
    policy_decision = _minimal_policy()

    result = ChatOrchestrator.generate_normal_turn(
        user_message="hôm nay chán",
        context_pack=context_pack,
        route_tier="fast",
        planned_advisor_ids=[],
        apply_output_policy_or_fallback=lambda text, policy_decision, audit: text,
        policy_decision=policy_decision,
    )

    assert hasattr(result, "interaction_need")
    assert isinstance(result.interaction_need, str)
    assert len(result.interaction_need) > 0


# ---------------------------------------------------------------------------
# Test 7
# ---------------------------------------------------------------------------

def test_async_side_effects_enqueue_returns_job_type_outcomes():
    result = ChatOrchestrator.enqueue_async_side_effects(
        db=None,
        user_id="u1",
        session_id="s1",
        assistant_message_id="m1",
    )

    assert isinstance(result, dict)
    assert "memory_extraction" in result
    assert "dashboard_insight" in result
    assert "analyst_event" in result

    valid_values = {"queued", "enqueue_failed"}
    for key in ("memory_extraction", "dashboard_insight", "analyst_event"):
        assert result[key] in valid_values, f"Unexpected value for {key!r}: {result[key]!r}"
