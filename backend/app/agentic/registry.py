from __future__ import annotations

from . import tools
from app.agentic.schemas import (
    AdvisorConsultInput,
    ContextPackReadInput,
    MemoryLookupInput,
    NutritionContextReadInput,
    ResourceSearchInput,
    SafetyPolicyCheckInput,
    ToolSpec,
)


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(str(name or ""))

    def for_agent(self, agent_name: str, *, distress_score: float, crisis_route_finalized: bool = False) -> list[ToolSpec]:
        if crisis_route_finalized:
            return []
        return [
            spec
            for spec in self._specs.values()
            if agent_name in spec.allowed_agents and float(distress_score or 0.0) <= spec.max_distress_score
        ]

    def openai_tools_for_agent(
        self,
        agent_name: str,
        *,
        distress_score: float,
        crisis_route_finalized: bool = False,
    ) -> list[dict]:
        return [
            spec.openai_tool_schema()
            for spec in self.for_agent(
                agent_name,
                distress_score=distress_score,
                crisis_route_finalized=crisis_route_finalized,
            )
        ]


def build_default_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolSpec(
                name="memory_lookup",
                description="Read a small sanitized memory slice already loaded for this chat turn.",
                input_model=MemoryLookupInput,
                handler=tools.memory_lookup,
                allowed_agents=("analyst", "friend"),
                max_distress_score=0.82,
            ),
            ToolSpec(
                name="resource_search",
                description="Return curated internal Serene resources that may fit the current support need.",
                input_model=ResourceSearchInput,
                handler=tools.resource_search,
                allowed_agents=("friend",),
                max_distress_score=0.69,
            ),
            ToolSpec(
                name="advisor_consult",
                description="Consult internal non-user-facing advisors for response moves and constraints.",
                input_model=AdvisorConsultInput,
                handler=tools.advisor_consult,
                allowed_agents=("analyst", "friend"),
                max_distress_score=0.82,
            ),
            ToolSpec(
                name="context_pack_read",
                description="Read bounded sanitized chat context, mood, triggers, goals, and trajectory.",
                input_model=ContextPackReadInput,
                handler=tools.context_pack_read,
                allowed_agents=("analyst",),
                max_distress_score=0.82,
            ),
            ToolSpec(
                name="nutrition_context_read",
                description="Read bounded nutrition check-in context for today's turn.",
                input_model=NutritionContextReadInput,
                handler=tools.nutrition_context_read,
                allowed_agents=("analyst", "friend"),
                max_distress_score=0.74,
            ),
            ToolSpec(
                name="safety_policy_check",
                description="Return user-safe response constraints derived from deterministic safety policy.",
                input_model=SafetyPolicyCheckInput,
                handler=tools.safety_policy_check,
                allowed_agents=("analyst", "friend"),
                max_distress_score=0.89,
            ),
        ]
    )
