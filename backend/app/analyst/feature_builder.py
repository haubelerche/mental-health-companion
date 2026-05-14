from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import mean, pstdev
from typing import Any

from app.analyst.types import AnalystFeatureSnapshotPayload, AnalystSourceEvent

FEATURE_VERSION = "analyst_features_v1"

_MOOD_SCORE = {
    "terrible": 1,
    "stressful": 2,
    "bad": 2,
    "sad": 3,
    "fine": 5,
    "neutral": 5,
    "good": 7,
    "peaceful": 8,
    "awesome": 9,
    "delightful": 10,
}


def _score_mood(raw: Any) -> int | None:
    if raw is None:
        return None
    return _MOOD_SCORE.get(str(raw).strip().lower())


def _band_phq9(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 20:
        return "severe_signal"
    if score >= 15:
        return "moderately_severe_signal"
    if score >= 10:
        return "moderate_signal"
    if score >= 5:
        return "mild_signal"
    return "minimal_signal"


def _band_gad7(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 15:
        return "severe_signal"
    if score >= 10:
        return "moderate_signal"
    if score >= 5:
        return "mild_signal"
    return "minimal_signal"


def _top(counter: Counter[str], limit: int = 5) -> list[str]:
    return [label for label, _ in counter.most_common(limit)]


def build_features(events: list[AnalystSourceEvent], *, missing_sources: list[str]) -> AnalystFeatureSnapshotPayload:
    mood_events = [e for e in events if e.event_type == "mood_checkin"]
    meal_events = [e for e in events if e.event_type == "meal_checkin"]
    memory_events = [e for e in events if e.event_type == "memory"]
    conversation_events = [e for e in events if e.source_table in {"messages", "session_summaries_archive"}]
    screening_events = [e for e in events if e.event_type == "screening_result"]
    engagement_events = [e for e in events if e.event_type in {"resource_play", "bookmark", "persona_selection"}]
    safety_events = [e for e in events if e.event_type == "safety_snapshot"]

    mood = _mood_features(mood_events)
    nutrition = _nutrition_features(meal_events, mood_events)
    screening = _screening_features(screening_events)
    memory = _memory_features(memory_events)
    conversation = _conversation_features(conversation_events)
    engagement = _engagement_features(engagement_events)
    safety_internal = _safety_features(safety_events)
    data_quality = {
        "total_events": len(events),
        "source_count": len({e.source_table for e in events}),
        "missing_sources": missing_sources,
        "is_provisional": len(events) < 5 or len({e.source_table for e in events}) < 2,
    }
    return AnalystFeatureSnapshotPayload(
        mood=mood,
        nutrition=nutrition,
        screening=screening,
        memory=memory,
        conversation=conversation,
        engagement=engagement,
        safety_internal=safety_internal,
        data_quality=data_quality,
    )


def _mood_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    scores_by_day: dict[date, list[int]] = defaultdict(list)
    period_counts: Counter[str] = Counter()
    emotions: Counter[str] = Counter()
    triggers: Counter[str] = Counter()
    period_scores: dict[str, list[int]] = defaultdict(list)
    for event in events:
        mood_raw = event.payload.get("mood")
        score = _score_mood(mood_raw)
        if score is not None and event.local_date is not None:
            scores_by_day[event.local_date].append(score)
            period_scores[event.local_period].append(score)
        period_counts[event.local_period] += 1
        emotions.update(str(x).strip() for x in event.payload.get("emotions", []) if str(x).strip())
        triggers.update(str(x).strip() for x in event.payload.get("triggers", []) if str(x).strip())

    day_avgs = [mean(v) for v in scores_by_day.values() if v]
    morning = period_scores.get("morning") or []
    evening = period_scores.get("evening") or []
    delta = round(mean(evening) - mean(morning), 2) if morning and evening else None
    return {
        "checkin_count": len(events),
        "days_with_data": len(scores_by_day),
        "avg_score": round(mean(day_avgs), 2) if day_avgs else None,
        "volatility": round(pstdev(day_avgs), 2) if len(day_avgs) >= 2 else None,
        "morning_evening_delta": delta,
        "dominant_emotions": _top(emotions),
        "top_triggers": _top(triggers),
        "checkin_coverage": dict(period_counts),
    }


def _nutrition_features(meal_events: list[AnalystSourceEvent], mood_events: list[AnalystSourceEvent]) -> dict[str, Any]:
    coverage: Counter[str] = Counter()
    days_by_slot: dict[str, set[date]] = defaultdict(set)
    for event in meal_events:
        slot = str(event.payload.get("meal_slot") or "unknown")
        coverage[slot] += 1
        if event.local_date:
            days_by_slot[slot].add(event.local_date)
    observed_days = {event.local_date for event in meal_events if event.local_date}
    skipped = {
        slot: max(0, len(observed_days) - len(days_by_slot.get(slot, set())))
        for slot in ("breakfast", "lunch", "dinner")
    }
    low_mood_days = {
        event.local_date
        for event in mood_events
        if event.local_date and (_score_mood(event.payload.get("mood")) or 10) <= 4
    }
    skipped_breakfast_low_mood = len(
        [day for day in observed_days if day not in days_by_slot.get("breakfast", set()) and day in low_mood_days]
    )
    return {
        "meal_log_count": len(meal_events),
        "days_observed": len(observed_days),
        "meal_coverage": dict(coverage),
        "skipped_meal_counts": skipped,
        "low_mood_after_skipped_breakfast_count": skipped_breakfast_low_mood,
        "correlation_notice": "correlation_only" if skipped_breakfast_low_mood else None,
    }


def _screening_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    if not events:
        return {"available": False}
    latest = max(events, key=lambda event: event.occurred_at)
    phq = latest.numeric_features.get("phq9_score")
    gad = latest.numeric_features.get("gad7_score")
    return {
        "available": True,
        "phq9_score_band_internal": _band_phq9(int(phq)) if phq is not None else None,
        "gad7_score_band_internal": _band_gad7(int(gad)) if gad is not None else None,
        "last_scored_at": latest.occurred_at.isoformat(),
        "coverage": latest.payload,
    }


def _memory_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    stressors: Counter[str] = Counter()
    coping: Counter[str] = Counter()
    support: Counter[str] = Counter()
    for event in events:
        text = f"{event.text_for_llm or ''} {event.payload}".lower()
        for token in ("deadline", "gia đình", "học", "công việc", "ngủ"):
            if token in text:
                stressors[token] += 1
        for token in ("đi bộ", "nghe nhạc", "thở", "viết", "ngủ"):
            if token in text:
                coping[token] += 1
        for token in ("short_reply", "gentle_question", "nhẹ", "ngắn"):
            if token in text:
                support[token] += 1
    return {
        "memory_count": len(events),
        "stable_stressors": _top(stressors, 4),
        "coping_preferences": _top(coping, 4),
        "support_style": _top(support, 4),
    }


def _conversation_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    themes = Counter(str(e.payload.get("dominant_emotion") or "").strip() for e in events if e.payload.get("dominant_emotion"))
    return {
        "event_count": len(events),
        "recent_emotional_themes": _top(themes),
        "bounded_text_evidence_count": sum(1 for e in events if e.text_for_llm),
    }


def _engagement_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    by_type = Counter(e.event_type for e in events)
    return {"event_count": len(events), "by_type": dict(by_type)}


def _safety_features(events: list[AnalystSourceEvent]) -> dict[str, Any]:
    high = [e for e in events if e.payload.get("crisis_mode") or e.payload.get("escalation_flag")]
    return {
        "snapshot_count": len(events),
        "restricted_snapshot_count": len([e for e in events if e.sensitivity == "restricted"]),
        "last_high_risk_at_internal": max((e.occurred_at.isoformat() for e in high), default=None),
    }
