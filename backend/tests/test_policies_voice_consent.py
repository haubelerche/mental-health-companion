from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.routers import policies as policies_router
from app.main import app


class _Db:
    pass


def _override_user():
    return SimpleNamespace(user_id="usr_policy")


def test_voice_consent_get_endpoint(monkeypatch):
    monkeypatch.setattr(policies_router, "get_voice_consent", lambda _db, _uid: True)

    def override_db():
        yield _Db()

    app.dependency_overrides[policies_router.get_current_user] = _override_user
    app.dependency_overrides[policies_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/policies/voice-consent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["voice_consent"] is True
    finally:
        app.dependency_overrides.clear()


def test_voice_consent_set_endpoint(monkeypatch):
    monkeypatch.setattr(policies_router, "set_voice_consent", lambda _db, _uid, consent: consent)

    def override_db():
        yield _Db()

    app.dependency_overrides[policies_router.get_current_user] = _override_user
    app.dependency_overrides[policies_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post("/v1/policies/voice-consent", json={"consent": False})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["voice_consent"] is False
    finally:
        app.dependency_overrides.clear()
