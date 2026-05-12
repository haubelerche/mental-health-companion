from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import auth as auth_router
from app.core.product_constants import CURRENT_POLICY_VERSION
from app.services.db.models import User
from app.services.db.session import Base
from app.services.utils import utc_now
from app.main import app


class _DummyAuthRateLimiter:
    """Avoid Redis-backed limits during integration tests (shared IP + shared Redis → flaky 429)."""

    def enforce_per_minute(self, *args: object, **kwargs: object) -> None:
        return

    def enforce_auth_lockout(self, *args: object, **kwargs: object) -> None:
        return

    def record_auth_failure(self, *args: object, **kwargs: object) -> None:
        return

    def clear_auth_failure(self, *args: object, **kwargs: object) -> None:
        return


@pytest.fixture(autouse=True)
def _disable_auth_router_rate_limit(monkeypatch):
    monkeypatch.setattr(auth_router, "get_rate_limiter", lambda: _DummyAuthRateLimiter())


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}@example.com"


def _stub_tokens(monkeypatch):
    monkeypatch.setattr(auth_router, "issue_access_token", lambda *_args, **_kwargs: "test-access-token")
    monkeypatch.setattr(auth_router, "generate_refresh_token", lambda: "test-refresh-token")
    monkeypatch.setattr(auth_router, "send_verification_email", lambda **_kwargs: None)


