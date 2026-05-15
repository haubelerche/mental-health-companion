"""Tests: analyst_bundle exposed from run_non_sos_turn + record_analyst_bundle_signal."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.analyst_writer import record_analyst_bundle_signal


# --- record_analyst_bundle_signal unit tests ---


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    return db


class FakeBundle:
    def __init__(self, emotional_theme="academic_pressure", risk_indicators=None, suggested_focus=None):
        self.emotional_theme = emotional_theme
        self.risk_indicators = risk_indicators or ["deadline_stress"]
        self.suggested_focus = suggested_focus


def test_record_analyst_bundle_signal_writes_signal_row():
    db = _make_db()
    bundle = FakeBundle(emotional_theme="academic_pressure", risk_indicators=["deadline"])
    result = record_analyst_bundle_signal(
        db,
        user_id="u1",
        session_id="s1",
        analyst_bundle=bundle,
        distress_score=0.45,
    )
    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result is not None


def test_record_analyst_bundle_signal_skips_sos():
    db = _make_db()
    bundle = FakeBundle()
    result = record_analyst_bundle_signal(
        db, user_id="u1", session_id="s1", analyst_bundle=bundle, sos_triggered=True
    )
    db.add.assert_not_called()
    assert result is None


def test_record_analyst_bundle_signal_skips_none_bundle():
    db = _make_db()
    result = record_analyst_bundle_signal(
        db, user_id="u1", session_id="s1", analyst_bundle=None
    )
    db.add.assert_not_called()
    assert result is None


def test_record_analyst_bundle_signal_skips_cold_start_theme():
    db = _make_db()
    bundle = FakeBundle(emotional_theme="cold_start_screen")
    result = record_analyst_bundle_signal(
        db, user_id="u1", session_id="s1", analyst_bundle=bundle
    )
    db.add.assert_not_called()
    assert result is None


def test_record_analyst_bundle_signal_skips_unknown_theme():
    db = _make_db()
    bundle = FakeBundle(emotional_theme="unknown")
    result = record_analyst_bundle_signal(
        db, user_id="u1", session_id="s1", analyst_bundle=bundle
    )
    assert result is None


def test_record_analyst_bundle_signal_distress_clamped():
    """distress_score out of [0, 1] must be clamped, not raise."""
    db = _make_db()
    bundle = FakeBundle(emotional_theme="self_blame", risk_indicators=["lo_au"])
    result = record_analyst_bundle_signal(
        db,
        user_id="u1",
        session_id="s1",
        analyst_bundle=bundle,
        distress_score=99.9,
    )
    assert result is not None
    added = db.add.call_args[0][0]
    assert 0.0 <= added.distress_score <= 1.0


def test_record_analyst_bundle_signal_db_exception_returns_none():
    db = _make_db()
    db.flush.side_effect = RuntimeError("db down")
    bundle = FakeBundle(emotional_theme="burnout")
    result = record_analyst_bundle_signal(
        db, user_id="u1", session_id="s1", analyst_bundle=bundle
    )
    assert result is None


# --- run_non_sos_turn exposes analyst_bundle ---


def test_run_non_sos_turn_result_contains_analyst_bundle_key():
    """analyst_bundle key must be present in the turn result dict."""
    import importlib
    import sys

    langgraph_mod = sys.modules.get("app.services.langgraph_chat")
    if langgraph_mod is None:
        import app.services.langgraph_chat as langgraph_mod  # type: ignore

    fake_bundle = FakeBundle(emotional_theme="academic_pressure")
    fake_out = {
        "reply": "Mình nghe bạn nói.",
        "assistant_tone": "validating",
        "goi_y_nhanh": [],
        "the_dinh_kem": [],
        "routing_history": [],
        "analyst_bundle": fake_bundle,
    }

    fake_snap = MagicMock()
    fake_snap.distress_score = 0.3
    fake_snap.conversation_mode = "friend"
    fake_snap.safety_tier = "normal"
    fake_snap.risk_level = 1

    with (
        patch.object(langgraph_mod, "get_chat_graph") as mock_graph,
        patch.object(langgraph_mod, "build_snapshot", return_value=fake_snap),
        patch.object(langgraph_mod, "_apply_cold_start_profile", return_value=(0.3, {}, "")),
        patch.object(langgraph_mod, "_trace_analyst_route_decision"),
        patch.object(langgraph_mod, "_trace_span"),
        patch.object(langgraph_mod, "set_active_tracer"),
        patch.object(langgraph_mod, "ChatTurnTracer", return_value=MagicMock()),
        patch.object(langgraph_mod, "get_settings", return_value=MagicMock(
            distress_voice_hint=0.6, distress_critical=0.85,
        )),
    ):
        mock_graph.return_value.invoke.return_value = fake_out
        result = langgraph_mod.run_non_sos_turn(
            user_message="test",
            recent_messages=[],
            mood_today=None,
            distress_score=0.3,
        )

    assert "analyst_bundle" in result
    assert result["analyst_bundle"] is fake_bundle
