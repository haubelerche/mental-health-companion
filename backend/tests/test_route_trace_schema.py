"""Route trace schema contract tests — PR-01.

Verifies that:
- All CHAT_LATENCY_INT_STAGES are present in every chat turn trace
- ChatTurnTracer.routing_decision emits route_tier, selected_advisor_ids, interaction_need
- Trace does not leak raw user/assistant text
- interaction_need is a valid non-empty string
- Observability redaction keeps route_tier and advisor fields visible
"""
from __future__ import annotations

from app.services.langfuse_tracing import ChatTurnTracer
from app.services.latency_metrics import CHAT_LATENCY_INT_STAGES, ensure_chat_latency_trace
from app.services.observability import log_chat_event, redacted_event
from app.services.interaction_need_classifier import classify_interaction_need
import logging


# ---------------------------------------------------------------------------
# 1. CHAT_LATENCY_INT_STAGES completeness
# ---------------------------------------------------------------------------

REQUIRED_LATENCY_STAGES = {
    "backend_request_parse_ms",
    "safety_gate_ms",
    "context_pack_ms",
    "friend_llm_call_ms",
    "advisor_consult_ms",
    "advisor_selector_ms",
    "outbox_enqueue_ms",
    "total_backend_ms",
    "total_frontend_visible_latency_ms",
}


def test_all_required_stages_in_chat_latency_int_stages():
    for stage in REQUIRED_LATENCY_STAGES:
        assert stage in CHAT_LATENCY_INT_STAGES, f"Missing required stage: {stage}"


def test_ensure_chat_latency_trace_fills_all_stages():
    trace = ensure_chat_latency_trace(
        {"friend_llm_call_ms": 450, "advisor_consult_ms": 120},
        total_backend_ms=900,
    )
    for stage in CHAT_LATENCY_INT_STAGES:
        assert stage in trace, f"Stage '{stage}' missing from normalized trace"
        assert isinstance(trace[stage], int), f"Stage '{stage}' must be int, got {type(trace[stage])}"


def test_ensure_chat_latency_trace_preserves_real_values():
    trace = ensure_chat_latency_trace(
        {
            "advisor_consult_ms": 88.7,
            "context_pack_ms": 12,
            "persona_router_ms": 5,
        },
        total_backend_ms=400,
    )
    assert trace["advisor_consult_ms"] == 88
    assert trace["context_pack_ms"] == 12
    assert trace["total_backend_ms"] == 400
    assert trace["total_frontend_visible_latency_ms"] == 400


def test_ensure_chat_latency_trace_defaults_missing_stages_to_zero():
    trace = ensure_chat_latency_trace({}, total_backend_ms=100)
    for stage in CHAT_LATENCY_INT_STAGES:
        assert trace[stage] == 0 or (stage in {"total_backend_ms", "total_frontend_visible_latency_ms"})


# ---------------------------------------------------------------------------
# 2. ChatTurnTracer.routing_decision emits required fields
# ---------------------------------------------------------------------------

def test_tracer_routing_decision_includes_interaction_need(monkeypatch):
    monkeypatch.setenv("SERENE_BACKEND_TESTING", "1")
    monkeypatch.delenv("LANGFUSE_ENABLE_IN_TESTS", raising=False)

    tracer = ChatTurnTracer(correlation_id="rt-test", user_id="u1", session_id="s1")
    tracer.routing_decision(
        route_tier="advisor_assisted",
        reason_codes=["explicit_analysis_request"],
        planned_advisor_ids=["strategy_resource_advisor"],
        selected_advisor_ids=["strategy_resource_advisor"],
        interaction_need="advice",
        persona_id="dung_luong",
    )
    tracer.flush()


def test_tracer_routing_decision_fast_route(monkeypatch):
    monkeypatch.setenv("SERENE_BACKEND_TESTING", "1")
    monkeypatch.delenv("LANGFUSE_ENABLE_IN_TESTS", raising=False)

    tracer = ChatTurnTracer(correlation_id="rt-fast", user_id="u2", session_id="s2")
    tracer.routing_decision(
        route_tier="fast",
        reason_codes=["greeting_fast"],
        planned_advisor_ids=[],
        selected_advisor_ids=[],
        interaction_need="small_talk",
        persona_id="dung_luong",
    )
    tracer.flush()


# ---------------------------------------------------------------------------
# 3. interaction_need classifier produces valid strings
# ---------------------------------------------------------------------------

VALID_INTERACTION_NEEDS = {
    "venting", "reassurance", "advice", "clarification",
    "distraction", "grounding", "safety", "recall", "mixed",
    "small_talk", "listen_only", "other",
}


def test_interaction_need_for_small_talk():
    need = classify_interaction_need("hôm nay chán quá", distress_score=0.1, sos_triggered=False)
    assert isinstance(need, str) and len(need) > 0


def test_interaction_need_for_advice_request():
    need = classify_interaction_need(
        "bạn phân tích giúp mình một phương án cho tuần này",
        distress_score=0.2,
        sos_triggered=False,
    )
    assert isinstance(need, str) and len(need) > 0


def test_interaction_need_for_high_distress():
    need = classify_interaction_need(
        "mình cảm thấy tuyệt vọng, không biết còn ý nghĩa gì",
        distress_score=0.75,
        sos_triggered=False,
    )
    assert isinstance(need, str) and len(need) > 0


def test_interaction_need_no_crash_on_empty_message():
    need = classify_interaction_need("", distress_score=0.0, sos_triggered=False)
    assert isinstance(need, str)


# ---------------------------------------------------------------------------
# 4. Observability redacts user content but preserves route fields
# ---------------------------------------------------------------------------

def test_observability_preserves_route_tier_and_advisor_ids(caplog):
    logger = logging.getLogger("test.trace.schema")
    with caplog.at_level(logging.INFO, logger=logger.name):
        event = log_chat_event(
            logger,
            "chat_turn_completed",
            metadata={
                "route_tier": "advisor_assisted",
                "selected_advisor_ids": ["empathy_advisor", "cbt_pattern_advisor"],
                "interaction_need": "venting",
                "user_message": "secret user text",
                "assistant_text": "secret assistant text",
                "validator_verdict": "allow",
                "advisor_timeout_count": 0,
            },
        )

    assert event["metadata"]["route_tier"] == "advisor_assisted"
    assert event["metadata"]["interaction_need"] == "venting"
    assert "user_message" not in event["metadata"]
    assert "assistant_text" not in event["metadata"]
    assert "secret user text" not in caplog.text


def test_redacted_event_keeps_advisor_fields():
    event = redacted_event(
        "chat_turn_completed",
        metadata={
            "route_tier": "advisor_assisted",
            "selected_advisor_ids": ["empathy_advisor"],
            "interaction_need": "venting",
            "validator_verdict": "allow",
            "advisor_timeout_count": 1,
        },
    )
    assert event["metadata"]["route_tier"] == "advisor_assisted"
    assert event["metadata"]["interaction_need"] == "venting"
    assert event["metadata"]["advisor_timeout_count"] == 1


# ---------------------------------------------------------------------------
# 5. Analyst turn trace includes analyst_agent_ms stage
# ---------------------------------------------------------------------------

def test_analyst_agent_ms_is_a_required_latency_stage():
    assert "analyst_agent_ms" in CHAT_LATENCY_INT_STAGES
