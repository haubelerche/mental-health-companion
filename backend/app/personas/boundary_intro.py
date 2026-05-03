"""Crush boundary intro — the disclosure text and acceptance endpoint logic.

PRD §3 + plan §05: Crush cannot activate until boundary_accepted=True.
The copy must communicate the non-romantic, safety-first nature of Crush mode.
"""

from __future__ import annotations

BOUNDARY_INTRO_TEXT = (
    "Crush là chế độ giao tiếp ấm áp hơn một chút — không phải người yêu thật, "
    "không tạo ra sự ràng buộc, phụ thuộc, hay tình cảm lãng mạn thật sự. "
    "Mình vẫn là Serene, chỉ là cởi mở và ấm áp hơn một chút khi bạn cần. "
    "Nếu bạn đang ở trạng thái căng thẳng cao, Serene có thể tạm thời chuyển về chế độ Bạn Tốt. "
    "Bạn có thể tắt chế độ này bất cứ lúc nào."
)

BOUNDARY_INTRO_POINTS = [
    "Crush là chế độ giao tiếp, không phải mối quan hệ thật.",
    "Không có ràng buộc, không phụ thuộc, không tình dục hoá.",
    "Serene có thể tạm về Bạn Tốt khi cần thiết vì lý do an toàn.",
    "Bạn tắt được bất cứ lúc nào.",
]


def build_boundary_intro_response() -> dict[str, object]:
    return {
        "intro_text": BOUNDARY_INTRO_TEXT,
        "key_points": BOUNDARY_INTRO_POINTS,
        "acceptance_required": True,
    }
