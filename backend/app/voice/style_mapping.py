"""Persona → TTS voice style mapping — Plan 08 §14.2.

Rules:
- Safety always overrides persona style (voice-tts.md hard rules).
- Crush voice must be non-seductive ("soft_affectionate").
- Default style is used when persona_id is unknown or None.
- Voice style is NOT rendered for locked voice styles without ownership + consent.
"""

from __future__ import annotations

# Canonical persona_id → tts_style_id mapping (plan 08 §14.2 table).
PERSONA_VOICE_STYLES: dict[str, str] = {
    "ban_than": "warm_friend",
    "nguoi_thay": "calm_mentor",
    "cun": "bright_playful",
    "meo": "quiet_calm",
    "crush": "soft_affectionate",
}

DEFAULT_VOICE_STYLE = "warm_friend"

# Styles that require explicit user ownership + consent before rendering.
# Attempting to render these without ownership silently falls back to default.
RESTRICTED_VOICE_STYLES: frozenset[str] = frozenset({
    "soft_affectionate",  # Crush — highest safety risk
    "bright_playful",     # Cún — requires unlock
    "quiet_calm",         # Mèo — requires unlock
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
    """Resolve the effective voice style for a response.

    Falls back to DEFAULT_VOICE_STYLE when the mapped style is restricted and
    the user does not own it. This ensures text-path safety without crashing.
    """
    style = get_voice_style(persona_id)
    if is_style_restricted(style) and not user_owns_voice_style:
        return DEFAULT_VOICE_STYLE
    return style
