from fastapi.testclient import TestClient

from app.api import deps as api_deps
from app.api.v1.routers import chat as chat_router
from app.core.product_constants import GUEST_TRIAL_MAX_DURATION_SEC
from app.main import app
from app.services import guest_service
from app.services.safety_scoring import SafetySnapshot


def _post_guest_message(client: TestClient, payload: dict):
    token_resp = client.get("/v1/auth/csrf-token")
    assert token_resp.status_code == 200
    csrf_token = token_resp.json()["data"]["csrf_token"]
    return client.post("/v1/chat/guest-message", json=payload, headers={"X-CSRF-Token": csrf_token})


def test_guest_chat_message_starts_session(monkeypatch):
    monkeypatch.setattr(chat_router, "guest_start_session", lambda: ("gst_123", 120))
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: {
            "session_fields": SafetySnapshot(
                distress_score=0.2,
                risk_level=1,
                safety_tier="normal",
                conversation_mode="normal",
            ),
            "reply": "Mình ở đây với bạn.",
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
            "routing_history": ["supervisor", "friend"],
        },
    )

    with TestClient(app) as client:
        resp = _post_guest_message(client, {"message": "chao"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["session_id"] == "gst_123"
    assert body["data"]["sos_triggered"] is False


def test_guest_chat_message_blocks_expired_trial(monkeypatch):
    monkeypatch.setattr(chat_router, "guest_heartbeat", lambda _sid: False)

    with TestClient(app) as client:
        resp = _post_guest_message(client, {"message": "cho minh noi tiep", "guest_session_id": "gst_expired"})

    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "GUEST_TRIAL_EXPIRED"


def test_guest_chat_message_allows_loopback_origin_on_different_port(monkeypatch):
    monkeypatch.setattr(chat_router, "guest_start_session", lambda: ("gst_123", 120))
    monkeypatch.setattr(chat_router, "decide_sos", lambda *_args, **_kwargs: (False, 0.1))
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: {
            "session_fields": SafetySnapshot(
                distress_score=0.1,
                risk_level=0,
                safety_tier="normal",
                conversation_mode="normal",
            ),
            "reply": "ok",
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
            "routing_history": [],
        },
    )
    monkeypatch.setattr(
        api_deps,
        "get_settings",
        lambda: type("S", (), {"csrf_trusted_origins": "http://localhost:5173"})(),
    )

    with TestClient(app) as client:
        token_resp = client.get("/v1/auth/csrf-token")
        assert token_resp.status_code == 200
        csrf_token = token_resp.json()["data"]["csrf_token"]
        resp = client.post(
            "/v1/chat/guest-message",
            json={"message": "hello"},
            headers={"X-CSRF-Token": csrf_token, "Origin": "http://localhost:5174"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_guest_chat_message_expires_after_backend_trial_duration(monkeypatch):
    fake_now = {"ts": 1_700_000_000.0}
    monkeypatch.setattr(guest_service, "get_redis", lambda: None)
    monkeypatch.setattr(guest_service, "_now", lambda: fake_now["ts"])
    guest_service._FALLBACK.clear()
    monkeypatch.setattr(chat_router, "decide_sos", lambda *_args, **_kwargs: (False, 0.12))
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: {
            "session_fields": SafetySnapshot(
                distress_score=0.12,
                risk_level=0,
                safety_tier="normal",
                conversation_mode="normal",
            ),
            "reply": "ok",
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
            "routing_history": [],
        },
    )

    with TestClient(app) as client:
        token_resp = client.get("/v1/auth/csrf-token")
        assert token_resp.status_code == 200
        csrf_token = token_resp.json()["data"]["csrf_token"]

        start_resp = client.post("/v1/guest/session/start", headers={"X-CSRF-Token": csrf_token})
        assert start_resp.status_code == 200
        guest_session_id = start_resp.json()["data"]["guest_session_id"]

        alive_resp = _post_guest_message(client, {"message": "chao", "guest_session_id": guest_session_id})
        assert alive_resp.status_code == 200

        fake_now["ts"] += GUEST_TRIAL_MAX_DURATION_SEC + 1
        expired_resp = _post_guest_message(client, {"message": "cho minh tiep tuc", "guest_session_id": guest_session_id})

    assert expired_resp.status_code == 403
    body = expired_resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "GUEST_TRIAL_EXPIRED"
