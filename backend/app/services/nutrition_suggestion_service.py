from __future__ import annotations

from typing import Any

_CURATIVE_PATTERNS = ("chữa", "cure", "điều trị", "triệu chứng sẽ hết", "khỏi hẳn")


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
