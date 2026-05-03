"""Persona unlock helpers for persona package code.

Canonical implementation lives in ``app.services.persona_unlock_persistence`` so
rewards and personas share one module without import cycles.
"""

from __future__ import annotations

from app.services.persona_unlock_persistence import (
    UNLOCKABLE_PERSONAS,
    accept_crush_boundary,
    get_persona_unlock_state,
    is_persona_unlocked,
    mark_persona_unlocked,
)

__all__ = (
    "UNLOCKABLE_PERSONAS",
    "accept_crush_boundary",
    "get_persona_unlock_state",
    "is_persona_unlocked",
    "mark_persona_unlocked",
)
