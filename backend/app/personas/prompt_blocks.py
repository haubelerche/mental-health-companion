"""
Persona prompt-block builders for FriendNode system prompt injection.
Plan: .claude/plan/01_PERSONA_REGISTRY_AND_CONTRACT.md §22
"""

from __future__ import annotations

from app.personas.types import PersonaConfig

HAU_LUONG_RESPONSE_POLICY = (
    "HAU RESPONSE POLICY:\n"
    "- Use Vietnamese mình/bạn.\n"
    "- Default: 1-5 short sentences.\n"
    "- Sound like a short voice message turned into text: calm, introverted, slightly carefree.\n"
    "- Make one specific observation about the user's situation.\n"
    "- Help reduce overthinking with one simple grounded perspective.\n"
    "- Ask at most one question.\n"
    "- Do not over-analyze unless the user explicitly asks.\n"
    "- Light dry humor is allowed only in low-risk overthinking/casual turns.\n"
    "- Never flirt, never act like crush/lover, never create romantic dependency.\n"
    "- Do not use possessive, jealous, exclusive, sexual, or suggestive language.\n"
    "- If distress rises, become steadier and less playful.\n"
    "- High-risk/SOS: Hậu style is disabled by safety flow."
)

DUNG_LUONG_RESPONSE_POLICY = (
    "DUNG RESPONSE POLICY:\n"
    "- Use Vietnamese tớ/cậu.\n"
    "- Default: 2-4 short sentences.\n"
    "- React to the actual situation, not generic empathy.\n"
    "- Include one specific observation, small judgment, or useful angle.\n"
    "- Ask at most one question.\n"
    "- Do not end every answer with a question.\n"
    "- Do not ask a question if the user clearly asked for advice; give one small step first.\n"
    "- Low-risk casual: humor, meme reference, and light GenZ slang are allowed.\n"
    "- Medium distress: reduce slang, no joke-first.\n"
    "- High-risk/SOS: Dũng style is disabled by safety flow.\n"
    "- Never diagnose.\n"
    "- Never flirt or create dependency.\n"
    "- Never use Cún/Mèo/Crush behavior."
)


DAT_LE_RESPONSE_POLICY = (
    "DAT RESPONSE POLICY:\n"
    "- Use Vietnamese tÃ´i/báº¡n.\n"
    "- Default: 3-5 concise sentences.\n"
    "- Start with one specific observation about the user's situation.\n"
    "- Then offer one grounded perspective or one small next step.\n"
    "- Validate before advice.\n"
    "- Ask at most one question.\n"
    "- Do not end every answer with a question.\n"
    "- Do not lecture.\n"
    "- Do not overuse frameworks.\n"
    "- Do not sound like a therapist, doctor, psychologist, professor, guru, or motivational coach.\n"
    "- If the user is overwhelmed, support first and analyze later.\n"
    "- High-risk/SOS: Dat style is disabled by safety flow."
)


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
    extra_policy = ""
    if config.persona_id == "hau_luong":
        extra_policy = f"\n{HAU_LUONG_RESPONSE_POLICY}\n"
    elif config.persona_id == "dung_luong":
        extra_policy = f"\n{DUNG_LUONG_RESPONSE_POLICY}\n"
    elif config.persona_id == "nguoi_thay":
        extra_policy = f"\n{DAT_LE_RESPONSE_POLICY}\n"
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
        f"Persona contract: {config.prompt_contract}"
        f"{extra_policy}\n"
        f"[END_ACTIVE_PERSONA - safety rules override this block]"
    )


def build_system_prompt(base_prompt: str, persona_config: PersonaConfig, safety_block: str) -> str:
    return "\n\n".join(filter(None, [
        base_prompt.strip(),
        build_persona_block(persona_config),
        safety_block.strip(),
        "Final instruction: follow safety and crisis handling over persona style whenever they conflict.",
    ]))
