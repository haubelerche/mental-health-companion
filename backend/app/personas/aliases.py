"""Persona alias resolution for the current Dung/Dat/Hau model.

Hau is a quiet, low-pressure unlockable persona, not a romantic persona.
Inputs that imply a romantic framing (``crush``, ``persona_crush``,
``nguoi_yeu``, ``lover``) must not resolve to any canonical persona.
"""

from __future__ import annotations

LEGACY_ALIAS_MAP: dict[str, str] = {
    "dung": "dung_luong",
    "d\u0169ng": "dung_luong",
    "dung luong": "dung_luong",
    "d\u0169ng l\u01b0\u01a1ng": "dung_luong",
    "dung_luong": "dung_luong",
    "ban_than": "dung_luong",
    "ban_tot": "dung_luong",
    "serene_default": "dung_luong",
    "friend": "dung_luong",
    "best_friend": "dung_luong",
    "default": "dung_luong",
    "dat_le": "dat_le",
    "dat": "dat_le",
    "\u0111\u1ea1t": "dat_le",
    "dat le": "dat_le",
    "\u0111\u1ea1t l\u00ea": "dat_le",
    "nguoi_thay": "dat_le",
    "mentor": "dat_le",
    "hau": "hau_luong",
    "h\u1eadu": "hau_luong",
    "háº­u": "hau_luong",
    "hau luong": "hau_luong",
    "hau_luong": "hau_luong",
}

_CANONICAL_IDS = frozenset({"dung_luong", "dat_le", "hau_luong"})

ROMANTIC_FRAMING_ALIASES: frozenset[str] = frozenset(
    {"crush", "persona_crush", "nguoi_yeu", "lover"}
)
REJECTED_ROMANTIC_PERSONA = "__rejected_romantic_persona__"


def resolve_alias(persona_id: str) -> str:
    if not persona_id:
        return "dung_luong"
    lower = persona_id.strip().lower()
    if lower in ROMANTIC_FRAMING_ALIASES:
        return REJECTED_ROMANTIC_PERSONA
    if lower in _CANONICAL_IDS:
        return lower
    return LEGACY_ALIAS_MAP.get(lower, lower)


def is_known_persona(persona_id: str) -> bool:
    return resolve_alias(persona_id) in _CANONICAL_IDS


normalize_persona_id = resolve_alias
