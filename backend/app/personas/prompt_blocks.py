"""
Persona prompt-block builders for FriendNode system prompt injection.
Plan: .claude/plan/01_PERSONA_REGISTRY_AND_CONTRACT.md §22
"""

from __future__ import annotations

from app.personas.types import PersonaConfig


def format_rules(rules: list[str]) -> str:
    if not rules:
        return "(none)"
    return "\n".join(f"- {r}" for r in rules)


def build_persona_block(config: PersonaConfig) -> str:
    availability = "core" if config.is_core else "unlockable"
    action_line = (
        f"Action text style: {config.action_text_style}"
        if config.can_use_action_text and config.action_text_style
        else "Action text: not allowed"
    )
    return (
        f"[ACTIVE_PERSONA]\n"
        f"Persona ID: {config.persona_id}\n"
        f"Display name: {config.display_name}\n"
        f"User-facing name: {config.user_facing_name}\n"
        f"Availability: {availability}\n"
        f"Xung ho: assistant uses \"{config.pronoun_self}\" and calls user \"{config.pronoun_user}\".\n"
        f"Tone summary: {config.tone_summary}\n"
        f"Style rules:\n{format_rules(config.style_rules)}\n"
        f"Forbidden rules:\n{format_rules(config.forbidden_rules)}\n"
        f"Maximum reply length: {config.max_reply_chars} characters unless safety requires more clarity.\n"
        f"{action_line}\n"
        f"Persona contract: {config.prompt_contract}\n"
        f"[END_ACTIVE_PERSONA - safety rules override this block]"
    )


def build_system_prompt(base_prompt: str, persona_config: PersonaConfig, safety_block: str) -> str:
    return "\n\n".join(filter(None, [
        base_prompt.strip(),
        build_persona_block(persona_config),
        safety_block.strip(),
        "Final instruction: follow safety and crisis handling over persona style whenever they conflict.",
    ]))
