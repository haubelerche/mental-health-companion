from __future__ import annotations

from typing import Any

from pydantic import Field

from .contracts import SafetyPolicyDecision, StrictSchema


class ContextPackInput(StrictSchema):
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    user_message: str = Field(min_length=1, max_length=2000)
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    safety_policy: SafetyPolicyDecision
    persona_id: str = Field(default="dung_luong", min_length=1, max_length=50)
    timeout_ms: int = Field(default=300, ge=50, le=3000)
