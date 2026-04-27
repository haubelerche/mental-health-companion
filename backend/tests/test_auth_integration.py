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
from app.db.models import User
from app.db.session import Base
from app.main import app


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
    Base.metadata.create_all(bind=engine)

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