@pytest.fixture
def auth_test_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]
    Base.metadata.create_all(bind=engine, tables=tables_for_sqlite)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[auth_router.get_db] = override_db
    try:
        yield SessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_signup_auto_acknowledges_policy_version(monkeypatch, auth_test_db):
    _stub_tokens(monkeypatch)
    email = _unique_email("signup")
    with TestClient(app) as client:
        resp = client.post(
            "/v1/auth/signup",
            json={
                "display_name": "Signup User",
                "email": email,
                "password": "StrongPass#2026",
                "disclaimer_accepted": True,
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    user_id = body["data"]["user_id"]
    assert body["data"]["verification_required"] is True

    db = auth_test_db()
    try:
        user = db.scalar(select(User).where(User.user_id == user_id))
        assert user is not None
        assert user.policy_version_ack == CURRENT_POLICY_VERSION
        assert user.policy_acknowledged_at is not None
    finally:
        db.close()


def test_login_updates_legacy_policy_acknowledgement(monkeypatch, auth_test_db):
    _stub_tokens(monkeypatch)
    email = _unique_email("login")
    password = "StrongPass#2026"

    with TestClient(app) as client:
        signup_resp = client.post(
            "/v1/auth/signup",
            json={
                "display_name": "Login User",
                "email": email,
                "password": password,
                "disclaimer_accepted": True,
            },
        )
        assert signup_resp.status_code == 202
        user_id = signup_resp.json()["data"]["user_id"]

        db = auth_test_db()
        try:
            user = db.scalar(select(User).where(User.user_id == user_id))
            assert user is not None
            user.is_active = True
            user.policy_version_ack = "legacy"
            user.policy_acknowledged_at = None
            db.commit()
        finally:
            db.close()

        login_resp = client.post(
            "/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

    assert login_resp.status_code == 200
    db = auth_test_db()
    try:
        updated_user = db.scalar(select(User).where(User.user_id == user_id))
        assert updated_user is not None
        assert updated_user.policy_version_ack == CURRENT_POLICY_VERSION
        assert updated_user.policy_acknowledged_at is not None
    finally:
        db.close()


def test_signup_local_fallback_auto_verifies_when_smtp_missing(monkeypatch, auth_test_db):
    _stub_tokens(monkeypatch)
    settings_override = auth_router.get_settings().model_copy(update={"auto_create_schema": True})
    monkeypatch.setattr(auth_router, "get_settings", lambda: settings_override)
    monkeypatch.setattr(auth_router, "send_verification_email", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("SMTP missing")))
    email = _unique_email("signup_local_fallback")

    with TestClient(app) as client:
        resp = client.post(
            "/v1/auth/signup",
            json={
                "display_name": "Local Fallback User",
                "email": email,
                "password": "StrongPass#2026",
                "disclaimer_accepted": True,
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["verification_required"] is False
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie_header
    assert "refresh_token=" in set_cookie_header

    db = auth_test_db()
    try:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.is_active is True
        assert user.email_verified_at is not None
    finally:
        db.close()


def test_me_persona_hau_and_alias_locked_without_store_unlock(monkeypatch, auth_test_db):
    # Real JWT access tokens so `get_current_user` + `/me/persona` work under TestClient cookies.
    monkeypatch.setattr(auth_router, "generate_refresh_token", lambda: "test-refresh-token")
    monkeypatch.setattr(auth_router, "send_verification_email", lambda **_kwargs: None)
    email = _unique_email("persona_hau_lock")
    password = "StrongPass#2026"
    with TestClient(app) as client:
        signup_resp = client.post(
            "/v1/auth/signup",
            json={
                "display_name": "Persona Lock User",
                "email": email,
                "password": password,
                "disclaimer_accepted": True,
            },
        )
        assert signup_resp.status_code == 202
        user_id = signup_resp.json()["data"]["user_id"]

        db = auth_test_db()
        try:
            user = db.scalar(select(User).where(User.user_id == user_id))
            assert user is not None
            user.is_active = True
            user.email_verified_at = utc_now().replace(tzinfo=None)
            db.commit()
        finally:
            db.close()

        assert client.post("/v1/auth/login", json={"email": email, "password": password}).status_code == 200
        csrf = client.get("/v1/auth/csrf-token").json()["data"]["csrf_token"]
        hau_resp = client.post(
            "/v1/auth/me/persona",
            json={"persona_id": "hau_luong"},
            headers={"X-CSRF-Token": csrf},
        )
        assert hau_resp.status_code == 403
        assert hau_resp.json()["error"]["code"] == "persona_locked"

        alias_resp = client.post(
            "/v1/auth/me/persona",
            json={"persona_id": "nguoi_yeu"},
            headers={"X-CSRF-Token": csrf},
        )
        assert alias_resp.status_code == 403
        assert alias_resp.json()["error"]["code"] == "persona_locked"

        ok_resp = client.post(
            "/v1/auth/me/persona",
            json={"persona_id": "ban_than"},
            headers={"X-CSRF-Token": csrf},
        )
        assert ok_resp.status_code == 200
        assert ok_resp.json()["data"]["persona_id"] == "dung_luong"
        me_resp = client.get("/v1/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["persona_id"] == "dung_luong"


def test_me_persona_unknown_returns_400(monkeypatch, auth_test_db):
    monkeypatch.setattr(auth_router, "generate_refresh_token", lambda: "test-refresh-token")
    monkeypatch.setattr(auth_router, "send_verification_email", lambda **_kwargs: None)
    email = _unique_email("persona_unknown")
    password = "StrongPass#2026"
    with TestClient(app) as client:
        signup_resp = client.post(
            "/v1/auth/signup",
            json={
                "display_name": "U2",
                "email": email,
                "password": password,
                "disclaimer_accepted": True,
            },
        )
        assert signup_resp.status_code == 202
        user_id = signup_resp.json()["data"]["user_id"]

        db = auth_test_db()
        try:
            user = db.scalar(select(User).where(User.user_id == user_id))
            assert user is not None
            user.is_active = True
            user.email_verified_at = utc_now().replace(tzinfo=None)
            db.commit()
        finally:
            db.close()

        assert client.post("/v1/auth/login", json={"email": email, "password": password}).status_code == 200
        csrf = client.get("/v1/auth/csrf-token").json()["data"]["csrf_token"]
        unk = client.post(
            "/v1/auth/me/persona",
            json={"persona_id": "nguoi_la"},
            headers={"X-CSRF-Token": csrf},
        )
        assert unk.status_code == 400
        assert unk.json()["error"]["code"] == "persona_unknown"
