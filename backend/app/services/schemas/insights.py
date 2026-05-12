from __future__ import annotations

from pydantic import Field

from .contracts import StrictSchema


class DashboardSafeInsight(StrictSchema):
    insight_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)
    user_safe_summary: str = Field(min_length=1, max_length=600)
    confidence: str = Field(pattern="^(low|medium|high)$")
    evidence_count: int = Field(ge=1)

