from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafetyPolicyDecision(StrictSchema):
    policy_action: Literal[
        "allow",
        "supportive_continuation",
        "constrain_response",
        "block_harmful_instruction",
    ]
    risk_level: int = Field(ge=0, le=5)
    distress_score: float = Field(ge=0.0, le=1.0)
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    persona_style_strength: float = Field(ge=0.0, le=1.0)
    ui_support_mode: Literal["none", "optional_sheet", "compact_card"] = "none"
    audit_required: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class ContextPack(StrictSchema):
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    active_memory: dict[str, Any] | None = None
    onboarding_summary: dict[str, Any] | None = None
    mood_context: dict[str, Any] | None = None
    nutrition_context: dict[str, Any] | None = None
    screening_summary: dict[str, Any] | None = None
    resource_candidates: list[dict[str, Any]] = Field(default_factory=list)
    persona_context: dict[str, Any] | None = None
    safety_policy: SafetyPolicyDecision


class AdvisorAdvice(StrictSchema):
    advisor_id: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    advice_to_friend: list[str] = Field(default_factory=list)
    suggested_response_moves: list[str] = Field(default_factory=list)
    forbidden_moves: list[str] = Field(default_factory=list)
    should_use: bool = False


class FriendAgentOutput(StrictSchema):
    final_text: str = Field(min_length=1)
    response_intent: Literal[
        "listen",
        "reflect",
        "advise",
        "resource",
        "nutrition",
        "grounding",
        "continue_story",
    ]
    used_advisor_ids: list[str] = Field(default_factory=list)
    used_resource_ids: list[str] = Field(default_factory=list)
    suggested_next_action: dict[str, Any] | None = None
    memory_write_candidates: list[dict[str, Any]] = Field(default_factory=list)
    tts_candidate: dict[str, Any] | None = None
    meme_candidate: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class AnalystBundle(StrictSchema):
    user_id: str = Field(min_length=1, max_length=50)
    time_window: dict[str, Any]
    dominant_emotions: list[str] = Field(default_factory=list)
    recurring_triggers: list[str] = Field(default_factory=list)
    cognitive_patterns: list[dict[str, Any]] = Field(default_factory=list)
    nutrition_patterns: list[dict[str, Any]] = Field(default_factory=list)
    coping_preferences: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    missing_info: list[str] = Field(default_factory=list)
    safe_dashboard_candidates: list[dict[str, Any]] = Field(default_factory=list)


class WorkerJob(StrictSchema):
    job_id: str = Field(min_length=1, max_length=100)
    job_type: Literal["memory_extraction", "dashboard_insight", "tts_render", "analyst_event", "analyst_run"]
    user_id: str = Field(min_length=1, max_length=50)
    session_id: str | None = Field(default=None, max_length=50)
    payload_ref: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    status: Literal["queued", "processing", "succeeded", "failed", "retrying"]
    attempt_count: int = Field(ge=0)
    trace_id: str | None = Field(default=None, max_length=80)
    request_id: str | None = Field(default=None, max_length=80)
