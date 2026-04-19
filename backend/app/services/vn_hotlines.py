"""
Đường dây nóng Việt Nam (tham khảo công khai). Dùng cho SOS payload và GET /connect/hotlines.
"""

from __future__ import annotations

# Định dạng hiển thị / quay số — giữ khoảng trắng theo cách viết thông dụng tại VN.


def hotline_cards_sos() -> list[dict[str, str]]:
    """Khối `hotline_cards` trong crisis payload (§7.2) — label + phone."""
    return [
        {
            "label": "Cấp cứu trầm cảm — BV Tâm thần TP.HCM (24/7)",
            "phone": "1900 1267",
        },
        {
            "label": "Dự án Ngày Mai — 13h–20h30 (Thứ 4, 6, 7, CN)",
            "phone": "096 306 1414",
        },
        {
            "label": "Đường dây tham vấn miễn phí",
            "phone": "0909 65 80 35",
        },
        {
            "label": "Tổng đài 1088 — tư vấn đa lĩnh vực (gồm tâm lý)",
            "phone": "1088",
        },
        {
            "label": "Tư vấn tình cảm & căng thẳng",
            "phone": "1900 633725",
        },
        {
            "label": "Cấp cứu y tế khẩn cấp",
            "phone": "115",
        },
    ]


def connect_hotlines_list() -> list[dict[str, str]]:
    """Danh sách cho `GET /connect/hotlines` (name, number, available, note)."""
    return [
        {
            "name": "Cấp cứu trầm cảm — Bệnh viện Tâm thần TP.HCM",
            "number": "1900 1267",
            "available": "24/7",
            "note": "Kết nối trực tiếp với chuyên gia y tế hỗ trợ trầm cảm hoặc nguy cơ tự sát.",
        },
        {
            "name": "Đường dây nóng Ngày Mai",
            "number": "096 306 1414",
            "available": "13:00–20:30 (Thứ 4, 6, 7, Chủ nhật)",
            "note": "Dự án hỗ trợ người trẻ trầm cảm.",
        },
        {
            "name": "Đường dây tham vấn miễn phí",
            "number": "0909 65 80 35",
            "available": "Theo giờ tổng đài",
            "note": "Tư vấn tâm lý trực tiếp qua điện thoại cho người gặp khó khăn.",
        },
        {
            "name": "Tổng đài 1088",
            "number": "1088",
            "available": "Theo tỉnh/thành và giờ phục vụ",
            "note": "Tư vấn đa lĩnh vực, bao gồm tâm lý và tình cảm.",
        },
        {
            "name": "Tổng đài tư vấn tình cảm",
            "number": "1900 633725",
            "available": "Theo giờ tổng đài",
            "note": "Chuyên gia hỗ trợ giải tỏa căng thẳng và tư vấn các mối quan hệ.",
        },
        {
            "name": "Cấp cứu y tế",
            "number": "115",
            "available": "24/7",
            "note": "Cấp cứu y tế khẩn cấp.",
        },
    ]
