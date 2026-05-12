"""Tests for persona unlock state, progression, and legacy boundary compatibility."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, select
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


def test_core_personas_always_unlocked(db):
    from app.personas.unlocks import is_persona_unlocked

    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="dung_luong") is True
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="dat_le") is True


def test_unlockable_persona_locked_by_default(db):
    from app.personas.unlocks import is_persona_unlocked

    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="hau_luong") is False


def test_mark_persona_unlocked(db):
    from app.personas.unlocks import is_persona_unlocked, mark_persona_unlocked

    mark_persona_unlocked(db, user_id="usr_unlock", persona_id="hau_luong", source="purchase")
    db.commit()
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="hau_luong") is True


def test_legacy_unlock_grants_hau_luong(db):
    from app.personas.unlocks import is_persona_unlocked, mark_persona_unlocked

    mark_persona_unlocked(db, user_id="usr_unlock", persona_id="crush", source="legacy_purchase")
    db.commit()
    assert is_persona_unlocked(db, user_id="usr_unlock", persona_id="hau_luong") is True


def test_boundary_intro_content():
    from app.personas.boundary_intro import BOUNDARY_INTRO_TEXT, build_boundary_intro_response

    resp = build_boundary_intro_response()
    assert resp["acceptance_required"] is False
    assert "Hậu" in BOUNDARY_INTRO_TEXT
    assert len(resp["key_points"]) >= 2


def test_accept_crush_boundary_sets_hau_flag(db):
    from app.personas.unlocks import accept_crush_boundary, get_persona_unlock_state

    accept_crush_boundary(db, user_id="usr_unlock")
    db.commit()
    state = get_persona_unlock_state(db, user_id="usr_unlock", persona_id="hau_luong")
    assert state is not None
    assert state.boundary_accepted is True
    assert state.unlocked is False


def test_progression_returns_hau_for_fresh_user(db):
    from app.personas.progression import get_unlock_progress

    progress = get_unlock_progress(db, user_id="usr_unlock", persona_id="hau_luong")
    assert progress["unlocked"] is False
    assert progress["price_hearts"] == 500
    assert progress["progress"] == {}


def test_active_persona_id_unlocked_persona_returns_it(db, monkeypatch):
    """After purchasing Hau, _active_persona_id should return Hau at safe distress."""
    from app.api.v1.routers.chat import _active_persona_id
    from app.personas.unlocks import mark_persona_unlocked

    mark_persona_unlocked(db, user_id="usr_unlock", persona_id="hau_luong", source="purchase")
    db.commit()

    from types import SimpleNamespace
    mock_profile = SimpleNamespace(profile={"persona": {"selected": "hau_luong"}})

    call_count = [0]

    def patched_scalar(stmt, *a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_profile
        engine = db.get_bind()
        with Session(engine) as s2:
            return s2.scalar(select(PersonaUnlockState).where(
                PersonaUnlockState.user_id == "usr_unlock",
                PersonaUnlockState.persona_id == "hau_luong",
            ))

    monkeypatch.setattr(db, "scalar", patched_scalar)
    result = _active_persona_id(db, "usr_unlock", distress=0.1)
    assert result == "hau_luong"
