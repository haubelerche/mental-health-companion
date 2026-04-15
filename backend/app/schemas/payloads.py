from datetime import date

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    disclaimer_accepted: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=50)


class MoodCheckinRequest(BaseModel):
    mood: str = Field(min_length=1, max_length=50)
    emoji: str | None = Field(default=None, max_length=10)
    note: str | None = None


class MoodCheckinPatchRequest(BaseModel):
    mood: str | None = Field(default=None, min_length=1, max_length=50)
    emoji: str | None = Field(default=None, max_length=10)
    note: str | None = None


class JournalCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    prompt_id: str | None = Field(default=None, max_length=50)


class PlayEventRequest(BaseModel):
    event: str
    duration_sec: int = Field(ge=0)
    percent: int = Field(ge=0, le=100)


class ClinicsRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius_km: int | None = Field(default=None, ge=1, le=50)


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    totp_code: str = Field(min_length=6, max_length=10)
