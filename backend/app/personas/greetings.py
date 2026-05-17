"""Opening lines returned by GET /chat/greeting."""

from __future__ import annotations

from app.personas.aliases import resolve_alias
from app.personas.registry import DEFAULT_PERSONA_ID, PERSONA_REGISTRY

PERSONA_CHAT_GREETINGS: dict[str, str] = {
    "dung_luong": (
        "Ê, tớ là Dũng đây — nay cậu ổn không? Xong deadline chưa hay bỏ đó đi chơi rồi?"
    ),
    "dat_le": (
        "Chào bạn, tôi là Đạt. Hôm nay bạn thấy thế nào — mọi thứ vẫn ổn chứ?"
    ),
    "hau_luong": (
        "Hú hú, Hậu đây. Tình hình thế nào rồi bro? Có gì muốn kể hong?"
    ),
}


def persona_chat_greeting_text(persona_id: str) -> str:
    pid = resolve_alias((persona_id or "").strip() or DEFAULT_PERSONA_ID)
    fallback = PERSONA_CHAT_GREETINGS[DEFAULT_PERSONA_ID]
    return PERSONA_CHAT_GREETINGS.get(pid, fallback)


def validate_greeting_registry_coverage() -> None:
    keys = set(PERSONA_CHAT_GREETINGS.keys())
    expected = set(PERSONA_REGISTRY.keys())
    assert keys == expected, f"greeting keys {keys} != registry {expected}"


validate_greeting_registry_coverage()
