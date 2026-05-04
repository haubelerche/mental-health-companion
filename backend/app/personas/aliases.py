"""
Legacy alias resolution — maps removed or alternate persona names to canonical IDs.
Plan: .claude/plan/01_PERSONA_REGISTRY_AND_CONTRACT.md §5 (alias handling)
"""

from __future__ import annotations

LEGACY_ALIAS_MAP: dict[str, str] = {
    # English variants
    "friend": "ban_than",
    "best_friend": "ban_than",
    "default": "ban_than",
    "serene_default": "ban_than",
    "mentor": "nguoi_thay",
    "teacher": "nguoi_thay",
    "coach": "nguoi_thay",
    "dog": "cun",
    "puppy": "cun",
    "cat": "meo",
    "kitty": "meo",
    # Vietnamese informal variants
    "may": "ban_than",
    "ban": "ban_than",
    "thay": "nguoi_thay",
    "con_cun": "cun",
    "con_meo": "meo",
    "nguoi_yeu": "crush",
}

_CANONICAL_IDS = frozenset({"ban_than", "nguoi_thay", "cun", "meo", "crush"})


def resolve_alias(persona_id: str) -> str:
    """Return canonical persona_id, resolving legacy aliases. Returns input unchanged if already canonical or unknown."""
    if not persona_id:
        return "ban_than"
    lower = persona_id.strip().lower()
    if lower in _CANONICAL_IDS:
        return lower
    return LEGACY_ALIAS_MAP.get(lower, lower)


def is_known_persona(persona_id: str) -> bool:
    return resolve_alias(persona_id) in _CANONICAL_IDS


# Alias expected by langgraph_chat.py
normalize_persona_id = resolve_alias
