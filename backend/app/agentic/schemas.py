from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictAgenticSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyToolInput(StrictAgenticSchema):
    """Schema for tools that do not require model-supplied arguments."""


class MemoryLookupInput(StrictAgenticSchema):
    query: str = Field(default="", max_length=300)
    limit: int = Field(default=3, ge=1, le=5)


class ResourceSearchInput(StrictAgenticSchema):
    query: str = Field(default="", max_length=300)
    limit: int = Field(default=2, ge=1, le=3)


class AdvisorConsultInput(StrictAgenticSchema):
    advisor_ids: list[str] = Field(default_factory=list, max_length=2)
    context_summary: str = Field(default="", max_length=500)


class ContextPackReadInput(StrictAgenticSchema):
    max_chars: int = Field(default=900, ge=200, le=1500)


class NutritionContextReadInput(StrictAgenticSchema):
    limit: int = Field(default=4, ge=1, le=8)


class SafetyPolicyCheckInput(StrictAgenticSchema):
    include_reason_codes: bool = False


class ToolCall(StrictAgenticSchema):
    tool_call_id: str = Field(default="", max_length=160)
    name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolPolicyDecision(StrictAgenticSchema):
    allowed: bool
    reason: str = Field(default="allowed", max_length=200)


class ToolRunRequest(StrictAgenticSchema):
    agent_name: Literal["analyst", "friend"]
    tool_call: ToolCall
    distress_score: float = Field(ge=0.0, le=1.0)
    persona_id: str = Field(default="", max_length=80)
    crisis_route_finalized: bool = False


class ToolRunResult(StrictAgenticSchema):
    tool_call_id: str = Field(default="", max_length=160)
    tool_name: str = Field(min_length=1, max_length=100)
    status: Literal["ok", "blocked", "error", "timeout", "invalid_args", "unknown_tool"]
    output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)
    blocked_reason: str | None = Field(default=None, max_length=240)


ToolHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class ToolSpec(StrictAgenticSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    input_model: type[BaseModel]
    handler: ToolHandler
    timeout_ms: int = Field(default=1200, ge=100, le=5000)
    allowed_agents: tuple[Literal["analyst", "friend"], ...] = ("analyst", "friend")
    max_distress_score: float = Field(default=0.89, ge=0.0, le=1.0)
    requires_user_consent: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    def openai_tool_schema(self) -> dict[str, Any]:
        schema = self.input_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


class AgentRunResult(StrictAgenticSchema):
    content: str = ""
    tool_results: list[ToolRunResult] = Field(default_factory=list)
    policy_blocks: list[ToolRunResult] = Field(default_factory=list)
    raw_response: Any | None = None
    agent_run_id: str = Field(default="", max_length=80)

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
