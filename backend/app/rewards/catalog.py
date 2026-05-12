"""Reward store catalog - backend-driven item definitions."""

from __future__ import annotations

from typing import Any

CATALOG: list[dict[str, Any]] = [
    {
        "item_id": "persona_dung_luong",
        "item_type": "persona",
        "title": "Dung Luong (Đang túc trực)",
        "subtitle": "Sinh viên năm tám",
        "description": (
            "Tên: Dung Luong\n"
            "Nghề nghiệp: Sinh viên sắp ra trường\n"
            "Tính cách: Vui vẻ, hay gửi meme đúng ngữ cảnh, sống tích cực, biết lắng nghe\n"
            "Chuyện đời: Deadline lắm quá huhuhu... thôi kệ nó, đi mua trà sữa đã"
        ),
        "price_hearts": 100,
        "tier": 1,
        "icon_key": "persona_dung_luong",
        "requirements": {},
        "metadata": {"unlocks_persona_id": "dung_luong", "core_persona": True},
    },
    {
        "item_id": "persona_dat_le",
        "item_type": "persona",
        "title": "Dat Le (Đang túc trực)",
        "subtitle": "Intern Mắt Thâm",
        "description": (
            "Tên: Dat Le\n"
            "Nghề nghiệp: Intern lương ba cọc, không đồng\n"
            "Tính cách: Trầm ngâm, suy ngẫm triết lý cuộc đời, hay động viên, truyền cảm hứng\n"
            "Chuyện đời: Lương 3 triệu thì trời mưa có nên lội tới công ty không ?"
        ),
        "price_hearts": 100,
        "tier": 1,
        "icon_key": "persona_dat_le",
        "requirements": {},
        "metadata": {"unlocks_persona_id": "dat_le", "core_persona": True},
    },
    {
        "item_id": "persona_hau_luong",
        "item_type": "persona",
        "title": "Nhân viên Cú vọ",
        "subtitle": "Hau Luong (Bị nhốt ở công ty)",
        "description": (
            "Tên: Hau Luong\n"
            "Nghề nghiệp: Nhân viên văn phòng\n"
            "Tính cách: Hướng nội hay gửi voice message vì lười nhắn, do vô tư nên chữa được lo âu và overthinking\n"
            "Chuyện đời: Đau lưng, mỏi gối tê tay, Hau và máy tính sống bên nhau trọn đời về sau, hạnh phúc không? Không biết..."
        ),
        "price_hearts": 500,
        "tier": 1,
        "icon_key": "persona_hau_luong",
        "requirements": {},
        "metadata": {"unlocks_persona_id": "hau_luong"},
    },
    {
        "item_id": "persona_cun",
        "item_type": "legacy_persona",
        "title": "Cun",
        "subtitle": "Legacy friendly persona alias",
        "description": "Compatibility store item for legacy purchases; unlocks the default warm friend style.",
        "price_hearts": 100,
        "tier": 1,
        "icon_key": "persona_dung_luong",
        "requirements": {},
        "metadata": {"unlocks_persona_id": "dung_luong", "legacy_alias": True},
    },
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
    {
        "item_id": "style_shorter_replies",
        "item_type": "micro_style",
        "title": "Nói ngắn hơn",
        "subtitle": "Trả lời súc tích hơn",
        "price_hearts": 500,
        "tier": 1,
        "icon_key": "style_short",
        "requirements": {},
        "metadata": {"applies_to": ["dung_luong", "dat_le", "hau_luong"]},
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
        "metadata": {"applies_to": ["dung_luong", "hau_luong"]},
    },
]

CATALOG_BY_ID: dict[str, dict[str, Any]] = {item["item_id"]: item for item in CATALOG}


def get_catalog_item(item_id: str) -> dict[str, Any] | None:
    return CATALOG_BY_ID.get(item_id)


def validate_catalog_item(item: dict[str, Any]) -> None:
    price = item.get("price_hearts", 0)
    if not (100 <= price <= 10000):
        raise ValueError(f"item {item['item_id']}: price_hearts {price} outside [100, 10000]")
    if not item.get("item_id"):
        raise ValueError("item missing item_id")
    if not item.get("title"):
        raise ValueError(f"item {item['item_id']}: missing title")


def validate_full_catalog() -> None:
    for item in CATALOG:
        validate_catalog_item(item)
