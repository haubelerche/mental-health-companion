"""Vietnamese style-state selection for Serene responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


PronounStyle = Literal["minh_ban", "toi_ban", "tui_ban", "to_cau"]


class VietnameseChatStyleState(BaseModel):
    sentence_initial_uppercase_required: bool = False
    lowercase_chat_allowed: bool = True
    preserve_proper_nouns: bool = True
    pronoun_style: PronounStyle = "minh_ban"
    tone_level: int = Field(ge=0, le=3)
    slang_level: int = Field(ge=0, le=3)
    humor_level: int = Field(ge=0, le=3)
    warmth_level: int = Field(ge=0, le=3)
    max_sentences: int = Field(default=3, ge=1, le=7)
    max_questions: int = 1
    avoid_therapy_script: bool = True
    avoid_forced_positivity: bool = True
    allow_playful: bool = False


# Backward-compatible name used by existing modules and tests.
VietnameseStyleState = VietnameseChatStyleState


def choose_vietnamese_style(
    *,
    persona_id: str = "ban_than",
    distress_score: float = 0.0,
    risk_mode: str = "normal",
) -> VietnameseChatStyleState:
    normalized_risk = "sos" if risk_mode in {"sos", "safety"} else risk_mode
    user_tone_allows = persona_id in {"cun", "meo", "crush"}

    if normalized_risk == "sos" or distress_score >= 0.88:
        return VietnameseChatStyleState(
            sentence_initial_uppercase_required=False,
            lowercase_chat_allowed=True,
            preserve_proper_nouns=True,
            tone_level=0,
            pronoun_style="minh_ban",
            slang_level=0,
            humor_level=0,
            warmth_level=2,
            allow_playful=False,
            max_questions=1,
            max_sentences=3,
        )

    if distress_score >= 0.55:
        return VietnameseChatStyleState(
            tone_level=1,
            pronoun_style="minh_ban",
            slang_level=0,
            humor_level=0,
            warmth_level=2,
            allow_playful=False,
            max_questions=1,
            max_sentences=3,
        )

    allow_playful = user_tone_allows and distress_score < 0.4
    return VietnameseChatStyleState(
        tone_level=2,
        pronoun_style="minh_ban",
        slang_level=1,
        humor_level=1 if allow_playful else 0,
        warmth_level=2,
        allow_playful=allow_playful,
        max_questions=1,
        max_sentences=3,
    )
