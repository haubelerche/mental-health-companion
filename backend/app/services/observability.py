from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Iterator


logger = logging.getLogger(__name__)

_SENSITIVE_KEY_FRAGMENTS = (
    "text",
    "content",
    "message",
    "prompt",
    "reply",
    "assistant_text",
    "user_message",
    "raw",
    "clinical",
    "risk_indicator",
    "risk_detail",
    "distress_score",
    "advisor_reasoning",
    "analyst_rationale",
    "note",
    "email",
    "phone",
    "authorization",
    "password",
    "secret",
    "token",
)

_LOW_CARDINALITY_LABELS = {"env", "route_tier", "model", "endpoint", "worker_type", "status"}
_active_trace: ContextVar["EvidenceTrace | None"] = ContextVar("_active_evidence_trace", default=None)
_sink_lock = Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _local_sink_path() -> Path | None:
    configured = os.getenv("SERENE_TRACE_JSONL_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.getenv("SERENE_TRACE_JSONL_ENABLED", "0") == "1":
        return _repo_root() / "artifacts" / "observability" / "latest_traces.jsonl"
    return None


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _redact_value(v) for k, v in value.items() if not _is_sensitive_key(str(k))}
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in list(value)[:50]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def redact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    return {str(k): _redact_value(v) for k, v in (metadata or {}).items() if not _is_sensitive_key(str(k))}


def hash_identifier(value: str | None, *, salt: str | None = None) -> str | None:
    token = str(value or "").strip()
    if not token:
        return None
    digest = hashlib.sha256(f"{salt or os.getenv('SERENE_OBSERVABILITY_HASH_SALT', 'serene')}:{token}".encode("utf-8")).hexdigest()
    return digest[:24]


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class EvidenceTrace:
    name: str
    trace_id: str
    request_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    quality_tags: dict[str, Any] = field(default_factory=dict)
    started_ms: int = field(default_factory=_now_ms)
    ended_ms: int | None = None
    status: str = "open"

    def start_span(self, name: str, *, metadata: dict[str, Any] | None = None) -> "_EvidenceSpan":
        return _EvidenceSpan(self, name=name, metadata=metadata)

    def record_event(self, name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {"name": name, "at_ms": _now_ms(), "metadata": redact_metadata(metadata)}
        self.events.append(event)
        return event

    def record_metric(
        self,
        name: str,
        value: int | float,
        *,
        labels: dict[str, Any] | None = None,
        unit: str | None = None,
    ) -> dict[str, Any]:
        safe_labels = {k: str(v) for k, v in (labels or {}).items() if k in _LOW_CARDINALITY_LABELS and v is not None}
        metric = {"name": name, "value": float(value), "labels": safe_labels}
        if unit:
            metric["unit"] = unit
        self.metrics.append(metric)
        return metric

    def emit_quality_tag(self, name: str, value: Any) -> None:
        if not _is_sensitive_key(name):
            self.quality_tags[str(name)] = _redact_value(value)

    def finish(self, *, status: str = "ok", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.ended_ms is None:
            self.ended_ms = _now_ms()
        self.status = status
        if metadata:
            self.metadata.update(redact_metadata(metadata))
        payload = self.to_dict()
        _write_local_trace(payload)
        return payload

    def to_dict(self) -> dict[str, Any]:
        duration_ms = (self.ended_ms or _now_ms()) - self.started_ms
        return {
            "schema_version": "serene.trace.v1",
            "name": self.name,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "status": self.status,
            "started_ms": self.started_ms,
            "ended_ms": self.ended_ms,
            "duration_ms": duration_ms,
            "metadata": redact_metadata(self.metadata),
            "spans": list(self.spans),
            "events": list(self.events),
            "metrics": list(self.metrics),
            "quality_tags": redact_metadata(self.quality_tags),
        }


class _EvidenceSpan:
    def __init__(self, trace: EvidenceTrace, *, name: str, metadata: dict[str, Any] | None = None) -> None:
        self._trace = trace
        self._name = name
        self._metadata = redact_metadata(metadata)
        self._started = time.perf_counter()
        self._started_ms = _now_ms()

    def __enter__(self) -> "_EvidenceSpan":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        status = "error" if exc_type is not None else "ok"
        self.finish(status=status, metadata={"error_type": getattr(exc_type, "__name__", None)} if exc_type else None)

    def finish(self, *, status: str = "ok", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        span = {
            "name": self._name,
            "status": status,
            "started_ms": self._started_ms,
            "duration_ms": int((time.perf_counter() - self._started) * 1000),
            "metadata": {**self._metadata, **redact_metadata(metadata)},
        }
        self._trace.spans.append(span)
        return span


def _write_local_trace(payload: dict[str, Any]) -> None:
    path = _local_sink_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with _sink_lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - observability must fail open
        logger.debug("local trace sink skipped: %s", exc)


def get_active_trace() -> EvidenceTrace | None:
    return _active_trace.get()


def set_active_trace(trace: EvidenceTrace | None) -> None:
    _active_trace.set(trace)


def start_trace(
    name: str,
    *,
    trace_id: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> EvidenceTrace:
    request = request_id or str(uuid.uuid4())
    trace = EvidenceTrace(
        name=name,
        trace_id=trace_id or str(uuid.uuid4()),
        request_id=request,
        metadata={
            "request_id": request,
            "user_id_hash": hash_identifier(user_id),
            "session_id_hash": hash_identifier(session_id),
            **redact_metadata(metadata),
        },
    )
    set_active_trace(trace)
    return trace


@contextmanager
def start_span(name: str, *, metadata: dict[str, Any] | None = None) -> Iterator[None]:
    trace = get_active_trace()
    if trace is None:
        yield
        return
    with trace.start_span(name, metadata=metadata):
        yield


def record_event(name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    trace = get_active_trace()
    if trace is not None:
        return trace.record_event(name, metadata=metadata)
    return redacted_event(name, metadata=metadata)


def record_metric(
    name: str,
    value: int | float,
    *,
    labels: dict[str, Any] | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    trace = get_active_trace()
    if trace is not None:
        return trace.record_metric(name, value, labels=labels, unit=unit)
    safe_labels = {k: str(v) for k, v in (labels or {}).items() if k in _LOW_CARDINALITY_LABELS and v is not None}
    out: dict[str, Any] = {"name": name, "value": float(value), "labels": safe_labels}
    if unit:
        out["unit"] = unit
    return out


def emit_quality_tag(name: str, value: Any) -> None:
    trace = get_active_trace()
    if trace is not None:
        trace.emit_quality_tag(name, value)


def finish_trace(*, status: str = "ok", metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
    trace = get_active_trace()
    if trace is None:
        return None
    try:
        return trace.finish(status=status, metadata=metadata)
    finally:
        set_active_trace(None)


def redacted_event(name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"event": name, "metadata": redact_metadata(metadata)}


def log_chat_event(logger: logging.Logger, name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    event = redacted_event(name, metadata=metadata)
    record_event(name, metadata=event["metadata"])
    logger.info("chat.observability event=%s metadata=%s", event["event"], event["metadata"])
    return event
