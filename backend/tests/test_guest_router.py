from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.product_constants import GUEST_TRIAL_MAX_DURATION_SEC
from app.main import app


def test_guest_session_start_returns_backend_ttl():
    with TestClient(app) as client:
        token_resp = client.get("/v1/auth/csrf-token")
        assert token_resp.status_code == 200
        csrf_token = token_resp.json()["data"]["csrf_token"]

        resp = client.post("/v1/guest/session/start", headers={"X-CSRF-Token": csrf_token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"]["guest_session_id"], str)
    assert body["data"]["guest_session_id"].startswith("gst_")
    assert body["data"]["max_duration_sec"] == GUEST_TRIAL_MAX_DURATION_SEC
