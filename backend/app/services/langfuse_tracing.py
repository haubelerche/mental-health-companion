"""Langfuse LLM observability for Serene agent turns.

Optional: when LANGFUSE_SECRET_KEY / LANGFUSE_PUBLIC_KEY are absent the
module is a complete no-op — no import errors, no runtime overhead.

Usage pattern (entry-point functions):
    tracer = ChatTurnTracer(correlation_id=..., user_id=..., session_id=...)
    set_active_tracer(tracer)
    try:
        ...run graph...
    finally:
        tracer.flush()
        set_active_tracer(None)

Inside nodes (analyst_node, friend_node etc.):
    tracer = get_active_tracer()
    if tracer:
        tracer.generation("analyst", model=..., ...)
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# ContextVar lets nodes pick up the active tracer without it being part of
# the LangGraph state (which must be JSON-serialisable).
_active_tracer: ContextVar[ChatTurnTracer | None] = ContextVar(
    "_active_langfuse_tracer", default=None
)


def _make_client() -> Any | None:
    """Lazy-init Langfuse client; returns None when credentials are absent."""
    from app.core.config import get_settings

    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]

        return Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host or "https://cloud.langfuse.com",
        )
    except Exception as exc:
        logger.debug("Langfuse init skipped: %s", exc)
        return None


class ChatTurnTracer:
    """One Langfuse trace per chat turn.

    All methods are safe to call unconditionally — they silently no-op when
    Langfuse credentials are absent or when the SDK raises unexpectedly.
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
        self._trace: Any = None
        self._active_spans: dict[str, Any] = {}

        if self._client is None:
            return
        try:
            self._trace = self._client.trace(
                id=correlation_id,
                name="chat_turn",
                user_id=user_id,
                session_id=session_id,
                input=input_meta or {},
            )
        except Exception as exc:
            logger.debug("Langfuse trace create failed: %s", exc)

    # ------------------------------------------------------------------
    # Spans (for non-LLM nodes, e.g. supervisor)
    # ------------------------------------------------------------------

    def span_start(self, name: str, *, data: dict[str, Any] | None = None) -> None:
        if self._trace is None:
            return
        try:
            self._active_spans[name] = self._trace.span(name=name, input=data or {})
        except Exception as exc:
            logger.debug("Langfuse span_start(%s): %s", name, exc)

    def span_end(self, name: str, *, data: dict[str, Any] | None = None) -> None:
        span = self._active_spans.pop(name, None)
        if span is None:
            return
        try:
            span.end(output=data or {})
        except Exception as exc:
            logger.debug("Langfuse span_end(%s): %s", name, exc)

    # ------------------------------------------------------------------
    # Generations (for LLM calls in analyst / friend nodes)
    # ------------------------------------------------------------------

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
        if self._trace is None:
            return
        try:
            self._trace.generation(
                name=name,
                model=model,
                input=input_messages,
                output=output,
                usage={"input": input_tokens, "output": output_tokens},
                metadata=metadata or {},
            )
        except Exception as exc:
            logger.debug("Langfuse generation(%s): %s", name, exc)

    # ------------------------------------------------------------------
    # Scores (e.g. distress_score for each turn)
    # ------------------------------------------------------------------

    def score(self, name: str, value: float, *, comment: str | None = None) -> None:
        if self._trace is None:
            return
        try:
            self._trace.score(name=name, value=value, comment=comment)
        except Exception as exc:
            logger.debug("Langfuse score(%s): %s", name, exc)

    # ------------------------------------------------------------------
    # Finalise the trace output
    # ------------------------------------------------------------------

    def update_output(
        self,
        output: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._trace is None:
            return
        try:
            self._trace.update(output=output, metadata=metadata or {})
        except Exception as exc:
            logger.debug("Langfuse trace update: %s", exc)

    # ------------------------------------------------------------------
    # Flush — call once at the end of the turn
    # ------------------------------------------------------------------

    def flush(self) -> None:
        if self._client is None:
            return
        try:
            self._client.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level helpers consumed by nodes
# ---------------------------------------------------------------------------


def get_active_tracer() -> ChatTurnTracer | None:
    return _active_tracer.get()


def set_active_tracer(tracer: ChatTurnTracer | None) -> None:
    _active_tracer.set(tracer)
