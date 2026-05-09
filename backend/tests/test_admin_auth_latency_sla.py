from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.routers import admin as admin_router
from app.main import app
from app.services.auth_latency_metrics import observe_auth_latency, reset_auth_latency_metrics
from app.services.db.session import get_db
from app.api.deps import get_admin_claims


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commits += 1


def test_admin_auth_latency_sla_returns_login_and_signup_snapshots(monkeypatch):
    reset_auth_latency_metrics()
    for value in [420.0, 500.0, 610.0, 700.0]:
        observe_auth_latency(flow="login", duration_ms=value, success=True)
    for value in [900.0, 1100.0, 1500.0, 1700.0]:
        observe_auth_latency(flow="signup", duration_ms=value, success=True)

    fake_db = _FakeDb()
    from app.api.v1.routers.admin import auth as admin_auth_module
    monkeypatch.setattr(admin_auth_module, "enforce_admin_ip", lambda _request: None)

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_admin_claims] = lambda: {"sub": "adm_test"}
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/admin/auth/latency-sla")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["login"]["window"] >= 4
        assert body["data"]["login"]["p95_ms"] >= 700.0
        assert body["data"]["signup"]["window"] >= 4
        assert body["data"]["signup"]["p95_ms"] >= 1700.0
        assert body["data"]["signup"]["within_sla"] is False
        assert fake_db.commits == 1
    finally:
        app.dependency_overrides.clear()
