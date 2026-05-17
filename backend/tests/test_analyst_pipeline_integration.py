"""Integration-oriented analyst pipeline regression tests."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest


def test_analyst_signal_model_has_evidence_refs_field():
    from app.services.db.models import AnalystSignal

    assert hasattr(AnalystSignal, "evidence_refs")


def test_record_analyst_bundle_signal_stores_evidence_refs():
    from app.services.analyst_writer import record_analyst_bundle_signal

    class FakeBundle:
        emotional_theme = "academic_pressure"
        risk_indicators = ["deadline"]
        suggested_focus = "sleep"

    db = MagicMock()
    result = record_analyst_bundle_signal(
        db,
        user_id="u1",
        session_id="s1",
        analyst_bundle=FakeBundle(),
        distress_score=0.45,
        evidence_refs=["mood:c1", "screening:abc123"],
    )

    assert result is not None
    added = db.add.call_args[0][0]
    assert added.evidence_refs == ["mood:c1", "screening:abc123"]


def test_analyst_context_load_failure_does_not_block_chat(monkeypatch):
    from app.services.analyst_context_loader import AnalystContextLoader

    def boom(*args, **kwargs):
        raise RuntimeError("DB connection lost")

    monkeypatch.setattr(AnalystContextLoader, "load_all", boom)

    analyst_extra_context: str | None = "will_be_overwritten"
    try:
        _ctx = AnalystContextLoader.__new__(AnalystContextLoader)
        _ctx.load_all(user_id="u1", window_days=14)
        analyst_extra_context = "should_not_reach"
    except Exception:
        analyst_extra_context = None

    assert analyst_extra_context is None


def test_all_five_screening_band_helpers_return_safe_strings():
    from app.services.analyst_agent import (
        _dass21_anxiety_band,
        _dass21_depression_band,
        _dass21_stress_band,
        _gad7_band,
        _mdq_band,
        _pcl5_band,
        _phq9_band,
    )

    for score in range(28):
        assert _phq9_band(score) in ("minimal", "mild", "moderate", "moderately_severe_or_above")
    for score in range(22):
        assert _gad7_band(score) in ("minimal", "mild", "moderate", "severe")
    for score in range(43):
        assert _dass21_depression_band(score) in ("normal", "mild", "moderate", "severe_or_above")
        assert _dass21_anxiety_band(score) in ("normal", "mild", "moderate", "severe_or_above")
        assert _dass21_stress_band(score) in ("normal", "mild", "moderate", "severe_or_above")
    for score in range(14):
        assert _mdq_band(score) in ("no_signal", "possible_signal")
    for score in range(81):
        assert _pcl5_band(score) in ("minimal", "low_to_moderate", "moderate", "moderately_high")

    forbidden = ["disorder", "ptsd", "bipolar", "depression", "anxiety", "diagnosis", "roi loan"]
    all_outputs = (
        [_phq9_band(s) for s in range(28)]
        + [_gad7_band(s) for s in range(22)]
        + [_dass21_depression_band(s) for s in range(43)]
        + [_mdq_band(s) for s in range(14)]
        + [_pcl5_band(s) for s in range(81)]
    )
    for out in all_outputs:
        for term in forbidden:
            assert term not in out.lower()


def test_analyst_context_evidence_refs_not_pii():
    import re

    from app.services.analyst_context_loader import AnalystContextLoader
    from app.services.db.models import MoodCheckin

    db = MagicMock()
    row = MagicMock(spec=MoodCheckin)
    row.checkin_id = "c-abc-123"
    row.mood = "lo_au"
    row.triggers = []
    row.logged_date = date.today()
    db.scalars.return_value.all.return_value = [row]
    db.scalar.return_value = None

    ctx = AnalystContextLoader(db=db).load_all(user_id="user@example.com", window_days=14)

    pii_patterns = [r"\S+@\S+\.\S+", r"\b0[0-9]{9,10}\b"]
    for ref in ctx.evidence_refs:
        for pattern in pii_patterns:
            assert not re.search(pattern, ref)


def test_analyst_node_emits_context_load_span(monkeypatch):
    events_emitted: list[str] = []

    class FakeTracer:
        def event(self, name: str, **kwargs: object) -> None:
            events_emitted.append(name)

        def generation(self, *args: object, **kwargs: object) -> None:
            pass

    monkeypatch.setattr("app.services.langgraph_chat.get_active_tracer", lambda: FakeTracer())

    import app.services.langgraph_chat as lc

    state: dict = {
        "user_message": "toi lo lang nhieu",
        "recent_messages": [],
        "mood_today": None,
        "top_triggers": [],
        "effective_coping": [],
        "clinical_trajectory": "",
        "analyst_extra_context": None,
        "nutrition_meals": None,
        "mem0_facts": [],
        "graph_patterns": {},
        "distress_score": 0.85,
        "correlation_id": "test-123",
        "user_id": "u1",
        "session_id": "s1",
        "crisis_route_finalized": False,
        "analyst_bundle": None,
        "use_fast_friend_model": False,
        "active_persona_id": "friend",
        "active_memory_text": "",
        "active_goals": [],
        "user_traits": {},
    }
    lc.analyst_node(state)

    assert any("analyst" in event for event in events_emitted)
