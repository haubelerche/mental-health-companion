from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AnalystRunType = Literal["turn", "daily", "rolling_3d", "weekly", "on_demand_dashboard", "post_screening"]
AnalystRunStatus = Literal["queued", "running", "completed", "failed", "skipped_insufficient_data", "blocked_by_safety"]
LocalPeriod = Literal["morning", "afternoon", "evening", "unknown"]
Sensitivity = Literal["low", "medium", "high", "restricted"]


class AnalystRunRequest(BaseModel):
    user_id: str
    run_type: AnalystRunType
    window_start: datetime
    window_end: datetime
    data_cutoff_at: datetime
    force: bool = False


class AnalystSourceEvent(BaseModel):
    event_id: str
    user_id: str
    source_table: str
    source_id: str
    event_type: str
    occurred_at: datetime
    local_date: date | None
    local_period: LocalPeriod
    payload: dict[str, Any] = Field(default_factory=dict)
    sensitivity: Sensitivity
    text_for_llm: str | None = None
    numeric_features: dict[str, Any] = Field(default_factory=dict)


class AnalystFeatureSnapshotPayload(BaseModel):
    mood: dict[str, Any] = Field(default_factory=dict)
    nutrition: dict[str, Any] = Field(default_factory=dict)
    screening: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    conversation: dict[str, Any] = Field(default_factory=dict)
    engagement: dict[str, Any] = Field(default_factory=dict)
    safety_internal: dict[str, Any] = Field(default_factory=dict)
    data_quality: dict[str, Any] = Field(default_factory=dict)


class AnalystLLMInput(BaseModel):
    user_id: str
    run_type: str
    window_start: datetime
    window_end: datetime
    data_cutoff_at: datetime
    compact_features: dict[str, Any]
    redacted_text_evidence: list[dict[str, Any]] = Field(default_factory=list)
    existing_insights_summary: list[dict[str, Any]] = Field(default_factory=list)


class AnalystLLMOutput(BaseModel):
    status: Literal["success", "insufficient_signal", "safety_restricted"]
    emotional_themes: list[str] = Field(default_factory=list)
    recurring_stressors: list[str] = Field(default_factory=list)
    coping_preferences: list[str] = Field(default_factory=list)
    nutrition_links: list[dict[str, Any]] = Field(default_factory=list)
    mood_pattern_candidates: list[dict[str, Any]] = Field(default_factory=list)
    user_safe_insight_candidates: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    forbidden_output_detected: bool = False


class AnalystRunResult(BaseModel):
    run_id: str
    status: AnalystRunStatus
    snapshot_id: str | None = None
    source_counts: dict[str, int] = Field(default_factory=dict)
    missing_sources: list[str] = Field(default_factory=list)
    created_insight_ids: list[str] = Field(default_factory=list)
    skipped_reason: str | None = None
