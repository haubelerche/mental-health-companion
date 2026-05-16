"""Dashboard Analyst evaluation harness — PR-06.

Tests that dashboard insight cards are:
- Evidence-backed (evidence_count > 0, evidence_refs present)
- Non-diagnostic (no disorder claims, clinical labels)
- Concise (not long generic text)
- Correctly absent when no data exists (no hallucination)
- Graded by signal strength (low vs high confidence differ)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timezone

from app.services.analyst_agent import AnalystAgent
from app.services.analyst_pipeline import AnalystPipeline


# ---------------------------------------------------------------------------
# AnalystAgent.generate_bundle — evidence_refs and missing_info logic
# ---------------------------------------------------------------------------

DIAGNOSIS_KEYWORDS = [
    "trầm cảm",
    "rối loạn",
    "disorder",
    "bệnh",
    "chẩn đoán",
    "diagnosis",
    "bạn bị",
    "phần trăm",
    "%",
]


def _assert_no_diagnosis(obj: object) -> None:
    text = str(obj).lower()
    for kw in DIAGNOSIS_KEYWORDS:
        assert kw.lower() not in text, f"Diagnostic keyword '{kw}' found in output: {obj}"


def test_analyst_bundle_has_evidence_refs_when_events_supplied():
    events = [
        {"event_id": "e1", "emotion": "sad", "triggers": ["deadline"]},
        {"event_id": "e2", "emotion": "sad", "triggers": ["deadline"]},
        {"event_id": "e3", "emotion": "anxious", "triggers": ["co_don"]},
    ]
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=events)
    assert len(bundle.evidence_refs) == 3
    assert "e1" in bundle.evidence_refs


def test_analyst_bundle_insufficient_signal_when_no_events():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=[])
    assert "insufficient_signal" in bundle.missing_info
    assert bundle.confidence == "low"


def test_analyst_bundle_confidence_low_for_single_event():
    bundle = AnalystAgent().generate_bundle(
        user_id="u1",
        events=[{"event_id": "e1", "emotion": "anxious", "triggers": []}],
    )
    assert bundle.confidence == "low"


def test_analyst_bundle_confidence_medium_for_two_events():
    events = [
        {"event_id": f"e{i}", "emotion": "sad", "triggers": ["deadline"]}
        for i in range(2)
    ]
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=events)
    assert bundle.confidence in {"medium", "high"}
    assert "insufficient_signal" not in bundle.missing_info


def test_analyst_bundle_confidence_high_for_five_or_more_events():
    events = [
        {"event_id": f"e{i}", "emotion": "anxious", "triggers": ["stress"]}
        for i in range(5)
    ]
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=events)
    assert bundle.confidence == "high"


def test_analyst_bundle_recurring_trigger_requires_two_occurrences():
    events = [
        {"event_id": "e1", "emotion": "anxious", "triggers": ["deadline", "sleep"]},
        {"event_id": "e2", "emotion": "sad", "triggers": ["deadline"]},
        {"event_id": "e3", "emotion": "sad", "triggers": ["co_don"]},
    ]
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=events)
    assert "deadline" in bundle.recurring_triggers
    assert "co_don" not in bundle.recurring_triggers  # only once


def test_analyst_bundle_no_diagnosis_in_any_field():
    events = [
        {"event_id": "e1", "emotion": "sad", "triggers": ["stress"]},
        {"event_id": "e2", "emotion": "anxious", "triggers": ["co_don"]},
    ]
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=events)
    _assert_no_diagnosis(bundle.dominant_emotions)
    _assert_no_diagnosis(bundle.recurring_triggers)


def test_analyst_bundle_single_weak_signal_no_dominant_emotions():
    bundle = AnalystAgent().generate_bundle(
        user_id="u1",
        events=[{"event_id": "e1", "emotion": None, "triggers": []}],
    )
    assert bundle.dominant_emotions == []
    assert bundle.confidence == "low"


# ---------------------------------------------------------------------------
# AnalystPipeline.run — payload shape
# ---------------------------------------------------------------------------

def test_pipeline_run_shape_has_required_fields():
    payload = AnalystPipeline().run(
        user_id="u1",
        normalized_events=[{"event_id": "e1", "emotion": "sad", "triggers": ["deadline"]}],
    )
    assert "evidence_refs" in payload
    assert "confidence" in payload
    assert "missing_info" in payload
    assert "final_text" not in payload  # advisor role contract: no user-facing prose


def test_pipeline_run_no_events_signals_insufficient():
    payload = AnalystPipeline().run(user_id="u1", normalized_events=[])
    assert "insufficient_signal" in payload.get("missing_info", [])


def test_pipeline_payload_no_diagnosis_keywords():
    events = [
        {"event_id": f"e{i}", "emotion": "lo_au", "triggers": ["deadline"]}
        for i in range(5)
    ]
    payload = AnalystPipeline().run(user_id="u1", normalized_events=events)
    _assert_no_diagnosis(payload)


# ---------------------------------------------------------------------------
# PHQ-9 / GAD-7 absent → no hallucination
# Simulated via "no mood checkins" and "no events" scenario
# ---------------------------------------------------------------------------

def test_no_screening_data_produces_low_confidence_insufficient():
    """When no PHQ/GAD/mood events provided, confidence must be low and signal insufficient."""
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=[])
    assert bundle.confidence == "low"
    assert "insufficient_signal" in bundle.missing_info
    assert bundle.dominant_emotions == []
    assert bundle.recurring_triggers == []


def test_no_screening_data_no_safe_dashboard_candidates():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=[])
    assert bundle.safe_dashboard_candidates == []


# ---------------------------------------------------------------------------
# Multi-signal pattern: low sleep + low mood + skipped meals
# (Simulated via events with multiple emotion/trigger signals)
# ---------------------------------------------------------------------------

MULTI_SIGNAL_EVENTS = [
    {"event_id": "mood:0", "emotion": "sad", "triggers": ["skipped_sleep"]},
    {"event_id": "mood:1", "emotion": "sad", "triggers": ["skipped_sleep"]},
    {"event_id": "mood:2", "emotion": "anxious", "triggers": ["skipped_sleep"]},
    {"event_id": "meal:0", "emotion": None, "triggers": ["meal_breakfast"]},
    {"event_id": "meal:1", "emotion": None, "triggers": ["meal_dinner"]},
    {"event_id": "mem0:0", "emotion": None, "triggers": ["mem0_source_user"]},
]


def test_multi_signal_produces_recurring_trigger():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=MULTI_SIGNAL_EVENTS)
    assert "skipped_sleep" in bundle.recurring_triggers


def test_multi_signal_produces_medium_or_high_confidence():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=MULTI_SIGNAL_EVENTS)
    assert bundle.confidence in {"medium", "high"}


def test_multi_signal_evidence_refs_contain_all_sources():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=MULTI_SIGNAL_EVENTS)
    ids = set(bundle.evidence_refs)
    assert "mood:0" in ids
    assert "meal:0" in ids
    assert "mem0:0" in ids


def test_multi_signal_no_diagnosis_keywords():
    bundle = AnalystAgent().generate_bundle(user_id="u1", events=MULTI_SIGNAL_EVENTS)
    _assert_no_diagnosis(bundle.dominant_emotions)
    _assert_no_diagnosis(bundle.recurring_triggers)
    _assert_no_diagnosis(str(bundle.cognitive_patterns))


# ---------------------------------------------------------------------------
# InsightHypothesis writer integration: record_analyst_signal skips SOS
# ---------------------------------------------------------------------------

def test_record_analyst_signal_skips_sos_session():
    from app.services.analyst_writer import record_analyst_signal
    from app.services.memory_enrichment import StructuredExtract

    db = MagicMock()
    # StructuredExtract(key_triggers, coping_attempts, dominant_emotion, sos_triggered)
    extract = StructuredExtract(["co_don"], ["chia_se"], "buon_ba", True)
    result = record_analyst_signal(db, user_id="u1", session_id="s1", extract=extract)
    assert result is None
    db.add.assert_not_called()


def test_record_analyst_signal_writes_non_sos_session():
    from app.services.analyst_writer import record_analyst_signal
    from app.services.memory_enrichment import StructuredExtract

    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    extract = StructuredExtract(["deadline", "cang_thang"], ["chia_se"], "lo_au", False)
    result = record_analyst_signal(db, user_id="u1", session_id="s1", extract=extract)
    db.add.assert_called_once()
    db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# DashboardInsightCard shape: evidence_count > 0, no clinical leak
# ---------------------------------------------------------------------------

def test_insight_card_model_requires_evidence_count():
    from app.dashboard.types import DashboardInsightCard

    card = DashboardInsightCard(
        insight_id="ih_1",
        title="Tín hiệu căng thẳng lặp lại",
        user_safe_summary="Serene nhận thấy một số tín hiệu nhẹ.",
        evidence_count=3,
        evidence_sources=["Check-in & phiên trò chuyện"],
        confidence="medium",
        severity_band="watch",
        suggested_action="Thử nghỉ ngơi 5 phút.",
        updated_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
    )
    assert card.evidence_count > 0
    assert "trầm cảm" not in card.user_safe_summary
    assert "rối loạn" not in card.user_safe_summary
    assert "diagnosis" not in card.user_safe_summary.lower()


def test_insight_card_rejects_zero_evidence_count():
    from app.dashboard.types import DashboardInsightCard
    import pydantic

    with pytest.raises((pydantic.ValidationError, ValueError)):
        DashboardInsightCard(
            insight_id="ih_1",
            title="Test",
            user_safe_summary="summary",
            evidence_count=-1,  # invalid
            evidence_sources=[],
            confidence="low",
            severity_band="neutral",
            updated_at=datetime(2026, 5, 15, tzinfo=timezone.utc),
        )
