from __future__ import annotations

from app.agentic.schemas import ToolPolicyDecision, ToolSpec


def evaluate_tool_policy(
    *,
    spec: ToolSpec | None,
    agent_name: str,
    distress_score: float,
    crisis_route_finalized: bool = False,
    user_consented: bool = True,
) -> ToolPolicyDecision:
    if spec is None:
        return ToolPolicyDecision(allowed=False, reason="unknown_tool")
    if agent_name not in spec.allowed_agents:
        return ToolPolicyDecision(allowed=False, reason="agent_not_allowed")
    if crisis_route_finalized:
        return ToolPolicyDecision(allowed=False, reason="crisis_route_finalized")
    if float(distress_score or 0.0) > float(spec.max_distress_score):
        return ToolPolicyDecision(allowed=False, reason="distress_above_tool_limit")
    if spec.requires_user_consent and not user_consented:
        return ToolPolicyDecision(allowed=False, reason="missing_user_consent")
    return ToolPolicyDecision(allowed=True, reason="allowed")
