from __future__ import annotations

import json
from types import SimpleNamespace

from pydantic import BaseModel, Field

from app.agentic.policy import evaluate_tool_policy
from app.agentic.registry import ToolRegistry, build_default_tool_registry
from app.agentic.runner import AgentRunner
from app.agentic.schemas import ToolSpec


class _EchoInput(BaseModel):
    text: str = Field(min_length=1, max_length=20)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0
        self.kwargs = []

    def create(self, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        if self.calls == 1:
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            role="assistant",
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    id="call_1",
                                    function=SimpleNamespace(
                                        name="echo_tool",
                                        arguments=json.dumps({"text": "hello"}),
                                    ),
                                )
                            ],
                        )
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
            )
        assert kwargs["messages"][-1]["role"] == "tool"
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(role="assistant", content='{"reply":"ok"}', tool_calls=[]))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def _echo_handler(args: dict, context: dict) -> dict:
    return {"echo": args["text"], "user_message_len": len(context.get("user_message", ""))}


def test_default_registry_exposes_openai_tool_schemas() -> None:
    registry = build_default_tool_registry()
    schemas = registry.openai_tools_for_agent("friend", distress_score=0.2)

    names = {item["function"]["name"] for item in schemas}
    assert "memory_lookup" in names
    assert "resource_search" in names
    assert "context_pack_read" not in names
    assert all(item["type"] == "function" for item in schemas)


def test_policy_blocks_crisis_and_distress_over_limit() -> None:
    spec = build_default_tool_registry().get("resource_search")

    crisis_decision = evaluate_tool_policy(
        spec=spec,
        agent_name="friend",
        distress_score=0.2,
        crisis_route_finalized=True,
    )
    high_distress_decision = evaluate_tool_policy(
        spec=spec,
        agent_name="friend",
        distress_score=0.95,
        crisis_route_finalized=False,
    )

    assert not crisis_decision.allowed
    assert crisis_decision.reason == "crisis_route_finalized"
    assert not high_distress_decision.allowed
    assert high_distress_decision.reason == "distress_above_tool_limit"


def test_agent_runner_executes_tool_loop_and_appends_tool_result() -> None:
    registry = ToolRegistry(
        [
            ToolSpec(
                name="echo_tool",
                description="Echo test input.",
                input_model=_EchoInput,
                handler=_echo_handler,
                allowed_agents=("friend",),
            )
        ]
    )
    client = _FakeClient()

    result = AgentRunner(registry=registry).run(
        client=client,
        model="fake-model",
        messages=[{"role": "user", "content": "hello"}],
        agent_name="friend",
        context={"user_message": "hello", "distress_score": 0.1},
    )

    assert result.content == '{"reply":"ok"}'
    assert len(result.tool_results) == 1
    assert result.tool_results[0].status == "ok"
    assert result.tool_results[0].output["echo"] == "hello"
    assert client.chat.completions.calls == 2
    assert client.chat.completions.kwargs[0]["tools"][0]["function"]["name"] == "echo_tool"


def test_agent_runner_reports_invalid_args_without_crashing() -> None:
    registry = ToolRegistry(
        [
            ToolSpec(
                name="echo_tool",
                description="Echo test input.",
                input_model=_EchoInput,
                handler=_echo_handler,
                allowed_agents=("friend",),
            )
        ]
    )
    client = _FakeClient()
    client.chat.completions.create = lambda **kwargs: SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    role="assistant",
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="bad_1",
                            function=SimpleNamespace(name="echo_tool", arguments=json.dumps({"text": ""})),
                        )
                    ],
                )
            )
        ],
        usage=None,
    )

    result = AgentRunner(registry=registry).run(
        client=client,
        model="fake-model",
        messages=[{"role": "user", "content": "hello"}],
        agent_name="friend",
        context={"user_message": "hello", "distress_score": 0.1},
    )

    assert result.tool_results
    assert result.tool_results[0].status == "invalid_args"


def test_agent_runner_records_unknown_tool_as_policy_block() -> None:
    client = _FakeClient()
    client.chat.completions.create = lambda **kwargs: SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    role="assistant",
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="unknown_1",
                            function=SimpleNamespace(name="unknown_tool", arguments="{}"),
                        )
                    ],
                )
            )
        ],
        usage=None,
    )

    result = AgentRunner(registry=ToolRegistry()).run(
        client=client,
        model="fake-model",
        messages=[{"role": "user", "content": "hello"}],
        agent_name="friend",
        context={"user_message": "hello", "distress_score": 0.1},
    )

    assert result.policy_blocks
    assert result.policy_blocks[0].status == "unknown_tool"
    assert result.policy_blocks[0].blocked_reason == "unknown_tool"


def test_agent_runner_omits_tools_when_crisis_route_finalized() -> None:
    registry = ToolRegistry(
        [
            ToolSpec(
                name="echo_tool",
                description="Echo test input.",
                input_model=_EchoInput,
                handler=_echo_handler,
                allowed_agents=("friend",),
            )
        ]
    )
    client = _FakeClient()
    seen_kwargs = []

    def _final_without_tools(**kwargs):
        seen_kwargs.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(role="assistant", content='{"reply":"safe"}', tool_calls=[]))],
            usage=None,
        )

    client.chat.completions.create = _final_without_tools

    result = AgentRunner(registry=registry).run(
        client=client,
        model="fake-model",
        messages=[{"role": "user", "content": "help"}],
        agent_name="friend",
        context={"user_message": "help", "distress_score": 0.1, "crisis_route_finalized": True},
    )

    assert result.content == '{"reply":"safe"}'
    assert "tools" not in seen_kwargs[0]
