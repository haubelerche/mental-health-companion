"""
Persona unlock and safety gates — deterministic, no LLM, no I/O.
Plan: .claude/plan/02_PERSONA_ROUTER_AND_SAFETY_GATES.md §8.3-8.4
Safety priority: PRD §11. Safety rules override ALL persona gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateResult:
    allowed: bool
    blocked_reason: str | None = None
    requirements: list[str] = field(default_factory=list)
    progress: dict[str, object] = field(default_factory=dict)


_CORE_PERSONAS = frozenset({"dung_luong", "nguoi_thay"})


def check_unlock_gate(persona_id: str, *, is_unlocked: bool) -> GateResult:
    """Return allowed=True for core personas; for unlockable personas require is_unlocked=True."""
    if persona_id in _CORE_PERSONAS:
        return GateResult(allowed=True)
    if is_unlocked:
        return GateResult(allowed=True)
    return GateResult(
        allowed=False,
        blocked_reason="persona_locked_by_progression",
    )


def check_safety_gate(
    persona_id: str,
    *,
    distress: float,
    sos_triggered: bool,
    dependency_signal: bool = False,
) -> GateResult:
    """Deterministic safety gate — runs before any prompt rendering.

    SOS always bypasses persona style (safety overrides everything, PRD §11).
    Each unlockable persona has a distress ceiling; crossing it forces fallback to dung_luong.
    """
    if sos_triggered:
        return GateResult(allowed=False, blocked_reason="safety_crisis_bypass")

    if persona_id == "nguoi_thay" and distress >= 0.70:
        return GateResult(allowed=False, blocked_reason="safety_distress_override")

    if persona_id == "hau_luong":
        if distress >= 0.60:
            return GateResult(allowed=False, blocked_reason="hau_luong_distress_override")
        if dependency_signal:
            return GateResult(allowed=False, blocked_reason="dependency_boundary")

    return GateResult(allowed=True)
