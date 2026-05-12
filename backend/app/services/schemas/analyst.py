from __future__ import annotations

from pydantic import Field

from .contracts import AnalystBundle, StrictSchema


class AnalystInput(StrictSchema):
    user_id: str = Field(min_length=1, max_length=50)
    session_id: str | None = Field(default=None, max_length=50)
    events: list[dict] = Field(default_factory=list)


__all__ = ["AnalystBundle", "AnalystInput"]

