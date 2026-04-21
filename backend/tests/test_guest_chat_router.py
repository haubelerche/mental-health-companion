from fastapi.testclient import TestClient

from app.api.v1.routers import chat as chat_router
from app.main import app
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
