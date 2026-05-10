"""Voice/TTS type definitions — Plan 08.

Canonical status vocabulary (rule: voice-tts.md, plan 08 §14.4).
Frontend polling stops on terminal statuses.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

VoiceIntent = Literal[
    "sos_grounding",
    "sos_stay_with_user",
    "sos_next_safe_step",
    "elevated_encouragement",
    "elevated_lightness",
    "elevated_gentle_reminder",
    "casual_praise",
    "casual_playful_checkin",
    "casual_habit_nudge",
]

VoiceRiskMode = Literal["normal", "elevated", "sos"]
VoicePriority = Literal["low", "normal", "high"]
VoiceDedupePolicy = Literal["reuse_if_ready", "reuse_or_variant", "force_context_variant"]

TTSStatus = Literal[
    "queued",
    "processing",
    "ready",
    "failed",
    "skipped_duplicate",
    "cache_hit",
    "provider_disabled",
    "cancelled",
    "expired",
]

# Statuses at which frontend polling should stop.
TTS_TERMINAL_STATUSES: frozenset[str] = frozenset({
    "ready",
    "failed",
    "skipped_duplicate",
    "cache_hit",
    "provider_disabled",
    "cancelled",
    "expired",
})

# Statuses considered healthy (reusable for cache_hit path).
TTS_REUSABLE_STATUSES: frozenset[str] = frozenset({
    "queued",
    "processing",
    "ready",
    "cache_hit",
    "skipped_duplicate",
})


class VoiceMessagePlan(BaseModel):
    id: str
    intent: VoiceIntent
    voice_script: str = Field(min_length=1, max_length=900)
    priority: VoicePriority
    should_enqueue: bool
    dedupe_policy: VoiceDedupePolicy
    max_duration_seconds: int = Field(ge=5, le=60)
    reason_codes: list[str] = Field(default_factory=list)


class VoicePolicyDecision(BaseModel):
    should_attach_voice: bool
    risk_mode: VoiceRiskMode
    ordinary_cooldown_bypassed: bool = False
    min_voice_cards: int = 0
    max_voice_cards: int = 1
    voice_messages: list[VoiceMessagePlan] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class VoiceMessageClientPayload(BaseModel):
    id: str
    intent: str
    title: str
    status: TTSStatus
    tts_job_id: str | None = None
    audio_url: str | None = None
    error_code: str | None = None
