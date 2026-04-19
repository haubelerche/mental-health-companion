from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.routers import safety as safety_router
from app.main import app


def _override_user():
    return SimpleNamespace(user_id="usr_safety")


class _Db:
    pass


def test_safety_escalate_legal_gate_off(monkeypatch):
    monkeypatch.setattr(safety_router, "get_settings", lambda: SimpleNamespace(trusted_contact_outbound_enabled=False))
    monkeypatch.setattr(safety_router, "list_trusted_contacts", lambda *_args, **_kwargs: [{"name": "A", "phone": "0123"}])
    monkeypatch.setattr(safety_router, "get_outbound_opt_in", lambda *_args, **_kwargs: True)

    def override_db():
        yield _Db()

    app.dependency_overrides[safety_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[safety_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/v1/safety/escalate",
                json={"session_id": "sess_1", "risk_level": 5, "reason": "high_risk_detected"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["queued"] is False
        assert body["data"]["legal_gate_enabled"] is False
    finally:
        app.dependency_overrides.clear()


def test_safety_escalate_queues_when_enabled(monkeypatch):
    monkeypatch.setattr(safety_router, "get_settings", lambda: SimpleNamespace(trusted_contact_outbound_enabled=True))
    monkeypatch.setattr(safety_router, "list_trusted_contacts", lambda *_args, **_kwargs: [{"name": "A", "phone": "0123"}])
    monkeypatch.setattr(safety_router, "get_outbound_opt_in", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(safety_router, "enqueue_trusted_contact_notification", lambda *_args, **_kwargs: 999)

    def override_db():
        yield _Db()

    app.dependency_overrides[safety_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[safety_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/v1/safety/escalate",
                json={"session_id": "sess_1", "risk_level": 5, "reason": "high_risk_detected"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["queued"] is True
        assert body["data"]["outbox_id"] == 999
    finally:
        app.dependency_overrides.clear()
