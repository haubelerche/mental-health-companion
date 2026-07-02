from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from pydantic import ValidationError

from app.agentic.policy import evaluate_tool_policy
from app.agentic.registry import ToolRegistry, build_default_tool_registry
from app.agentic.schemas import AgentRunResult, ToolCall, ToolRunResult
from app.services.chat_cost_metrics import observe_chat_usage
from app.services.langfuse_tracing import get_active_tracer

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 2
_MAX_TOOLS_PER_ROUND = 2
_MAX_TOOL_OUTPUT_CHARS = 3000


def _message_to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        return dict(message)
    return {
        "role": getattr(message, "role", "assistant") or "assistant",
        "content": getattr(message, "content", None),
        "tool_calls": getattr(message, "tool_calls", None),
    }


def _extract_tool_calls(message: Any) -> list[ToolCall]:
    raw_calls = getattr(message, "tool_calls", None)
    if raw_calls is None and isinstance(message, dict):
        raw_calls = message.get("tool_calls")
    calls: list[ToolCall] = []
    for raw in list(raw_calls or [])[:_MAX_TOOLS_PER_ROUND]:
        call_id = getattr(raw, "id", None) or (raw.get("id") if isinstance(raw, dict) else "")
        fn = getattr(raw, "function", None) or (raw.get("function") if isinstance(raw, dict) else None)
        name = getattr(fn, "name", None) or (fn.get("name") if isinstance(fn, dict) else "")
        arg_text = getattr(fn, "arguments", None) or (fn.get("arguments") if isinstance(fn, dict) else "{}")
        try:
            arguments = json.loads(arg_text or "{}") if isinstance(arg_text, str) else dict(arg_text or {})
        except Exception:
            arguments = {"__invalid_json__": str(arg_text or "")[:500]}
        if name:
            calls.append(ToolCall(tool_call_id=str(call_id or ""), name=str(name), arguments=arguments))
    return calls


def _bounded_output(output: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(output, ensure_ascii=False, default=str)
    if len(text) <= _MAX_TOOL_OUTPUT_CHARS:
        return output
    return {
        "truncated": True,
        "preview": text[:_MAX_TOOL_OUTPUT_CHARS],
    }


class AgentRunner:
    def __init__(self, *, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or build_default_tool_registry()

    def run(
        self,
        *,
        client: Any,
        model: str,
        messages: list[dict[str, Any]],
        agent_name: str,
        context: dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
    ) -> AgentRunResult:
        del timeout_seconds  # The OpenAI client is already configured with request timeout.
        run_id = str(uuid.uuid4())
        distress_score = float(context.get("distress_score") or 0.0)
        crisis_route_finalized = bool(context.get("crisis_route_finalized"))
        tool_schemas = self._registry.openai_tools_for_agent(
            agent_name,
            distress_score=distress_score,
            crisis_route_finalized=crisis_route_finalized,
        )
        working_messages: list[dict[str, Any]] = [dict(m) for m in messages]
        tool_results: list[ToolRunResult] = []
        policy_blocks: list[ToolRunResult] = []
        raw_response: Any | None = None

        for round_idx in range(_MAX_TOOL_ROUNDS + 1):
            kwargs: dict[str, Any] = {
                "model": model,
                "temperature": temperature,
                "messages": working_messages,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            if tool_schemas:
                kwargs["tools"] = tool_schemas
                kwargs["tool_choice"] = "auto"
            resp = client.chat.completions.create(**kwargs)
            raw_response = resp
            message = resp.choices[0].message
            usage = getattr(resp, "usage", None)
            if usage is not None:
                observe_chat_usage(
                    input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                )

            calls = _extract_tool_calls(message)
            content = (getattr(message, "content", None) or "").strip()
            if not calls or round_idx >= _MAX_TOOL_ROUNDS:
                return AgentRunResult(
                    content=content,
                    tool_results=tool_results,
                    policy_blocks=policy_blocks,
                    raw_response=raw_response,
                    agent_run_id=run_id,
                )

            assistant_message = _message_to_dict(message)
            assistant_message["role"] = "assistant"
            working_messages.append(assistant_message)

            for call in calls:
                result = self._run_tool_call(
                    call,
                    agent_name=agent_name,
                    context=context,
                    distress_score=distress_score,
                    crisis_route_finalized=crisis_route_finalized,
                )
                if result.status in {"blocked", "unknown_tool"}:
                    policy_blocks.append(result)
                else:
                    tool_results.append(result)
                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.tool_call_id,
                        "name": call.name,
                        "content": json.dumps(
                            {
                                "status": result.status,
                                "output": result.output,
                                "blocked_reason": result.blocked_reason,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                )

        return AgentRunResult(
            content="",
            tool_results=tool_results,
            policy_blocks=policy_blocks,
            raw_response=raw_response,
            agent_run_id=run_id,
        )

    def _run_tool_call(
        self,
        call: ToolCall,
        *,
        agent_name: str,
        context: dict[str, Any],
        distress_score: float,
        crisis_route_finalized: bool,
    ) -> ToolRunResult:
        started = time.perf_counter()
        spec = self._registry.get(call.name)
        policy = evaluate_tool_policy(
            spec=spec,
            agent_name=agent_name,
            distress_score=distress_score,
            crisis_route_finalized=crisis_route_finalized,
            user_consented=True,
        )
        if not policy.allowed:
            result = ToolRunResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.name,
                status="unknown_tool" if policy.reason == "unknown_tool" else "blocked",
                output={},
                blocked_reason=policy.reason,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            self._trace_tool(agent_name=agent_name, result=result, args=call.arguments)
            return result
        assert spec is not None

        try:
            parsed = spec.input_model.model_validate(call.arguments)
        except ValidationError as exc:
            result = ToolRunResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.name,
                status="invalid_args",
                output={"error_count": len(exc.errors())},
                blocked_reason="schema_validation_failed",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            self._trace_tool(agent_name=agent_name, result=result, args=call.arguments)
            return result

        try:
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(spec.handler, parsed.model_dump(), context)
                output = future.result(timeout=spec.timeout_ms / 1000.0)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            result = ToolRunResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.name,
                status="ok",
                output=_bounded_output(dict(output or {})),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except TimeoutError:
            result = ToolRunResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.name,
                status="timeout",
                output={},
                blocked_reason="tool_timeout",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:
            logger.warning("agentic tool failed: %s", exc)
            result = ToolRunResult(
                tool_call_id=call.tool_call_id,
                tool_name=call.name,
                status="error",
                output={"error_type": type(exc).__name__},
                blocked_reason="tool_error",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        self._trace_tool(agent_name=agent_name, result=result, args=call.arguments)
        return result

    def _trace_tool(self, *, agent_name: str, result: ToolRunResult, args: dict[str, Any]) -> None:
        tracer = get_active_tracer()
        if tracer is None:
            return
        try:
            tracer.event(
                "agentic.tool_call",
                input_data={
                    "tool_name": result.tool_name,
                    "arg_keys": sorted(str(key) for key in args.keys())[:20],
                },
                output_data={
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                    "result_size": len(json.dumps(result.output, ensure_ascii=False, default=str)),
                    "blocked_reason": result.blocked_reason,
                },
                metadata={"agent": agent_name, "tool_name": result.tool_name, "status": result.status},
            )
        except Exception:
            pass
