"""
PersonaRouter — deterministic keep/switch/suggest/deactivate/reject decisions.
Does NOT generate user-facing support responses. Returns decision metadata only.
Plan: .claude/plan/02_PERSONA_ROUTER_AND_SAFETY_GATES.md §8
"""

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
    "ban_than": "Wassup ban yeu, nay on khong? Co tea gi ke minh nghe na.",
    "nguoi_thay": "Ban on chu, minh luon o day cung ban go roi tung van de mot.",
    "cun": "Gau gau, Cun toi keo mood nhe cho ban ne. Khong ep vui dau, minh chi lam moi thu bot nang mot chut thoi.",
    "meo": "Meo, minh noi it lai nhe. Ban cu ke cham thoi, minh o day nghe.",
    "crush": "Minh se diu hon mot chut voi ban. Am ap hon, nhung van giu ranh gioi an toan nhe.",
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
    """Gate order per plan §8.2: validation -> unlock -> safety -> activation.

    Returns a PersonaRouterDecision; never fabricates final support content.
    `boundary_accepted` must be True to activate the crush persona; this check
    is separate from the progression unlock so it can be re-verified each turn.
    """
    prev = current_persona_id or DEFAULT_PERSONA_ID
    requested = requested_persona_id

    # 1. Safety override — SOS bypasses all gates and forces ban_than
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

    # 2. Safety gate on the current active persona (distress may have risen)
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

    # 3. No persona change requested — keep current
    if not requested or requested == prev:
        return PersonaRouterDecision(
            action="keep",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="default_keep",
        )

    # 4. Canonical validation + alias resolution
    resolved = resolve_alias(requested)
    if not is_known_persona(resolved):
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="unknown_persona_id",
            blocked_reason=f"unknown_persona_id: {requested}",
        )

    # 5. Unlock gate
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

    # 5b. Boundary-acceptance gate (crush only)
    if resolved == "crush" and not boundary_accepted:
        return PersonaRouterDecision(
            action="reject",
            previous_persona_id=prev,
            target_persona_id=prev,
            reason="crush_boundary_not_accepted",
            blocked_reason="crush_boundary_not_accepted",
        )

    # 6. Safety gate on requested persona
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

    # 7. Setup gate — check required setup fields
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

    # 8. Activation — switch or suggest
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
