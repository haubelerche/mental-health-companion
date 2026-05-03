"""
Persona subsystem — style modes inside FriendNode, not separate agents.
PRD §3/§4: personas are communication modes, not autonomous agents.
"""

from app.personas.aliases import is_known_persona, normalize_persona_id, resolve_alias
from app.personas.gates import GateResult, check_safety_gate, check_unlock_gate
from app.personas.prompt_blocks import build_persona_block, build_system_prompt
from app.personas.registry import (
    DEFAULT_PERSONA_ID,
    PERSONA_REGISTRY,
    get_default_persona,
    get_persona,
    get_persona_config,
    validate_persona_registry,
)
from app.personas.router import PersonaRouterDecision, route_persona
from app.personas.types import PersonaConfig, PersonaState

__all__ = [
    "DEFAULT_PERSONA_ID",
    "GateResult",
    "PERSONA_REGISTRY",
    "PersonaConfig",
    "PersonaRouterDecision",
    "PersonaState",
    "build_persona_block",
    "build_system_prompt",
    "check_safety_gate",
    "check_unlock_gate",
    "get_default_persona",
    "get_persona",
    "get_persona_config",
    "is_known_persona",
    "normalize_persona_id",
    "resolve_alias",
    "route_persona",
    "validate_persona_registry",
]
