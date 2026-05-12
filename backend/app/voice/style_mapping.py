"""Persona to TTS voice style mapping."""

from __future__ import annotations

PERSONA_VOICE_STYLES: dict[str, str] = {
    "dung_luong": "warm_friend",
    "dat_le": "calm_mentor",
    "hau_luong": "soft_quiet",
}

DEFAULT_VOICE_STYLE = "warm_friend"

RESTRICTED_VOICE_STYLES: frozenset[str] = frozenset({
    "soft_quiet",
})


def get_voice_style(persona_id: str | None) -> str:
    """Return tts_style_id for a persona_id. Falls back to DEFAULT_VOICE_STYLE."""
    if not persona_id:
        return DEFAULT_VOICE_STYLE
    return PERSONA_VOICE_STYLES.get(persona_id, DEFAULT_VOICE_STYLE)


def is_style_restricted(style_id: str) -> bool:
    """True if this voice style requires ownership + consent before rendering."""
    return style_id in RESTRICTED_VOICE_STYLES


def resolve_active_style(
    persona_id: str | None,
    *,
    user_owns_voice_style: bool = False,
) -> str:
    """Resolve the effective voice style for a response."""
    style = get_voice_style(persona_id)
    if is_style_restricted(style) and not user_owns_voice_style:
        return DEFAULT_VOICE_STYLE
    return style
