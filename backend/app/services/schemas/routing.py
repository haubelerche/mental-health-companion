from __future__ import annotations

from typing import Literal

from pydantic import Field

from .contracts import StrictSchema


class RoutingDecision(StrictSchema):
    route_tier: Literal["fast", "service_only", "advisor_assisted"]
    reason_codes: list[str] = Field(default_factory=list)
    should_call_advisors: bool = False


class AdvisorSelection(StrictSchema):
    advisor_ids: list[str] = Field(default_factory=list, max_length=2)
    max_rounds: int = Field(default=1, ge=1, le=1)
    timeout_ms: int = Field(default=1200, ge=100, le=5000)

