from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator


class SignupRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    disclaimer_accepted: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=500)
    new_password: str = Field(min_length=8, max_length=128)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=50)


class GuestChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    guest_session_id: str | None = Field(default=None, max_length=80)


class ChatEndRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=50)


class SafetyCheckRequest(BaseModel):
    overwhelmed: str = Field(max_length=500)
    unsafe: str = Field(max_length=500)
    need_help_now: str = Field(max_length=500)


class PolicyAckRequest(BaseModel):
    policy_version: str = Field(min_length=1, max_length=32)


class VoiceConsentRequest(BaseModel):
    consent: bool


class TrustedContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=3, max_length=32)
    relation: str | None = Field(default=None, max_length=50)


class SafetyEscalateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=50)
    risk_level: int = Field(ge=0, le=5)
    reason: str = Field(min_length=1, max_length=500)


class GuestHeartbeatRequest(BaseModel):
    guest_session_id: str = Field(min_length=1, max_length=80)


class GuestChoiceRequest(BaseModel):
    guest_session_id: str = Field(min_length=1, max_length=80)
    choice: str = Field(pattern="^(checkin|screening|chat)$")


class ScreeningSubmitRequest(BaseModel):
    instrument_id: str = Field(min_length=1, max_length=50)
    answers: dict[str, int]


class CheckinQuickRequest(BaseModel):
    mood: str = Field(min_length=1, max_length=50)
    stress_level: int | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    study_hours: float | None = Field(default=None, ge=0, le=24)
    note: str | None = None


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

    @model_validator(mode="after")
    def lat_lng_pair(self) -> "ClinicsRequest":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be provided together")
        return self


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    totp_code: str = Field(min_length=6, max_length=10)
