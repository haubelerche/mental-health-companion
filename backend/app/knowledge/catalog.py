"""Knowledge pack catalog — seeded psychoeducation content.

3 packs, 3–5 cards each. Content is psychoeducation only (plan 07 §12.4):
- no diagnosis framing;
- no disorder probability claims;
- includes gentle escalation guidance;
- not a replacement for professional support.

Each pack has price_hearts=None (free) or a price and optional required_item_id.
Free packs are available to all users; priced packs require inventory ownership.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Packs  (pack_id, title, description, category, price_hearts, required_item_id)
# ---------------------------------------------------------------------------

KNOWLEDGE_PACKS: list[dict[str, Any]] = [
    {
        "pack_id": "kp_stress_basics",
        "title": "Hiểu về Căng thẳng",
        "description": "Tìm hiểu cách cơ thể và tâm trí phản ứng với áp lực — và những bước nhỏ để cân bằng lại.",
        "category": "stress",
        "price_hearts": None,  # free
        "required_item_id": None,
        "is_active": True,
    },
    {
        "pack_id": "kp_sleep_mood",
        "title": "Giấc Ngủ và Tâm Trạng",
        "description": "Khám phá mối liên hệ giữa giấc ngủ và cảm xúc, và những thói quen nhỏ có thể hỗ trợ cả hai.",
        "category": "sleep",
        "price_hearts": 300,
        "required_item_id": None,
        "is_active": True,
    },
    {
        "pack_id": "kp_social_energy",
        "title": "Năng Lượng Xã Hội",
        "description": "Hiểu vì sao tương tác xã hội đôi khi làm bạn kiệt sức — và cách nạp lại năng lượng theo cách của mình.",
        "category": "social",
        "price_hearts": 500,
        "required_item_id": None,
        "is_active": True,
    },
]

# ---------------------------------------------------------------------------
# Cards  (card_id, pack_id, title, content_markdown, order_index,
#          estimated_read_seconds, reflection_prompt)
# ---------------------------------------------------------------------------

KNOWLEDGE_CARDS: list[dict[str, Any]] = [
    # ── kp_stress_basics ──────────────────────────────────────────────────
    {
        "card_id": "kc_stress_what",
        "pack_id": "kp_stress_basics",
        "title": "Căng thẳng là gì?",
        "content_markdown": (
            "Căng thẳng là phản ứng tự nhiên của cơ thể khi đối mặt với thay đổi hoặc áp lực. "
            "Khi bạn cảm thấy bị đẩy vượt quá giới hạn, hệ thần kinh kích hoạt phản ứng 'fight-or-flight' "
            "— nhịp tim tăng, cơ căng, suy nghĩ nhanh hơn.\n\n"
            "Điều này không có nghĩa là có gì sai với bạn. Đây là cơ chế bảo vệ đã tồn tại hàng ngàn năm. "
            "Vấn đề xảy ra khi trạng thái này kéo dài mà không được nghỉ ngơi.\n\n"
            "_Lưu ý: Nếu bạn cảm thấy kiệt sức kéo dài hoặc khó kiểm soát, hãy trao đổi với "
            "chuyên gia sức khỏe tâm thần._"
        ),
        "order_index": 1,
        "estimated_read_seconds": 60,
        "reflection_prompt": "Gần đây điều gì khiến bạn cảm thấy áp lực nhất?",
    },
    {
        "card_id": "kc_stress_signals",
        "pack_id": "kp_stress_basics",
        "title": "Nhận ra dấu hiệu cơ thể",
        "content_markdown": (
            "Cơ thể thường báo hiệu căng thẳng trước khi tâm trí nhận ra. Một số dấu hiệu phổ biến:\n\n"
            "- Vai và cổ căng cứng\n"
            "- Đau đầu nhẹ hoặc nặng mí mắt\n"
            "- Khó ngủ hoặc ngủ nhiều hơn bình thường\n"
            "- Cảm giác bồn chồn, khó tập trung\n"
            "- Ăn nhiều hoặc ít hơn bình thường\n\n"
            "Nhận ra những dấu hiệu này sớm giúp bạn phản ứng trước khi căng thẳng leo thang. "
            "Đây là kỹ năng tự quan sát, không phải chẩn đoán.\n\n"
            "_Nếu các triệu chứng này kéo dài hoặc ảnh hưởng nghiêm trọng đến sinh hoạt, "
            "hãy tham khảo ý kiến chuyên gia._"
        ),
        "order_index": 2,
        "estimated_read_seconds": 75,
        "reflection_prompt": "Cơ thể bạn thường phản ứng với căng thẳng theo cách nào?",
    },
    {
        "card_id": "kc_stress_micro",
        "pack_id": "kp_stress_basics",
        "title": "Micro-break hiệu quả",
        "content_markdown": (
            "Nghiên cứu về phục hồi nhận thức cho thấy những khoảng nghỉ ngắn (5–10 phút) "
            "có thể giúp hệ thần kinh 'reset' hiệu quả hơn cố gắng tiếp tục khi đã mệt.\n\n"
            "Một số micro-break đơn giản:\n\n"
            "- Đứng dậy, duỗi người, đi lấy nước\n"
            "- Nhìn ra cửa sổ hoặc một điểm xa trong 2 phút\n"
            "- Hít 4 nhịp — giữ 4 nhịp — thở ra 6 nhịp\n"
            "- Nghe một bài nhạc yêu thích\n\n"
            "Không cần làm gì hoành tráng. Sự nhất quán quan trọng hơn cường độ."
        ),
        "order_index": 3,
        "estimated_read_seconds": 55,
        "reflection_prompt": "Bạn có thể thử micro-break nào ngay hôm nay?",
    },

    # ── kp_sleep_mood ─────────────────────────────────────────────────────
    {
        "card_id": "kc_sleep_link",
        "pack_id": "kp_sleep_mood",
        "title": "Giấc ngủ ảnh hưởng đến cảm xúc thế nào?",
        "content_markdown": (
            "Khi ngủ không đủ giấc, não xử lý cảm xúc tiêu cực mạnh hơn và "
            "giảm khả năng điều tiết phản ứng. Đây là lý do vì sao mọi thứ "
            "thường trông tệ hơn khi bạn mệt.\n\n"
            "Mối liên hệ này là hai chiều: tâm trạng xấu cũng làm khó ngủ, "
            "tạo ra vòng lặp khó thoát.\n\n"
            "Điều tốt là chu kỳ này có thể dần cải thiện từ những thay đổi nhỏ.\n\n"
            "_Nếu khó ngủ kéo dài nhiều tuần, hãy trao đổi với bác sĩ để loại trừ "
            "nguyên nhân khác._"
        ),
        "order_index": 1,
        "estimated_read_seconds": 65,
        "reflection_prompt": "Bạn ngủ trung bình bao nhiêu tiếng mỗi đêm tuần này?",
    },
    {
        "card_id": "kc_sleep_hygiene",
        "pack_id": "kp_sleep_mood",
        "title": "Thói quen nhỏ trước khi ngủ",
        "content_markdown": (
            "Môi trường và thói quen trước khi ngủ ảnh hưởng lớn đến chất lượng giấc ngủ.\n\n"
            "Một số gợi ý dựa trên nghiên cứu về giấc ngủ:\n\n"
            "- Giảm ánh sáng xanh từ màn hình 30–60 phút trước khi ngủ\n"
            "- Giữ nhiệt độ phòng mát (khoảng 18–22°C nếu có thể)\n"
            "- Ngủ và thức dậy cùng giờ mỗi ngày — kể cả cuối tuần\n"
            "- Tránh caffeine sau 2–3 giờ chiều\n\n"
            "Không cần thực hiện tất cả cùng lúc. Chọn một thay đổi nhỏ và thử trong một tuần."
        ),
        "order_index": 2,
        "estimated_read_seconds": 70,
        "reflection_prompt": "Có thói quen nào bạn muốn thử thêm vào trước khi ngủ không?",
    },

    # ── kp_social_energy ──────────────────────────────────────────────────
    {
        "card_id": "kc_social_introvert",
        "pack_id": "kp_social_energy",
        "title": "Kiệt sức sau giao tiếp — hoàn toàn bình thường",
        "content_markdown": (
            "Một số người cảm thấy mệt sau thời gian dài giao tiếp xã hội — "
            "dù cuộc trò chuyện đó hoàn toàn dễ chịu. Điều này không có nghĩa "
            "là bạn có vấn đề với xã hội hay 'hướng nội bệnh lý'.\n\n"
            "Mỗi người có ngưỡng xã hội khác nhau, và ngưỡng đó còn thay đổi "
            "theo trạng thái sức khỏe, giấc ngủ, và áp lực hiện tại.\n\n"
            "Nhận ra ngưỡng của mình là kỹ năng tự biết bản thân — "
            "không phải dấu hiệu của điều gì sai."
        ),
        "order_index": 1,
        "estimated_read_seconds": 60,
        "reflection_prompt": "Sau kiểu tương tác nào bạn thường cảm thấy mệt nhất?",
    },
    {
        "card_id": "kc_social_recharge",
        "pack_id": "kp_social_energy",
        "title": "Cách nạp lại năng lượng xã hội",
        "content_markdown": (
            "Nạp lại năng lượng xã hội là cá nhân hoá — không có công thức chung.\n\n"
            "Một số người nạp năng lượng bằng cách ở một mình và yên lặng. "
            "Một số khác lại cảm thấy tốt hơn khi ở bên một người thân thiết, "
            "chứ không phải đám đông.\n\n"
            "Câu hỏi hay để tự hỏi: 'Sau điều này, tôi cảm thấy được nạp thêm hay mất đi?'\n\n"
            "Việc biết điều gì nạp năng lượng cho bạn là nền tảng của tự chăm sóc bản thân."
        ),
        "order_index": 2,
        "estimated_read_seconds": 55,
        "reflection_prompt": "Điều gì thường giúp bạn cảm thấy phục hồi sau một ngày dài?",
    },
    {
        "card_id": "kc_social_boundaries",
        "pack_id": "kp_social_energy",
        "title": "Ranh giới trong giao tiếp",
        "content_markdown": (
            "Đặt ranh giới trong giao tiếp không có nghĩa là từ chối mọi người — "
            "mà là quản lý năng lượng có ý thức.\n\n"
            "Ranh giới lành mạnh có thể trông như:\n\n"
            "- Nói 'tôi cần thêm thời gian để trả lời' thay vì phản ứng ngay\n"
            "- Chọn không tham gia những cuộc trò chuyện làm bạn kiệt sức mà không có lợi\n"
            "- Cho phép mình rời buổi gặp gỡ khi đã đủ — không cần giải thích dài\n\n"
            "Ranh giới là kỹ năng học được, không phải tính cách bẩm sinh."
        ),
        "order_index": 3,
        "estimated_read_seconds": 65,
        "reflection_prompt": None,
    },
]


def get_all_packs() -> list[dict]:
    return KNOWLEDGE_PACKS


def get_cards_for_pack(pack_id: str) -> list[dict]:
    return sorted(
        [c for c in KNOWLEDGE_CARDS if c["pack_id"] == pack_id],
        key=lambda c: c["order_index"],
    )


def get_pack(pack_id: str) -> dict | None:
    return next((p for p in KNOWLEDGE_PACKS if p["pack_id"] == pack_id), None)


def get_card(card_id: str) -> dict | None:
    return next((c for c in KNOWLEDGE_CARDS if c["card_id"] == card_id), None)
