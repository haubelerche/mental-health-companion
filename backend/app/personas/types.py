"""
Persona data contracts — immutable config + mutable session state.
Plan: .claude/plan/01_PERSONA_REGISTRY_AND_CONTRACT.md §4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PersonaId = Literal["dung_luong", "dat_le", "hau_luong"]
PersonaRiskClass = Literal["default", "guidance", "calm_low_risk"]
ActivationMode = Literal["default", "explicit_opt_in", "explicit_or_suggested", "unlockable"]
QualityGuardProfile = Literal[
    "supportive_default",
    "mentor_reflective",
    "quiet_minimal",
]


@dataclass(frozen=True)
class PersonaConfig:
    persona_id: str
    display_name: str
    user_facing_name: str
    short_description: str
    legacy_aliases: list[str]

    risk_class: PersonaRiskClass
    activation_mode: ActivationMode
    quality_guard_profile: QualityGuardProfile

    is_core: bool
    is_unlockable: bool
    unlock_item_id: str | None

    pronoun_self: str
    pronoun_user: str
    tone_summary: str
    style_rules: list[str]
    forbidden_rules: list[str]
    prompt_contract: str

    max_reply_chars: int
    temperature_delta: float
    can_use_action_text: bool
    action_text_style: str | None

    min_distress: float
    max_distress: float
    auto_deactivate_distress: float | None
    max_session_turns: int | None
    max_session_minutes: int | None

    trigger_keywords: list[str] = field(default_factory=list)
    suggestion_signals: list[str] = field(default_factory=list)
    tts_style_id: str | None = None
    tts_voice_env_key: str | None = None
    requires_setup: list[str] = field(default_factory=list)
    allow_when_sos: bool = False


@dataclass
class PersonaState:
    active_persona_id: str = "dung_luong"
    preferred_persona_id: str = "dung_luong"
    persona_locked: bool = False
    selected_by_user: bool = False
    active_since_turn: int = 0
    active_since_ts: float | None = None
    last_switch_reason: str | None = None
    last_safety_override_ts: float | None = None
    cooldown_until_turn: int | None = None
    current_turn: int = 0
