from __future__ import annotations

from app.services.nutrition_suggestion_service import NutritionSuggestionService


def test_unhealthy_eating_message_gets_specific_meal_suggestion() -> None:
    service = NutritionSuggestionService()

    suggestion = service.suggest_for_message(user_message="Dạo này mình toàn ăn linh tinh, trà sữa với mì gói.")

    assert suggestion is not None
    assert suggestion["id"] == "food_reset"
    assert "Cơm" in suggestion["dish"]
    assert suggestion["route"] == "/serene/nutrition?agent=food_reset"
    assert "tư vấn y khoa" in suggestion["disclaimer"]


def test_skipped_breakfast_gets_breakfast_reset_suggestion() -> None:
    service = NutritionSuggestionService()

    suggestion = service.suggest_for_message(user_message="Mình bỏ bữa sáng mấy ngày rồi, chiều lại ăn đồ ngọt.")

    assert suggestion is not None
    assert suggestion["id"] == "breakfast_reset"
    assert "Yến mạch" in suggestion["dish"]


def test_neutral_message_does_not_create_nutrition_suggestion() -> None:
    service = NutritionSuggestionService()

    suggestion = service.suggest_for_message(user_message="Hôm nay mình hơi chán và muốn nghe một bài nhạc.")

    assert suggestion is None
