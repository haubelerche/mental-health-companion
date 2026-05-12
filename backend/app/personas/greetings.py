"""Opening lines returned by GET /chat/greeting."""

from __future__ import annotations

from app.personas.aliases import resolve_alias
from app.personas.registry import DEFAULT_PERSONA_ID, PERSONA_REGISTRY

PERSONA_CHAT_GREETINGS: dict[str, str] = {
    "dung_luong": (
        "Ê, Dũng đây, tớ nghe nè. Hôm nay cậu đang chill, hơi đuối, hay kiểu deadline dí sát gáy rồi?"
    ),
    "nguoi_thay": (
        "Chào bạn. Tôi ở đây cùng bạn nhìn rõ điều đang làm hôm nay nặng hơn một chút."
    ),
    "hau_luong": (
        "Hú, Hậu đây. Tình hình thế nào rồi bạn?"
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
