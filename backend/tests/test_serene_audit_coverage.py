"""Focused regression tests for Serene audit items (persona routing, Mem0 PII, crisis plan)."""

from __future__ import annotations

from app.api.v1.routers import chat as chat_mod
from app.personas.router import route_persona
from app.services.crisis_intervention_planner import build_fallback_plan


def test_route_persona_crush_high_distress_falls_back_to_ban_than():
    d = route_persona(
        current_persona_id="crush",
        requested_persona_id="crush",
        distress=0.65,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert d.target_persona_id == "ban_than"
    assert d.safety_override is True


def test_route_persona_cun_distress_ceiling():
    d = route_persona(
        current_persona_id="cun",
        requested_persona_id="cun",
        distress=0.41,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert d.target_persona_id == "ban_than"


def test_route_persona_meo_distress_ceiling():
    d = route_persona(
        current_persona_id="meo",
        requested_persona_id="meo",
        distress=0.56,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert d.target_persona_id == "ban_than"


def test_route_persona_low_distress_unlocked_stays():
    d = route_persona(
        current_persona_id="meo",
        requested_persona_id="meo",
        distress=0.2,
        sos_triggered=False,
        is_unlocked=True,
    )
    assert d.target_persona_id == "meo"


def test_route_persona_nguoi_thay_is_free_core_without_unlock():
    d = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="nguoi_thay",
        distress=0.2,
        sos_triggered=False,
        is_unlocked=False,
        user_explicit=True,
    )
    assert d.action == "switch"
    assert d.target_persona_id == "nguoi_thay"


def test_route_persona_locked_progression_reason_is_stable():
    d = route_persona(
        current_persona_id="ban_than",
        requested_persona_id="crush",
        distress=0.2,
        sos_triggered=False,
        is_unlocked=False,
        user_explicit=True,
    )
    assert d.action == "reject"
    assert d.reason == "persona_locked_by_progression"
    assert d.blocked_reason == "persona_locked_by_progression"


def test_enqueue_turn_mem0_masks_vn_phone(monkeypatch):
    captured: dict[str, object] = {}

    class _MM:
        @classmethod
        def instance(cls):
            return cls()

        def add_session(self, user_id: str, messages: list[dict]) -> None:
            captured["messages"] = messages

    monkeypatch.setattr(chat_mod, "MemoryManager", _MM)
    chat_mod._enqueue_turn_mem0("user_x", "Gọi mình theo số 0912345678 nhé", "OK, mình ghi 0912345678")
    msgs = captured.get("messages")
    assert isinstance(msgs, list)
    blob = str(msgs)
    assert "0912345678" not in blob
    assert "[PHONE]" in blob


def test_build_fallback_plan_voice_script_differs_from_visible():
    # build_fallback_plan now generates its own visible_text; the key invariant
    # is that voice_script is non-empty and differs from visible_text.
    plan = build_fallback_plan("", session_sos_count=0, is_alone=False)
    assert plan.visible_text.strip()
    assert plan.voice_script.strip()
    assert plan.voice_script != plan.visible_text
