from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .contracts import AdvisorAdvice, StrictSchema


class AdvisorAdviceEnvelope(StrictSchema):
    advice: AdvisorAdvice

    @model_validator(mode="before")
    @classmethod
    def _reject_final_text(cls, data):
        if isinstance(data, dict):
            payload = data.get("advice") if isinstance(data.get("advice"), dict) else data
            if isinstance(payload, dict) and "final_text" in payload:
                raise ValueError("advisor output must not include final_text")
        return data


class AdvisorRunRequest(StrictSchema):
    advisor_id: str = Field(min_length=1, max_length=100)
    user_message: str = Field(min_length=1, max_length=2000)
    context_summary: str = Field(default="", max_length=1200)


class AdvisorCase(StrictSchema):
    case_id: str = Field(min_length=1, max_length=80)
    raw_case_id: str | None = Field(default=None, max_length=120)
    language: str = Field(default="vi", max_length=16)
    user_context: str = Field(min_length=1, max_length=1200)
    primary_problem: str | None = Field(default=None, max_length=500)
    topic_tags: list[str] = Field(default_factory=list, max_length=12)
    emotional_state_tags: list[str] = Field(default_factory=list, max_length=12)
    interaction_need: str | None = Field(default=None, max_length=80)
    cognitive_pattern_tags: list[str] = Field(default_factory=list, max_length=12)
    counseling_goal: str | None = Field(default=None, max_length=500)
    recommended_approach: str | None = Field(default=None, max_length=500)
    intervention_steps: list[str] = Field(default_factory=list, max_length=6)
    reflection_questions: list[str] = Field(default_factory=list, max_length=4)
    do_say: list[str] = Field(default_factory=list, max_length=6)
    do_not_say: list[str] = Field(default_factory=list, max_length=6)
    risk_flags: list[str] = Field(default_factory=list, max_length=8)
    source_response_summary: str | None = Field(default=None, max_length=700)
    safety_review_status: str = Field(default="pending", max_length=30)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_score: float | None = Field(default=None)


class AdvisorCaseRetrievalResult(StrictSchema):
    cases: list[AdvisorCase] = Field(default_factory=list, max_length=5)
    approved_only: bool = True
    fallback_used: bool = False


class CounselingGuidance(StrictSchema):
    case_understanding: str = Field(default="", max_length=700)
    likely_patterns: list[str] = Field(default_factory=list, max_length=6)
    response_goal: str = Field(default="", max_length=500)
    recommended_moves: list[str] = Field(default_factory=list, max_length=6)
    one_reflection_question: str | None = Field(default=None, max_length=260)
    one_practical_step: str | None = Field(default=None, max_length=300)
    avoid: list[str] = Field(default_factory=list, max_length=8)
    case_refs: list[str] = Field(default_factory=list, max_length=5)
    metadata: dict[str, Any] = Field(default_factory=dict)
