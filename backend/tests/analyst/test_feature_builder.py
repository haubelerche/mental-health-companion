from __future__ import annotations

from datetime import datetime, timedelta

from app.analyst.feature_builder import build_features
from app.analyst.source_events import make_event


def test_mood_three_period_feature_calculation():
    base = datetime(2026, 5, 14, 7, 0, 0)
    events = [
        make_event(
            user_id="u1",
            source_table="mood_checkins",
            source_id="m1",
            event_type="mood_checkin",
            occurred_at=base,
            local_period="morning",
            payload={"mood": "good", "emotions": ["ổn"], "triggers": ["deadline"]},
        ),
        make_event(
            user_id="u1",
            source_table="mood_checkins",
            source_id="m2",
            event_type="mood_checkin",
            occurred_at=base + timedelta(hours=12),
            local_period="evening",
            payload={"mood": "bad", "emotions": ["mệt"], "triggers": ["deadline"]},
        ),
    ]
    features = build_features(events, missing_sources=[])
    assert features.mood["checkin_coverage"]["morning"] == 1
    assert features.mood["checkin_coverage"]["evening"] == 1
    assert features.mood["morning_evening_delta"] < 0
    assert features.mood["top_triggers"] == ["deadline"]


def test_nutrition_skipped_breakfast_correlation_is_correlation_only():
    base = datetime(2026, 5, 14, 13, 0, 0)
    events = [
        make_event(
            user_id="u1",
            source_table="nutrition_meal_checkins",
            source_id="meal1",
            event_type="meal_checkin",
            occurred_at=base,
            payload={"meal_slot": "lunch"},
        ),
        make_event(
            user_id="u1",
            source_table="mood_checkins",
            source_id="mood1",
            event_type="mood_checkin",
            occurred_at=base + timedelta(hours=1),
            payload={"mood": "bad"},
        ),
    ]
    features = build_features(events, missing_sources=[])
    assert features.nutrition["meal_coverage"]["lunch"] == 1
    assert features.nutrition["skipped_meal_counts"]["breakfast"] == 1
    assert "disorder" not in str(features.nutrition).lower()

