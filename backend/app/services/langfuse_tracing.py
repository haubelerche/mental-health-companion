"""Langfuse observability for Serene agent turns.

Tracing is optional and fail-open. If Langfuse credentials are absent or the
SDK is unavailable, all methods are no-ops. When enabled, each chat turn is one
root `agent` observation with child observations for safety, analyst, and
friend work.
"""

from __future__ import annotations

import logging
import os
from contextlib import ExitStack
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

_active_tracer: ContextVar["ChatTurnTracer | None"] = ContextVar(
    "_active_langfuse_tracer", default=None
)

_MAX_TEXT_CHARS = 4000
_PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


def _proxy_is_known_dead(value: str | None) -> bool:
    token = str(value or "").strip().lower()
    return token in {"http://127.0.0.1:9", "https://127.0.0.1:9", "http://localhost:9", "https://localhost:9"}


def _clear_known_dead_proxy_env() -> list[str]:
    """Remove local blackhole proxy settings that prevent Langfuse OTLP export.

    Some sandboxed shells set proxy env vars to 127.0.0.1:9. The Langfuse SDK
    honors those variables via requests/OTel, which makes tracing silently fail.
    We only clear that known-dead value and leave real corporate proxies intact.
    """
    cleared: list[str] = []
    for key in _PROXY_ENV_KEYS:
        if _proxy_is_known_dead(os.getenv(key)):
            os.environ.pop(key, None)
            cleared.append(key)
    if cleared:
        logger.warning("Langfuse export ignored known-dead proxy env vars: %s", ",".join(cleared))
    return cleared


def _settings_ready() -> tuple[str, str, str] | None:
    from app.core.config import get_settings

    if os.getenv("SERENE_BACKEND_TESTING") == "1" and os.getenv("LANGFUSE_ENABLE_IN_TESTS") != "1":
        return None

    settings = get_settings()
    public_key = (settings.langfuse_public_key or "").strip().strip('"')
    secret_key = (settings.langfuse_secret_key or "").strip().strip('"')
    base_url = (settings.langfuse_host or "https://cloud.langfuse.com").strip().strip('"')
    if not (public_key and secret_key):
        return None
    return public_key, secret_key, base_url


def _make_client() -> Any | None:
    creds = _settings_ready()
    if creds is None:
        return None
    public_key, secret_key, base_url = creds
    try:
        _clear_known_dead_proxy_env()
        from langfuse import Langfuse  # type: ignore[import-untyped]

        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            flush_at=1,
        )
    except Exception as exc:
        logger.debug("Langfuse init skipped: %s", exc)
        return None


def _mask_text(value: str) -> str:
    text = value or ""
    try:
        from app.services.pii_mask import mask_pii

        text = mask_pii(text)
    except Exception:
        pass
    if len(text) > _MAX_TEXT_CHARS:
        return text[: _MAX_TEXT_CHARS - 3] + "..."
    return text


