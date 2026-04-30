from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.v1.routers import bamboo as bamboo_router
from app.api.deps import ensure_policy_acknowledged, get_admin_claims, enforce_admin_ip
from app.db.session import Base, get_db
from app.db.models import User
from datetime import datetime


@pytest.fixture
def client_no_auth():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_user(monkeypatch):
    # stub user dependency to simulate logged-in policy-acknowledged user
    fake_user = SimpleNamespace(user_id="usr_test", policy_acknowledged_at="2026-04-29T00:00:00Z")

    def _stub_user():
        return fake_user

    app.dependency_overrides[ensure_policy_acknowledged] = _stub_user

    # also override DB to use in-memory for isolation
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    # seed two users: the sender and an alternate recipient
    sess = SessionLocal()
    try:
        u1 = User(
            user_id="usr_test",
            display_name="Test User",
            email="usr_test@example.com",
            password_hash="x",
            disclaimer_accepted=True,
            is_active=True,
            policy_acknowledged_at=datetime.utcnow(),
        )
        u2 = User(
            user_id="other_user",
            display_name="Other User",
            email="other@example.com",
            password_hash="x",
            disclaimer_accepted=True,
            is_active=True,
            policy_acknowledged_at=datetime.utcnow(),
        )
        sess.add_all([u1, u2])
        sess.commit()
    finally:
        sess.close()

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client_admin(monkeypatch):
    # stub admin checks
    def _stub_admin_claims():
        return {"sub": "admin_1", "role": "admin", "scope": "admin_only"}

    def _noop_enforce(request=None):
        return None

    app.dependency_overrides[get_admin_claims] = _stub_admin_claims
    app.dependency_overrides[enforce_admin_ip] = _noop_enforce

    # also stub user so admin can act
    app.dependency_overrides[ensure_policy_acknowledged] = lambda: SimpleNamespace(user_id="admin_1")

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_send_requires_auth(client_no_auth):
    resp = client_no_auth.post("/v1/bamboo/send", json={"content": "hello"})
    # CSRF check runs before auth for POST requests; expect 403 when CSRF missing
    assert resp.status_code == 403


def test_send_and_approve_flow(client_user, client_admin):
    # send
    resp = client_user.post("/v1/bamboo/send", json={"content": "Test letter", "topic": "encouragement"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    msg_id = body["data"]["message_id"]

    # storage should include the pending message for owner
    st = client_user.get("/v1/bamboo/storage")
    assert st.status_code == 200
    assert any(item["message_id"] == msg_id for item in st.json()["data"]["letters"])

    # owner can view pending
    detail = client_user.get(f"/v1/bamboo/letters/{msg_id}")
    assert detail.status_code == 200

    # admin approves
    patch = client_admin.patch(f"/v1/bamboo/moderation/{msg_id}", json={"status": "approved"})
    assert patch.status_code == 200
    assert patch.json()["data"]["status"] == "approved"

    # storage should still include the message for owner; moderation should indicate recipient assignment
    inbox = client_user.get("/v1/bamboo/inbox")
    assert inbox.status_code == 200
    patch_data = patch.json()["data"]
    assert "recipient_id" in patch_data
    # owner storage still shows the message
    st2 = client_user.get("/v1/bamboo/storage")
    assert any(item["message_id"] == msg_id for item in st2.json()["data"]["letters"]) 


def test_reply_and_pass(client_user, client_admin):
    # send and approve a message first
    s = client_user.post("/v1/bamboo/send", json={"content": "For reply test"})
    msg_id = s.json()["data"]["message_id"]
    client_admin.patch(f"/v1/bamboo/moderation/{msg_id}", json={"status": "approved"})

    # switch auth context to the assigned recipient for recipient-only actions
    app.dependency_overrides[ensure_policy_acknowledged] = lambda: SimpleNamespace(
        user_id="other_user", policy_acknowledged_at="2026-04-29T00:00:00Z"
    )

    # reply
    r = client_user.post("/v1/bamboo/reply", json={"message_id": msg_id, "content": "Thanks!"})
    assert r.status_code == 201
    assert r.json()["data"]["message_id"] == msg_id

    # pass
    p = client_user.post("/v1/bamboo/pass", json={"message_id": msg_id})
    assert p.status_code == 200
    assert p.json()["data"]["message_id"] == msg_id
    assert "new_recipient" not in p.json()["data"]


def test_grouped_inboxes_and_thread_messages(client_user, client_admin):
    first = client_user.post("/v1/bamboo/send", json={"content": "Hello inbox A"})
    second = client_user.post("/v1/bamboo/send", json={"content": "Hello inbox B"})
    first_id = first.json()["data"]["message_id"]
    second_id = second.json()["data"]["message_id"]

    client_admin.patch(f"/v1/bamboo/moderation/{first_id}", json={"status": "approved"})
    client_admin.patch(f"/v1/bamboo/moderation/{second_id}", json={"status": "approved"})

    inboxes_resp = client_user.get("/v1/bamboo/inboxes")
    assert inboxes_resp.status_code == 200
    payload = inboxes_resp.json()["data"]
    assert payload["total"] >= 1
    first_inbox = payload["inboxes"][0]
    assert "inbox_id" in first_inbox
    assert "message_count" in first_inbox
    assert "display_name" in first_inbox
    assert "user_id" not in first_inbox
    assert "recipient_id" not in first_inbox

    thread_resp = client_user.get(f"/v1/bamboo/inboxes/{first_inbox['inbox_id']}/messages")
    assert thread_resp.status_code == 200
    thread_payload = thread_resp.json()["data"]
    assert thread_payload["inbox"]["inbox_id"] == first_inbox["inbox_id"]
    assert isinstance(thread_payload["messages"], list)
    if thread_payload["messages"]:
        assert "direction" in thread_payload["messages"][0]
