"""Persona router integration tests — Batch 2.

Covers:
- route_persona() safety and unlock gates
- SOS bypass forces ban_than with safety_override
- _active_persona_id() wires route_persona() correctly
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.personas import route_persona
from app.personas.registry import DEFAULT_PERSONA_ID


# ---------------------------------------------------------------------------
# route_persona unit tests
# ---------------------------------------------------------------------------

def test_route_persona_keep_default():
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id=None,
        distress=0.1,
        sos_triggered=False,
    )
    assert decision.action == "keep"
    assert decision.target_persona_id == DEFAULT_PERSONA_ID
    assert decision.safety_override is False


def test_route_persona_sos_forces_ban_than_safety_override():
    decision = route_persona(
        current_persona_id="nguoi_thay",
        requested_persona_id=None,
        distress=0.95,
        sos_triggered=True,
    )
    assert decision.action in ("keep", "deactivate")
    assert decision.target_persona_id == DEFAULT_PERSONA_ID
    assert decision.safety_override is True


def test_route_persona_high_distress_deactivates_nguoi_thay():
    # nguoi_thay auto-deactivates at distress >= 0.70
    decision = route_persona(
        current_persona_id="nguoi_thay",
        requested_persona_id=None,
        distress=0.75,
        sos_triggered=False,
    )
    assert decision.action == "deactivate"
    assert decision.target_persona_id == DEFAULT_PERSONA_ID
    assert decision.safety_override is True


def test_route_persona_unlock_gate_blocks_cun():
    # cun is unlockable; without is_unlocked=True it must be rejected
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id="cun",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=False,
        user_explicit=True,
    )
    assert decision.action == "reject"
    assert decision.target_persona_id == DEFAULT_PERSONA_ID
    assert "locked" in decision.reason


def test_route_persona_switch_nguoi_thay_at_safe_distress():
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id="nguoi_thay",
        distress=0.3,
        sos_triggered=False,
        user_explicit=True,
    )
    assert decision.action == "switch"
    assert decision.target_persona_id == "nguoi_thay"
    assert decision.should_persist_preference is True


def test_route_persona_reject_unknown_id():
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id="ghost_persona",
        distress=0.0,
        sos_triggered=False,
    )
    assert decision.action == "reject"
    assert decision.target_persona_id == DEFAULT_PERSONA_ID


# ---------------------------------------------------------------------------
# _active_persona_id integration
# ---------------------------------------------------------------------------

def test_active_persona_id_returns_default_on_no_profile():
    """DB returning None profile should fall back to ban_than."""
    from app.api.v1.routers.chat import _active_persona_id

    mock_db = MagicMock()
    mock_db.scalar.return_value = None
    result = _active_persona_id(mock_db, "usr_test", distress=0.1)
    assert result == DEFAULT_PERSONA_ID


def test_active_persona_id_returns_validated_persona():
    """Profile with nguoi_thay + safe distress should yield nguoi_thay."""
    from app.api.v1.routers.chat import _active_persona_id

    mock_profile = SimpleNamespace(profile={"persona": {"selected": "nguoi_thay"}})
    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_profile
    result = _active_persona_id(mock_db, "usr_test", distress=0.2)
    assert result == "nguoi_thay"


def test_active_persona_id_safety_gate_overrides_at_high_distress():
    """Profile with nguoi_thay + distress >= 0.70 must return ban_than."""
    from app.api.v1.routers.chat import _active_persona_id

    mock_profile = SimpleNamespace(profile={"persona": {"selected": "nguoi_thay"}})
    mock_db = MagicMock()
    mock_db.scalar.return_value = mock_profile
    result = _active_persona_id(mock_db, "usr_test", distress=0.80)
    assert result == DEFAULT_PERSONA_ID


def test_active_persona_id_db_error_returns_default():
    """DB exception must fall back silently to ban_than."""
    from app.api.v1.routers.chat import _active_persona_id

    mock_db = MagicMock()
    mock_db.scalar.side_effect = Exception("connection lost")
    result = _active_persona_id(mock_db, "usr_test", distress=0.3)
    assert result == DEFAULT_PERSONA_ID


def test_route_persona_crush_rejects_without_boundary_accepted():
    """Crush must be rejected when boundary_accepted=False, even if unlocked."""
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id="crush",
        distress=0.1,
        sos_triggered=False,
        is_unlocked=True,
        boundary_accepted=False,
        user_explicit=True,
    )
    assert decision.action == "reject"
    assert decision.target_persona_id == DEFAULT_PERSONA_ID
    assert decision.blocked_reason == "crush_boundary_not_accepted"
