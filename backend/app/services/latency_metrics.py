from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any


CHAT_LATENCY_INT_STAGES: tuple[str, ...] = (
    "backend_request_parse_ms",
    "auth_or_session_load_ms",
    "safety_gate_ms",
    "context_pack_ms",
    "memory_load_ms",
    "friend_llm_call_ms",
    "advisor_consult_ms",
    "advisor_selector_ms",
    "tts_enqueue_ms",
    "outbox_enqueue_ms",
    "persona_router_ms",
    "unlock_gate_ms",
    "vietnamese_style_controller_ms",
    "response_planner_ms",
    "analyst_agent_ms",
    "safety_output_validator_ms",
    "db_write_ms",
    "frontend_send_to_backend_ms",
    "total_backend_ms",
    "total_frontend_visible_latency_ms",
)


@contextmanager
def measure_stage(trace: dict[str, int], stage: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        trace[stage] = int((time.perf_counter() - started) * 1000)


def ensure_chat_latency_trace(
    trace: dict[str, Any] | None,
    *,
    total_backend_ms: int | None = None,
) -> dict[str, Any]:
    """Normalize public chat latency traces without leaking request content."""
    out: dict[str, Any] = dict(trace or {})
    for stage in CHAT_LATENCY_INT_STAGES:
        value = out.get(stage)
        out[stage] = int(value) if isinstance(value, (int, float)) else 0
    if total_backend_ms is not None:
        out["total_backend_ms"] = int(total_backend_ms)
        out["total_frontend_visible_latency_ms"] = int(total_backend_ms)
    fallbacks = out.get("context_pack_fallbacks")
    out["context_pack_fallbacks"] = list(fallbacks) if isinstance(fallbacks, list) else []
    return out
