"""
Structured observability for Serene backend.

Provides:
- configure_json_logging(): switches root logger to JSON format via
  python-json-logger when LOG_FORMAT=json (default in production).
  Falls back to plain text in dev / test.
- Prometheus counters + histograms for HTTP requests and chat turns.
- _configure_prometheus_metrics(): wires a /metrics route onto a FastAPI app.

Usage (in main.py lifespan or module init):
    from app.core.observability import configure_json_logging, wire_prometheus
    configure_json_logging()
    wire_prometheus(app)
"""
from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------

def configure_json_logging(log_level: str = "INFO") -> None:
    """
    Configure root logger with JSON formatter when available.
    Falls back to plain text (StreamHandler) if python-json-logger is missing.

    Safe to call multiple times — idempotent after first call.
    """
    if getattr(configure_json_logging, "_done", False):
        return

    level = getattr(logging, log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "langchain", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    log_format = os.getenv("LOG_FORMAT", "json").lower()

    if log_format == "json":
        try:
            from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

            handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
                rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
            )
            handler.setFormatter(formatter)
            root.handlers = [handler]
            configure_json_logging._done = True  # type: ignore[attr-defined]
            return
        except ImportError:
            pass  # fall through to plain text

    # Plain text fallback (dev / test)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
    )
    root.handlers = [handler]
    configure_json_logging._done = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

_metrics_initialized = False
http_request_counter = None
http_request_duration = None
chat_turn_counter = None
chat_turn_duration = None
sos_trigger_counter = None


def _init_prometheus() -> bool:
    """Lazily initialise Prometheus metrics. Returns True if available."""
    global _metrics_initialized, http_request_counter, http_request_duration
    global chat_turn_counter, chat_turn_duration, sos_trigger_counter

    if _metrics_initialized:
        return http_request_counter is not None

    _metrics_initialized = True
    try:
        from prometheus_client import Counter, Histogram

        http_request_counter = Counter(
            "serene_http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status_code"],
        )
        http_request_duration = Histogram(
            "serene_http_request_duration_seconds",
            "HTTP request latency",
            ["method", "path"],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
        )
        chat_turn_counter = Counter(
            "serene_chat_turns_total",
            "Total chat turns processed",
            ["route_tier", "persona"],
        )
        chat_turn_duration = Histogram(
            "serene_chat_turn_duration_seconds",
            "Chat turn end-to-end latency",
            ["route_tier"],
            buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0],
        )
        sos_trigger_counter = Counter(
            "serene_sos_triggers_total",
            "Total SOS / crisis turns triggered",
            ["risk_level"],
        )
        return True
    except ImportError:
        return False


def record_chat_turn(
    *,
    route_tier: str,
    persona: str,
    duration_seconds: float,
) -> None:
    """Record a completed chat turn. No-op when prometheus-client not installed."""
    if not _init_prometheus() or chat_turn_counter is None:
        return
    chat_turn_counter.labels(route_tier=route_tier, persona=persona).inc()
    if chat_turn_duration is not None:
        chat_turn_duration.labels(route_tier=route_tier).observe(duration_seconds)


def record_sos_trigger(risk_level: int) -> None:
    """Increment SOS trigger counter. No-op when prometheus-client not installed."""
    if not _init_prometheus() or sos_trigger_counter is None:
        return
    sos_trigger_counter.labels(risk_level=str(risk_level)).inc()


def wire_prometheus(app: "FastAPI") -> bool:
    """
    Attach /metrics endpoint and request-latency middleware to a FastAPI app.
    Returns True if successfully wired, False if prometheus-client missing.
    """
    if not _init_prometheus():
        return False

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from fastapi import Request, Response
    from fastapi.routing import APIRoute

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.middleware("http")
    async def _prometheus_middleware(request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration = time.perf_counter() - start

        # Normalise path — replace UUIDs / numeric IDs to avoid cardinality explosion
        path = _normalise_path(request.url.path)

        if http_request_counter is not None:
            http_request_counter.labels(
                method=request.method,
                path=path,
                status_code=str(response.status_code),
            ).inc()
        if http_request_duration is not None:
            http_request_duration.labels(
                method=request.method,
                path=path,
            ).observe(duration)

        return response

    return True


def _normalise_path(path: str) -> str:
    """Replace path segments that look like IDs with {id} placeholder."""
    import re
    # UUID pattern
    path = re.sub(
        r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "/{id}",
        path,
        flags=re.IGNORECASE,
    )
    # Pure numeric segment
    path = re.sub(r"/\d+", "/{id}", path)
    return path
