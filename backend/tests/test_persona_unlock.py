"""Tests for persona unlock state, progression, and boundary intro.

Also verifies _active_persona_id() uses real unlock state (not hardcoded False).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.services.db.models import PersonaUnlockState, User
from app.services.db.session import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(engine, tables=tables_for_sqlite)
    with Session(engine) as session:
        session.add(User(user_id="usr_unlock", display_name="U", email="u@test.com",
                          password_hash="x", is_active=True))
        session.commit()
        yield session
    Base.metadata.drop_all(engine, tables=tables_for_sqlite)


# ---------------------------------------------------------------------------
# is_persona_unlocked
# ---------------------------------------------------------------------------

def test_core_personas_always_unlocked(db):
    from app.personas.unlocks import is_persona_unlocked
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="ban_than") is True
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="nguoi_thay") is True


def test_unlockable_persona_locked_by_default(db):
    from app.personas.unlocks import is_persona_unlocked
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="cun") is False
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="meo") is False
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="crush") is False


def test_mark_persona_unlocked(db):
    from app.personas.unlocks import is_persona_unlocked, mark_persona_unlocked
    mark_persona_unlocked(db, user_id="usr_unlock", persona_id="cun", source="purchase")
    db.commit()
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="cun") is True


# ---------------------------------------------------------------------------
# Crush boundary intro
# ---------------------------------------------------------------------------

def test_boundary_intro_content():
    from app.personas.boundary_intro import BOUNDARY_INTRO_TEXT, build_boundary_intro_response
    resp = build_boundary_intro_response()
    assert resp["acceptance_required"] is True
    assert "người yêu thật" not in BOUNDARY_INTRO_TEXT or "không phải" in BOUNDARY_INTRO_TEXT
    assert len(resp["key_points"]) >= 3


def test_accept_crush_boundary_sets_flag(db):
    from app.personas.unlocks import accept_crush_boundary, get_persona_unlock_state
    accept_crush_boundary(db, user_id="usr_unlock")
    db.commit()
    state = get_persona_unlock_state(db, user_id="usr_unlock", persona_id="crush")
    assert state is not None
    assert state.boundary_accepted is True
    assert state.unlocked is False  # boundary acceptance alone doesn't unlock


# ---------------------------------------------------------------------------
# Progression aggregation
# ---------------------------------------------------------------------------

def test_progression_returns_unmet_for_fresh_user(db):
    from app.personas.progression import get_unlock_progress
    progress = get_unlock_progress(db, user_id="usr_unlock", persona_id="cun")
    assert progress["unlocked"] is False
    assert progress["progress"]["mood_checkins"]["current"] == 0
    assert progress["progress"]["mood_checkins"]["met"] is False


# ---------------------------------------------------------------------------
# _active_persona_id uses unlock state
# ---------------------------------------------------------------------------

def test_active_persona_id_unlocked_persona_returns_it(db, monkeypatch):
    """After purchasing cun, _active_persona_id should return cun at safe distress."""
    from app.personas.unlocks import mark_persona_unlocked
    from app.api.v1.routers.chat import _active_persona_id

    mark_persona_unlocked(db, user_id="usr_unlock", persona_id="cun", source="purchase")
    db.commit()

    from types import SimpleNamespace
    mock_profile = SimpleNamespace(profile={"persona": {"selected": "cun"}})
    monkeypatch.setattr(db, "scalar", lambda *a, **kw: mock_profile)

    # After monkeypatching scalar globally we need a real is_persona_unlocked call
    # so restore it just for that call:
    from app.personas import unlocks as unlocks_mod
    orig_scalar = db.scalar

    call_count = [0]
    def patched_scalar(stmt, *a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_profile
        # second call is is_persona_unlocked (select PersonaUnlockState)
        from sqlalchemy.orm import Session as _S
        engine = db.get_bind()
        with _S(engine) as s2:
            from app.services.db.models import PersonaUnlockState
            from sqlalchemy import select
            return s2.scalar(select(PersonaUnlockState).where(
                PersonaUnlockState.user_id == "usr_unlock",
                PersonaUnlockState.persona_id == "cun",
            ))

    monkeypatch.setattr(db, "scalar", patched_scalar)
    result = _active_persona_id(db, "usr_unlock", distress=0.1)
    assert result == "cun"
