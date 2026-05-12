from __future__ import annotations

from typing import Literal

from pydantic import Field

from .contracts import StrictSchema


class ResourceSelectionInput(StrictSchema):
    conversation_need: Literal["grounding", "journaling", "sleep", "task_breakdown", "reflection"]
    emotion: str = Field(default="", max_length=64)
    time_available_minutes: int = Field(default=3, ge=1, le=90)
    user_preference: str | None = Field(default=None, max_length=32)


class ResourceSuggestion(StrictSchema):
    resource_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    why_this: str = Field(min_length=1, max_length=280)
    delivery_mode: Literal["inline_short", "card", "library_link"] = "card"

