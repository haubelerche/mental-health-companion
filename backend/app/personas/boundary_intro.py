"""Deprecated boundary-intro compatibility response for legacy clients."""

from __future__ import annotations

BOUNDARY_INTRO_TEXT = "Hậu là persona unlockable bằng 500 tim. Không cần bước xác nhận riêng."

BOUNDARY_INTRO_POINTS = [
    "Hậu thay thế persona unlockable cũ.",
    "Mở khóa Hậu bằng 500 tim trong cửa hàng vật phẩm.",
]


def build_boundary_intro_response() -> dict[str, object]:
    return {
        "intro_text": BOUNDARY_INTRO_TEXT,
        "key_points": BOUNDARY_INTRO_POINTS,
        "acceptance_required": False,
    }
