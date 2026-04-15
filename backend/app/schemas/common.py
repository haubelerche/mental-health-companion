from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class Envelope(BaseModel):
    success: bool
    data: Any | None
    error: ErrorBody | None


class SessionPreview(BaseModel):
    session_id: str
    last_message_at: datetime
    preview: str | None