def _safe_payload(value: Any) -> Any:
    """Mask and bound payloads before sending them to Langfuse."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _mask_text(value)
    if isinstance(value, list):
        return [_safe_payload(item) for item in value[:20]]
    if isinstance(value, tuple):
        return [_safe_payload(item) for item in value[:20]]
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in list(value.items())[:50]:
            key_str = str(key)[:120]
            if key_str.lower() in {"api_key", "authorization", "password", "secret", "token"}:
                safe[key_str] = "[redacted]"
            else:
                safe[key_str] = _safe_payload(item)
        return safe
    return _mask_text(str(value))


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, str]:
    """Keep metadata filterable and compatible with current Langfuse SDK guidance."""
    if not metadata:
        return {}
    out: dict[str, str] = {}
    for key, value in list(metadata.items())[:30]:
        if value is None:
            continue
        text = str(value)
        out[str(key)[:80]] = text[:200]
    return out


class ChatTurnTracer:
    """One Langfuse trace per chat turn.

    Baseline properties:
    - trace name is stable and descriptive;
    - `user_id` and `session_id` are propagated for filtering/session views;
    - child observations are typed (`generation`, `guardrail`, `span`);
    - prompt/response payloads are masked before export;
    - `flush()` closes the root observation and sends queued events.
    """

    def __init__(
        self,
        *,
        correlation_id: str,
        user_id: str | None = None,
        session_id: str | None = None,
        input_meta: dict[str, Any] | None = None,
    ) -> None:
        self._client = _make_client()
        self._root: Any = None
        self._exit_stack: ExitStack | None = None
        self._active_spans: dict[str, Any] = {}
        self._closed = False

        if self._client is None:
            return

        try:
            trace_id = self._client.create_trace_id(seed=correlation_id)
            stack = ExitStack()
            root_cm = self._client.start_as_current_observation(
                name="serene-chat-turn",
                as_type="agent",
                trace_context={"trace_id": trace_id},
                input=_safe_payload(input_meta or {}),
                metadata=_safe_metadata(
                    {
                        "correlation_id": correlation_id,
                        "feature": "chat",
                        **(input_meta or {}),
                    }
                ),
            )
            self._root = stack.enter_context(root_cm)

            from langfuse import propagate_attributes  # type: ignore[import-untyped]

            stack.enter_context(
                propagate_attributes(
                    user_id=user_id or None,
                    session_id=session_id or None,
                    trace_name="serene-chat-turn",
                    tags=["serene", "chat", "agent"],
                    metadata=_safe_metadata({"feature": "chat"}),
                )
            )
            self._exit_stack = stack
        except Exception as exc:
            logger.debug("Langfuse root observation create failed: %s", exc)
            self._close_contexts()
            self._client = None

    def _close_contexts(self) -> None:
        if self._exit_stack is None:
            return
        try:
            self._exit_stack.close()
        except Exception:
            pass
        finally:
            self._exit_stack = None
            self._closed = True

    def span_start(
        self,
        name: str,
        *,
        data: dict[str, Any] | None = None,
        as_type: str = "span",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._client is None:
            return
        try:
            self._active_spans[name] = self._client.start_observation(
                name=name,
                as_type=as_type,
                input=_safe_payload(data or {}),
                metadata=_safe_metadata(metadata),
            )
        except Exception as exc:
            logger.debug("Langfuse span_start(%s): %s", name, exc)

    def span_end(self, name: str, *, data: dict[str, Any] | None = None) -> None:
        span = self._active_spans.pop(name, None)
        if span is None:
            return
        try:
            span.update(output=_safe_payload(data or {}))
            span.end()
        except Exception as exc:
            logger.debug("Langfuse span_end(%s): %s", name, exc)

    def event(
        self,
        name: str,
        *,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        as_type: str = "span",
    ) -> None:
        if self._client is None:
            return
        try:
            obs = self._client.start_observation(
                name=name,
                as_type=as_type,
                input=_safe_payload(input_data or {}),
                metadata=_safe_metadata(metadata),
            )
            obs.update(output=_safe_payload(output_data or {}))
            obs.end()
        except Exception as exc:
            logger.debug("Langfuse event(%s): %s", name, exc)

    def update_metadata(self, metadata: dict[str, Any]) -> None:
        if self._root is None:
            return
        try:
            self._root.update(metadata=_safe_metadata(metadata))
        except Exception as exc:
            logger.debug("Langfuse metadata update: %s", exc)

    def routing_decision(
        self,
        *,
        route_tier: str,
        reason_codes: list[str] | tuple[str, ...],
        planned_advisor_ids: list[str] | tuple[str, ...],
        selected_advisor_ids: list[str] | tuple[str, ...] | None = None,
        interaction_need: str | None = None,
        persona_id: str | None = None,
    ) -> None:
        self.event(
            "dynamic_routing.decision",
            input_data={
                "message_length_bucket": "redacted",
            },
            output_data={
                "route_tier": route_tier,
                "reason_codes": list(reason_codes or [])[:8],
                "planned_advisor_ids": list(planned_advisor_ids or [])[:4],
                "selected_advisor_ids": list(selected_advisor_ids or [])[:4],
                "interaction_need": interaction_need,
                "persona_id": persona_id,
            },
            metadata={
                "route_tier": route_tier,
                "advisor_count": len(list(planned_advisor_ids or [])),
                "interaction_need": interaction_need,
                "persona_id": persona_id,
            },
        )

    def advisor_result(
        self,
        *,
        advisor_id: str,
        status: str,
        should_use: bool = False,
        confidence: float = 0.0,
        evidence_count: int = 0,
        move_count: int = 0,
    ) -> None:
        self.event(
            f"advisor.{advisor_id}.result",
            output_data={
                "advisor_id": advisor_id,
                "status": status,
                "should_use": bool(should_use),
                "confidence": round(float(confidence or 0.0), 3),
                "evidence_count": int(evidence_count or 0),
                "move_count": int(move_count or 0),
            },
            metadata={
                "worker_type": "advisor",
                "status": status,
                "advisor_id": advisor_id,
            },
        )

    def worker_enqueue(self, outcomes: dict[str, str]) -> None:
        self.event(
            "workers.enqueue",
            output_data={
                "worker_outcomes": dict(outcomes or {}),
                "worker_count": len(outcomes or {}),
            },
            metadata={
                "worker_count": len(outcomes or {}),
                "status": "ok" if all(v == "queued" for v in (outcomes or {}).values()) else "partial",
            },
        )

    def guardrail(
        self,
        name: str,
        *,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.event(
            name,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            as_type="guardrail",
        )

    def generation(
        self,
        name: str,
        *,
        model: str,
        input_messages: list[dict[str, Any]],
        output: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._client is None:
            return
        try:
            obs = self._client.start_observation(
                name=name,
                as_type="generation",
                model=model,
                input=_safe_payload(input_messages),
                output=_safe_payload(output),
                usage_details={
                    "input_tokens": int(input_tokens or 0),
                    "output_tokens": int(output_tokens or 0),
                },
                metadata=_safe_metadata(metadata),
            )
            obs.end()
        except Exception as exc:
            logger.debug("Langfuse generation(%s): %s", name, exc)

    def score(self, name: str, value: float, *, comment: str | None = None) -> None:
        if self._root is None:
            return
        try:
            self._root.score_trace(name=name, value=float(value), comment=comment)
        except Exception as exc:
            logger.debug("Langfuse score(%s): %s", name, exc)

    def update_output(
        self,
        output: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._root is None:
            return
        try:
            self._root.update(
                output=_safe_payload(output),
                metadata=_safe_metadata(metadata),
            )
        except Exception as exc:
            logger.debug("Langfuse root update: %s", exc)

    def flush(self) -> None:
        for name in list(self._active_spans.keys()):
            self.span_end(name, data={"status": "abandoned"})
        self._close_contexts()
        if self._client is None:
            return
        try:
            self._client.flush()
        except Exception:
            pass


def get_active_tracer() -> ChatTurnTracer | None:
    return _active_tracer.get()


def set_active_tracer(tracer: ChatTurnTracer | None) -> None:
    _active_tracer.set(tracer)
