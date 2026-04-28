from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlencode


_EXERCISES: list[dict[str, Any]] = [
    {
        "id": "box_breath",
        "type": "breathing_exercise",
        "title": "Box",
        "description": "Nhịp thở 4-4-4-4 giúp ổn định hệ thần kinh và thư giãn nhanh.",
        "duration_sec": 300,
        "route": "/serene/exercises?exercise=box_breath",
        "pattern": {"inhale": 4, "hold": 4, "exhale": 4, "hold2": 4},
        "steps": [
            "Hít vào bằng mũi trong 4 giây.",
            "Giữ hơi thở trong 4 giây.",
            "Thở ra thật chậm trong 4 giây.",
            "Giữ nhẹ thêm 4 giây rồi lặp lại.",
        ],
        "thumbnail": None,
    },
    {
        "id": "breath_478",
        "type": "breathing_exercise",
        "title": "Hơi thở bình yên",
        "description": "Bài thở 4-7-8 trong 2 phút để hạ nhịp căng thẳng.",
        "duration_sec": 120,
        "route": "/serene/exercises?exercise=breath_478",
        "pattern": {"inhale": 4, "hold": 7, "exhale": 8},
        "steps": [
            "Đặt một tay lên ngực, một tay lên bụng.",
            "Hít vào bằng mũi trong 4 giây.",
            "Giữ hơi thở trong 7 giây.",
            "Thở ra thật chậm trong 8 giây.",
        ],
        "thumbnail": None,
    },
    {
        "id": "equal_breath",
        "type": "breathing_exercise",
        "title": "Equal",
        "description": "Nhịp 5-0-5 giúp cân bằng hơi thở và tăng tập trung.",
        "duration_sec": 300,
        "route": "/serene/exercises?exercise=equal_breath",
        "pattern": {"inhale": 5, "hold": 0, "exhale": 5},
        "steps": [
            "Hít vào đều qua mũi 5 giây.",
            "Thở ra đều 5 giây.",
            "Giữ nhịp mềm và thả lỏng vai gáy.",
        ],
        "thumbnail": None,
    },
    {
        "id": "custom_breath",
        "type": "breathing_exercise",
        "title": "Custom",
        "description": "Tùy chỉnh nhịp thở theo cảm giác hiện tại của bạn.",
        "duration_sec": 300,
        "route": "/serene/exercises?exercise=custom_breath",
        "pattern": None,
        "steps": [
            "Bắt đầu với một nhịp hít vào thoải mái.",
            "Giữ ngắn hoặc bỏ qua nếu thấy khó chịu.",
            "Thở ra dài hơn một chút so với hít vào.",
            "Duy trì nhịp cá nhân trong 5 phút.",
        ],
        "thumbnail": None,
    },
    {
        "id": "grounding_54321",
        "type": "grounding_exercise",
        "title": "Neo lại hiện tại",
        "description": "Grounding 5-4-3-2-1 để kéo sự chú ý về môi trường an toàn quanh bạn.",
        "duration_sec": 180,
        "route": "/serene/exercises?exercise=grounding_54321",
        "pattern": None,
        "steps": [
            "Nhìn quanh và gọi tên 5 thứ bạn thấy.",
            "Chạm vào 4 bề mặt khác nhau.",
            "Lắng nghe 3 âm thanh đang có mặt.",
            "Nhận ra 2 mùi hương hoặc cảm giác trong hơi thở.",
            "Gọi tên 1 điều nhỏ đang giúp bạn an toàn hơn.",
        ],
        "thumbnail": None,
    },
    {
        "id": "body_scan",
        "type": "body_scan",
        "title": "Quét cơ thể dịu lại",
        "description": "Năm phút buông lỏng từng vùng cơ thể sau một ngày quá tải.",
        "duration_sec": 300,
        "route": "/serene/exercises?exercise=body_scan",
        "pattern": None,
        "steps": [
            "Ngồi hoặc nằm ở tư thế bạn thấy vững.",
            "Đưa sự chú ý xuống bàn chân và thả lỏng các ngón chân.",
            "Di chuyển dần lên bắp chân, đùi, bụng và vai.",
            "Thả lỏng hàm, trán và vùng quanh mắt.",
            "Kết thúc bằng một hơi thở sâu, chậm và mềm.",
        ],
        "thumbnail": None,
    },
]


def list_exercises() -> list[dict[str, Any]]:
    return deepcopy(_EXERCISES)


def get_exercise(exercise_id: str) -> dict[str, Any] | None:
    for exercise in _EXERCISES:
        if exercise["id"] == exercise_id:
            return deepcopy(exercise)
    return None


def build_chat_attachment(exercise_id: str) -> dict[str, Any]:
    exercise = get_exercise(exercise_id)
    if exercise is None:
        exercise = get_exercise("breath_478")
    if exercise is None:
        raise RuntimeError("exercise catalog is empty")

    return {
        "type": exercise["type"],
        "id": exercise["id"],
        "title": exercise["title"],
        "description": exercise["description"],
        "duration_sec": exercise["duration_sec"],
        "action": "open_exercise",
        "route": exercise["route"],
        "thumbnail": exercise["thumbnail"],
    }


def build_resource_attachment(resource_id: str = "sleep_meditation") -> dict[str, Any]:
    resources: dict[str, dict[str, Any]] = {
        "sleep_meditation": {
            "type": "resource",
            "id": "sleep_meditation",
            "title": "Thiền ngủ dịu lại",
            "description": "Mở bộ sưu tập thiền ngủ, sleep story và âm nền nhẹ để cơ thể chuyển sang trạng thái nghỉ.",
            "duration_sec": 600,
            "action": "open_resource",
            "route": "/serene/resources?category=sleep&q=thi%E1%BB%81n%20ng%E1%BB%A7",
            "thumbnail": None,
        },
        "calm_library": {
            "type": "resource",
            "id": "calm_library",
            "title": "Thư viện bình yên",
            "description": "Các bài nghe, bài thở và âm thanh thiên nhiên để hạ nhịp căng thẳng.",
            "duration_sec": 900,
            "action": "open_resource",
            "route": "/serene/resources?category=meditate",
            "thumbnail": None,
        },
    }
    return deepcopy(resources.get(resource_id) or resources["calm_library"])


def build_clinic_attachment(query: str = "phòng tham vấn tâm lý gần tôi") -> dict[str, Any]:
    clean_query = " ".join(str(query or "").split()) or "phòng tham vấn tâm lý gần tôi"
    return {
        "type": "clinic_map",
        "id": "nearby_clinic",
        "title": "Tìm phòng tham vấn gần bạn",
        "description": "Mở bản đồ Kết Nối để tìm địa chỉ phòng khám, cơ sở tham vấn hoặc hỗ trợ chuyên môn phù hợp.",
        "duration_sec": None,
        "action": "open_connect_map",
        "route": f"/serene/connect?{urlencode({'q': clean_query})}",
        "thumbnail": None,
    }
