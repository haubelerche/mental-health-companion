"""Reward store catalog — backend-driven item definitions.

Each item has a stable item_id slug. The catalog is seeded into reward_store_items
on first startup or via migration. PRD §11.
"""

from __future__ import annotations

from typing import Any

# Catalog items: (item_id, item_type, title, subtitle, price_hearts, tier, icon_key, requirements)
CATALOG: list[dict[str, Any]] = [
    # ── Persona shelf ─────────────────────────────────────────────────────────
    {
        "item_id": "persona_cun",
        "item_type": "persona",
        "title": "Cún",
        "subtitle": "Đồng hành vui vẻ, nâng mood mỗi ngày",
        "description": "Cún là chế độ giao tiếp năng động, vui vẻ. Phù hợp khi bạn cần một chút nhẹ nhàng.",
        "price_hearts": 500,
        "tier": 1,
        "icon_key": "persona_cun",
        "requirements": {"mood_checkins_min": 3},
        "metadata": {"unlocks_persona_id": "cun"},
    },
    {
        "item_id": "persona_meo",
        "item_type": "persona",
        "title": "Mèo",
        "subtitle": "Đồng hành yên lặng, lắng nghe sâu",
        "description": "Mèo là chế độ giao tiếp nhẹ nhàng, ít lời, phù hợp khi bạn cần không gian yên tĩnh.",
        "price_hearts": 1200,
        "tier": 2,
        "icon_key": "persona_meo",
        "requirements": {"mood_checkins_min": 5, "reflections_completed_min": 2},
        "metadata": {"unlocks_persona_id": "meo"},
    },
    {
        "item_id": "persona_crush",
        "item_type": "persona",
        "title": "Crush",
        "subtitle": "Ấm áp hơn một chút, vẫn giữ ranh giới an toàn",
        "description": (
            "Crush là chế độ ấm áp hơn — không phải người yêu thật, không có cam kết, "
            "không tình dục hoá. App có thể tạm đổi về Bạn Tốt khi cần thiết."
        ),
        "price_hearts": 5000,
        "tier": 3,
        "icon_key": "persona_crush",
        "requirements": {
            "mood_checkins_min": 14,
            "boundary_intro_accepted": True,
            "no_recent_dependency_signal": True,
        },
        "metadata": {"unlocks_persona_id": "crush", "safety_restricted": True},
    },
    # ── Knowledge shelf ────────────────────────────────────────────────────────
    {
        "item_id": "knowledge_overthinking_101",
        "item_type": "knowledge",
        "title": "Overthinking 101",
        "subtitle": "Vì sao não cứ lặp lại lo nghĩ",
        "price_hearts": 100,
        "tier": 1,
        "icon_key": "knowledge_brain",
        "requirements": {},
        "metadata": {},
    },
    {
        "item_id": "knowledge_anxiety_loop",
        "item_type": "knowledge",
        "title": "Anxiety Loop",
        "subtitle": "Vòng lặp lo âu và né tránh",
        "price_hearts": 200,
        "tier": 1,
        "icon_key": "knowledge_loop",
        "requirements": {},
        "metadata": {},
    },
    {
        "item_id": "knowledge_sleep_reset",
        "item_type": "knowledge",
        "title": "Sleep Reset Kit",
        "subtitle": "Chuẩn bị ngủ khi đầu không tắt",
        "price_hearts": 400,
        "tier": 2,
        "icon_key": "knowledge_sleep",
        "requirements": {},
        "metadata": {},
    },
    # ── Mood Room shelf ────────────────────────────────────────────────────────
    {
        "item_id": "moodroom_sticker_cloud",
        "item_type": "mood_room",
        "title": "Sticker: Mây nhỏ",
        "subtitle": "First check-in reward",
        "price_hearts": 100,
        "tier": 1,
        "icon_key": "sticker_cloud",
        "requirements": {},
        "metadata": {},
    },
    {
        "item_id": "moodroom_cacao_cup",
        "item_type": "mood_room",
        "title": "Cốc cacao",
        "subtitle": "Cozy return ritual",
        "price_hearts": 200,
        "tier": 1,
        "icon_key": "moodroom_cacao",
        "requirements": {},
        "metadata": {},
    },
    {
        "item_id": "moodroom_theme_rainy",
        "item_type": "mood_room",
        "title": "Rainy Window Theme",
        "subtitle": "Calm room world",
        "price_hearts": 2000,
        "tier": 3,
        "icon_key": "theme_rainy",
        "requirements": {},
        "metadata": {},
    },
    # ── Micro-style shelf ─────────────────────────────────────────────────────
    {
        "item_id": "style_shorter_replies",
        "item_type": "micro_style",
        "title": "Nói ngắn hơn",
        "subtitle": "Trả lời súc tích hơn",
        "price_hearts": 500,
        "tier": 1,
        "icon_key": "style_short",
        "requirements": {},
        "metadata": {"applies_to": ["ban_than", "nguoi_thay", "cun", "meo", "crush"]},
    },
    {
        "item_id": "style_warmer",
        "item_type": "micro_style",
        "title": "Ấm hơn chút",
        "subtitle": "Ấm áp hơn, không phụ thuộc",
        "price_hearts": 600,
        "tier": 1,
        "icon_key": "style_warm",
        "requirements": {},
        "metadata": {"applies_to": ["ban_than", "crush"]},
    },
]

CATALOG_BY_ID: dict[str, dict[str, Any]] = {item["item_id"]: item for item in CATALOG}


def get_catalog_item(item_id: str) -> dict[str, Any] | None:
    return CATALOG_BY_ID.get(item_id)


def validate_catalog_item(item: dict[str, Any]) -> None:
    """Raise ValueError if item violates catalog constraints."""
    price = item.get("price_hearts", 0)
    if not (100 <= price <= 10000):
        raise ValueError(f"item {item['item_id']}: price_hearts {price} outside [100, 10000]")
    if not item.get("item_id"):
        raise ValueError("item missing item_id")
    if not item.get("title"):
        raise ValueError(f"item {item['item_id']}: missing title")
    crush_items = ("persona_crush", "style_soft_but_boundaried")
    forbidden_crush_copy = ("người yêu AI", "bạn trai", "bạn gái", "tình yêu thật")
    if item.get("item_id") in crush_items:
        for phrase in forbidden_crush_copy:
            if phrase in (item.get("description") or "") or phrase in (item.get("subtitle") or ""):
                raise ValueError(f"item {item['item_id']}: forbidden crush copy found: {phrase!r}")


def validate_full_catalog() -> None:
    for item in CATALOG:
        validate_catalog_item(item)
