from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.routers import bamboo as bamboo_router
from app.api.deps import ensure_policy_acknowledged, get_admin_claims, enforce_admin_ip


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

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


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

    # inbox should now contain the message
    inbox = client_user.get("/v1/bamboo/inbox")
    assert inbox.status_code == 200
    assert any(m["message_id"] == msg_id for m in inbox.json()["data"]["messages"]) 


def test_reply_and_pass(client_user, client_admin):
    # send and approve a message first
    s = client_user.post("/v1/bamboo/send", json={"content": "For reply test"})
    msg_id = s.json()["data"]["message_id"]
    client_admin.patch(f"/v1/bamboo/moderation/{msg_id}", json={"status": "approved"})

    # reply
    r = client_user.post("/v1/bamboo/reply", json={"message_id": msg_id, "content": "Thanks!"})
    assert r.status_code == 201
    assert r.json()["data"]["message_id"] == msg_id

    # pass
    p = client_user.post("/v1/bamboo/pass", json={"message_id": msg_id})
    assert p.status_code == 200
    assert p.json()["data"]["message_id"] == msg_id
