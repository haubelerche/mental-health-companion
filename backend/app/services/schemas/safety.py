from __future__ import annotations

from pydantic import Field

from .contracts import SafetyPolicyDecision, StrictSchema


class SafetyPolicyInput(StrictSchema):
    user_message: str = Field(min_length=1, max_length=2000)
    recent_user_messages: list[str] = Field(default_factory=list)


class SafetyValidationInput(StrictSchema):
    final_text: str = Field(min_length=1)
    surface: str = Field(default="chat", pattern="^(chat|dashboard|tts)$")


__all__ = [
    "SafetyPolicyDecision",
    "SafetyPolicyInput",
    "SafetyValidationInput",
]
