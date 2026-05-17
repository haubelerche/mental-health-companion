from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class DistressMessageSegment(BaseModel):
    type: Literal["text", "line_break", "route_link"]
    text: str | None = Field(default=None, max_length=500)
    route: str | None = Field(default=None, max_length=200)


class DistressSupportPopup(BaseModel):
    show: bool = False
    popup_id: str | None = None
    character_id: Literal["dat_le"] = "dat_le"
    character_label: str = "Đạt"
    asset_path: str = "/frontend/assets/dat-le-shock-sos.png"
    title: str = "Đạt đang ở đây"
    message_html: str | None = None
    message_segments: list[DistressMessageSegment] = Field(default_factory=list)
    support_route: str = "/serene/support"
    breathing_exercise_route: str = "/serene/exercises?exercise=anxiety_breathing"
    cooldown_seconds: int = 900
    reason: str | None = None


class DistressConversationUi(BaseModel):
    mode: Literal["none", "distress_soft_support", "sos_soft_popup"] = "none"
    suppress_inline_crisis_cards: bool = False
    support_popup: DistressSupportPopup | None = None
    allow_quick_replies: bool = True
    preferred_input_focus: bool = True


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
    persona_id: str | None = Field(default=None, max_length=50)


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
    session_id: str | None = Field(default=None, max_length=50)
    locale: str = Field(default="vi-VN", min_length=2, max_length=16)


class CheckinQuickRequest(BaseModel):
    mood: str = Field(min_length=1, max_length=50)
    time_bucket: Literal["morning", "afternoon", "evening", "other"] | None = None
    stress_level: int | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    sleep_start: str | None = Field(default=None, max_length=10)
    wake_time: str | None = Field(default=None, max_length=10)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    study_hours: float | None = Field(default=None, ge=0, le=24)
    emotions: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
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


class AdminResourceCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    format: str = Field(min_length=1, max_length=20)
    duration_sec: int = Field(ge=1)
    storage_key: str = Field(min_length=1, max_length=500)
    thumbnail_key: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True


class AdminResourceUpdateRequest(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    format: str | None = Field(default=None, min_length=1, max_length=20)
    duration_sec: int | None = Field(default=None, ge=1)
    storage_key: str | None = Field(default=None, min_length=1, max_length=500)
    thumbnail_key: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    is_active: bool | None = None

class AdminAgentCrawlRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    limit: int = Field(default=5, ge=1, le=50)


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


class CrisisReviewRequest(BaseModel):
    reviewed: bool = True
    note: str | None = Field(default=None, max_length=500)


class OnboardingCompleteRequest(BaseModel):
    disclaimer_accepted: bool
    nickname: str = Field(min_length=1, max_length=64)
    age_group: str = Field(min_length=1, max_length=32)
    emotional_state: str = Field(
        pattern="^(difficult_recently|ongoing_challenges|doing_okay)$"
    )
    primary_concern: str | None = Field(default=None, max_length=64)
    support_level: str | None = Field(default=None, pattern="^(excellent|good|limited|poor)$")
    stress_level: int = Field(ge=0, le=4)
    wake_time: str = Field(pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    bed_time: str = Field(pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    practice_ids: list[str] = Field(default_factory=list, max_length=8)


class OnboardingTourStartRequest(BaseModel):
    variant: str = Field(default="first_run", max_length=50)


class OnboardingTourProgressRequest(BaseModel):
    step_id: str = Field(min_length=1, max_length=80)
    skipped: bool = False
    next_step_id: str | None = Field(default=None, max_length=80)


class PersonaUpdateRequest(BaseModel):
    persona_id: str = Field(
        min_length=2,
        max_length=50,
        pattern="^[a-z_]+$",
    )


# ---------------------------------------------------------------------------
# Letter System 
# ---------------------------------------------------------------------------

class LetterSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class LetterReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class LetterReactRequest(BaseModel):
    reaction_type: str = Field(default="heart", max_length=20)


class LetterReportRequest(BaseModel):
    letter_id: str = Field(min_length=1, max_length=50)
    report_category: str = Field(min_length=1, max_length=30)
    reason: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)

class AdminUserUpdateRequest(BaseModel):
    is_active: bool | None = None
    display_name: str | None = Field(default=None, max_length=255)
