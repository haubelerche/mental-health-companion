"""Deterministic persona routing for keep/switch/suggest/deactivate/reject decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from app.personas.aliases import is_known_persona, resolve_alias
from app.personas.gates import GateResult, check_safety_gate, check_unlock_gate
from app.personas.registry import DEFAULT_PERSONA_ID, PERSONA_REGISTRY

logger = logging.getLogger(__name__)

RouterAction = Literal["keep", "switch", "suggest", "deactivate", "reject"]

_BRIDGE_MESSAGES: dict[str, str] = {
    "dung_luong": "Dũng đây. Mình quay về nhịp chắc hơn một chút nha, cậu cứ nói phần đang nặng nhất trước.",
    "dat_le": "Tôi ở đây cùng bạn nhìn rõ điều đang làm hôm nay nặng hơn một chút.",
    "hau_luong": "Hú, Hậu đây. Tình hình thế nào rồi bạn?",
}


@dataclass
class PersonaRouterDecision:
    action: RouterAction
    previous_persona_id: str
    target_persona_id: str
    reason: str
    confidence: float = 1.0
    safety_override: bool = False
    blocked_reason: str | None = None
    bridge_message: str | None = None
    should_persist_preference: bool = False
    cooldown_until_turn: int | None = None
    requires_setup_fields: list[str] = field(default_factory=list)
    unlock_requirements: list[str] = field(default_factory=list)
    unlock_progress: dict[str, object] = field(default_factory=dict)


def route_persona(
    *,
    current_persona_id: str,
    requested_persona_id: str | None,
    distress: float,
    sos_triggered: bool,
    is_unlocked: bool = False,
    boundary_accepted: bool = False,
    dependency_signal: bool = False,
    user_explicit: bool = False,
) -> PersonaRouterDecision:
    """Gate order: validation -> unlock -> safety -> activation."""
    del boundary_accepted
    prev = resolve_alias(current_persona_id or DEFAULT_PERSONA_ID)
    requested = requested_persona_id

    if sos_triggered:
        action: RouterAction = "deactivate" if prev != DEFAULT_PERSONA_ID else "keep"
        return PersonaRouterDecision(
            action=action,
            previous_persona_id=prev,
            target_persona_id=DEFAULT_PERSONA_ID,
            reason="safety_crisis_bypass",
            safety_override=True,
            blocked_reason="safety_crisis_bypass",
        )

    current_safety = check_safety_gate(
        prev,
        distress=distress,
        sos_triggered=False,
        dependency_signal=dependency_signal,
    )
    if not current_safety.allowed:
        return PersonaRouterDecision(
            action="deactivate",
            previous_persona_id=prev,
            target_persona_id=DEFAULT_PERSONA_ID,
            reason=current_safety.blocked_reason or "safety_distress_override",
            safety_override=True,
            blocked_reason=current_safety.blocked_reason,
            bridge_message=_BRIDGE_MESSAGES.get(DEFAULT_PERSONA_ID),
        )

    if not requested or resolve_alias(requested) == prev:
        return PersonaRouterDecision(
            action="keep",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="default_keep",
        )

    resolved = resolve_alias(requested)
    if not is_known_persona(resolved):
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="unknown_persona_id",
            blocked_reason=f"unknown_persona_id: {requested}",
        )

    unlock_result: GateResult = check_unlock_gate(resolved, is_unlocked=is_unlocked)
    if not unlock_result.allowed:
        cfg = PERSONA_REGISTRY.get(resolved)
        requirements = [cfg.unlock_item_id] if cfg and cfg.unlock_item_id else []
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="persona_locked_by_progression",
            blocked_reason="persona_locked_by_progression",
            unlock_requirements=requirements,
        )

    safety_result: GateResult = check_safety_gate(
        resolved,
        distress=distress,
        sos_triggered=False,
        dependency_signal=dependency_signal,
    )
    if not safety_result.allowed:
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason=safety_result.blocked_reason or "safety_gate_blocked",
            safety_override=True,
            blocked_reason=safety_result.blocked_reason,
        )

    cfg = PERSONA_REGISTRY.get(resolved)
    if cfg and cfg.requires_setup:
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="setup_required",
            blocked_reason="setup_required",
            requires_setup_fields=list(cfg.requires_setup),
        )

    if user_explicit:
        action = "switch"
        reason = "user_explicit_switch"
        persist = True
    else:
        action = "suggest"
        reason = "contextual_suggestion"
        persist = False

    logger.info(
        "[PersonaRouter] %s -> %s (action=%s, reason=%s, distress=%.2f)",
        prev,
        resolved,
        action,
        reason,
        distress,
    )

    return PersonaRouterDecision(
        action=action,
        previous_persona_id=prev,
        target_persona_id=resolved,
        reason=reason,
        should_persist_preference=persist,
        bridge_message=_BRIDGE_MESSAGES.get(resolved) if action == "switch" else None,
    )
