from app.services.exercise_catalog import build_chat_attachment, get_exercise, list_exercises


def test_list_exercises_contains_clickable_breathing_session():
    exercises = list_exercises()

    breathing = next(item for item in exercises if item["id"] == "breath_478")

    assert breathing["title"] == "Hơi thở bình yên"
    assert breathing["route"] == "/serene/exercises?exercise=breath_478"
    assert breathing["pattern"] == {"inhale": 4, "hold": 7, "exhale": 8}


def test_get_exercise_returns_none_for_unknown_id():
    assert get_exercise("missing") is None


def test_build_chat_attachment_uses_exercise_contract():
    attachment = build_chat_attachment("breath_478")

    assert attachment == {
        "type": "breathing_exercise",
        "id": "breath_478",
        "title": "Hơi thở bình yên",
        "description": "Bài thở 4-7-8 trong 2 phút để hạ nhịp căng thẳng.",
        "duration_sec": 120,
        "action": "open_exercise",
        "route": "/serene/exercises?exercise=breath_478",
        "thumbnail": None,
    }
