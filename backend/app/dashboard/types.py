from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

DashboardReadinessLevel = Literal[
    "no_data",
    "first_signals",
    "early_insight",
    "weekly_trend",
    "stable_pattern",
]


class DashboardDataSufficiency(BaseModel):
    readiness_level: DashboardReadinessLevel
    active_days: int = Field(ge=0)
    mood_checkin_count: int = Field(ge=0)
    total_session_count: int = Field(ge=0)
    deep_session_count: int = Field(ge=0)
    calendar_days_observed: int = Field(ge=0, description="Inclusive span min(date)..max(date)")
    evidence_window_start: date | None = None
    evidence_window_end: date | None = None
    message: str
    next_data_needed: list[str]


class DashboardInsightCard(BaseModel):
    insight_id: str
    title: str
    user_safe_summary: str
    evidence_count: int = Field(ge=0)
    evidence_sources: list[str]
    confidence: Literal["low", "medium", "high"]
    severity_band: Literal["neutral", "watch", "supportive_attention"]
    suggested_action: str | None = None
    evidence_window_start: date | None = None
    evidence_window_end: date | None = None
    updated_at: datetime


class WellnessDimensionCard(BaseModel):
    dimension: Literal["emotion", "sleep", "mindfulness", "connection", "body", "growth"]
    label: str
    status: Literal["unknown", "limited_data", "steady", "needs_attention", "improving"]
    score: int | None = Field(default=None, ge=0, le=100)
    explanation: str
    evidence_count: int = Field(ge=0)
    suggested_action: str | None = None


class CheckinHistoryItem(BaseModel):
    checkin_id: str
    logged_at: datetime
    date: date
    time_bucket: Literal["morning", "afternoon", "evening", "other"]
    mood_label: str | None = None
    mood_score: int | None = None
    emotions: list[str]
    triggers: list[str]
    note: str | None = None
    reward_granted: bool | None = None


class CheckinHistoryDay(BaseModel):
    date: date
    completed: bool
    checkins: list[CheckinHistoryItem]
    streak_day_index: int | None = None


class MoodSeriesPoint(BaseModel):
    date: date
    mood_score: float
    mood_score_pct: int = Field(ge=0, le=100)
    label: str
    checkin_count: int = Field(ge=1)


class DashboardProgressSnapshot(BaseModel):
    streak_days: int = Field(ge=0)
    total_sessions: int = Field(ge=0)
    days_active_last_30: int = Field(ge=0)
    breathing_sessions: int = Field(ge=0)
    effective_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class DashboardReflectSummary(BaseModel):
    sufficiency: DashboardDataSufficiency
    top_insights: list[DashboardInsightCard]
    wellness_dimensions: list[WellnessDimensionCard]
    mood_series: list[dict]
    checkin_history_preview: list[CheckinHistoryDay]
    radar_available: bool
    progress: DashboardProgressSnapshot
