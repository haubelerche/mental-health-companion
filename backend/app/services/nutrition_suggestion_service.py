from __future__ import annotations

import re
import unicodedata
from typing import Any

_CURATIVE_PATTERNS = ("chữa", "cure", "điều trị", "triệu chứng sẽ hết", "khỏi hẳn")

_UNHEALTHY_EATING_PATTERNS = (
    "an linh tinh",
    "an uong linh tinh",
    "toan an vat",
    "an vat thay bua",
    "mi goi",
    "tra sua",
    "do ngot",
    "nuoc ngot",
    "fast food",
    "junk food",
    "bo bua",
    "bo bua sang",
    "khong an sang",
    "an qua khuya",
    "ruou",
    "bia",
)


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", no_marks.replace("đ", "d")).strip()


class NutritionSuggestionService:
    def suggest(self, *, meals_today: list[dict[str, Any]] | None, distress_score: float) -> dict[str, Any] | None:
        if not meals_today and distress_score < 0.45:
            return None
        slots = {str((m or {}).get("slot") or "").lower() for m in (meals_today or [])}
        missing = [slot for slot in ("breakfast", "lunch", "dinner") if slot not in slots]
        if missing:
            text = "Nếu tiện, thử bổ sung một bữa nhẹ như trứng + cơm hoặc cháo ấm để đỡ tụt năng lượng."
        else:
            text = "Bạn đã có nhịp ăn trong ngày; giữ bữa tối nhẹ và uống thêm nước để cơ thể dễ nghỉ hơn."
        suggestion = {
            "title": "Gợi ý ăn nhẹ dễ làm",
            "text": text,
            "disclaimer": "Gợi ý này không thay thế tư vấn y khoa.",
            "missing_slots": missing,
        }
        lowered = " ".join(str(v).lower() for v in suggestion.values())
        if any(x in lowered for x in _CURATIVE_PATTERNS):
            return None
        return suggestion

    def suggest_for_message(self, *, user_message: str, meals_today: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        normalized = _normalize_text(user_message or "")
        if not any(pattern in normalized for pattern in _UNHEALTHY_EATING_PATTERNS):
            return None

        slots = {str((m or {}).get("slot") or "").lower() for m in (meals_today or [])}
        missed_breakfast = "breakfast" not in slots and any(
            pattern in normalized for pattern in ("bo bua sang", "khong an sang", "bo bua")
        )
        late_or_alcohol = any(pattern in normalized for pattern in ("an qua khuya", "ruou", "bia"))

        if missed_breakfast:
            dish = "Yến mạch qua đêm với sữa chua, chuối và hạt chia"
            benefit = "Có tinh bột chậm, protein và chất xơ để giảm đói gấp và đỡ phải bù bằng đồ ngọt."
            tip = "Chuẩn bị trong 5 phút từ tối trước; sáng chỉ cần lấy ra ăn."
            suggestion_id = "breakfast_reset"
        elif late_or_alcohol:
            dish = "Cháo trứng gừng kèm rau xanh mềm"
            benefit = "Ấm, dễ ăn và nhẹ hơn đồ chiên cay khi cơ thể đang mệt hoặc vừa uống rượu bia."
            tip = "Ăn lượng vừa phải, uống thêm nước, và tránh xem đây là cách xử lý say rượu."
            suggestion_id = "gentle_evening_reset"
        else:
            dish = "Cơm gạo lứt hoặc cơm trắng ít, trứng/cá, rau luộc và canh nóng"
            benefit = "Đủ protein, chất xơ và nước để thay thế nhịp ăn vặt nhiều đường hoặc nhiều dầu."
            tip = "Nếu đang rất mệt, chọn phiên bản tối giản: trứng, cơm, rau hoặc canh."
            suggestion_id = "food_reset"

        suggestion = {
            "id": suggestion_id,
            "title": "Gợi ý một bữa cân bằng hơn",
            "dish": dish,
            "benefit": benefit,
            "tip": tip,
            "trigger_reason": "unhealthy_eating_signal",
            "disclaimer": "Gợi ý này chỉ hỗ trợ lựa chọn bữa ăn thường ngày, không thay thế tư vấn y khoa.",
            "route": f"/serene/nutrition?agent={suggestion_id}",
        }
        lowered = " ".join(str(v).lower() for v in suggestion.values())
        if any(pattern in lowered for pattern in _CURATIVE_PATTERNS):
            return None
        return suggestion
