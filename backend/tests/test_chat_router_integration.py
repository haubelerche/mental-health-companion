from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.routers import chat as chat_router
from app.main import app
from app.services.safety_scoring import SafetySnapshot


class DummyLimiter:
    def enforce_per_minute(self, **_: object) -> None:
        return


class FakeDB:
    def __init__(self) -> None:
        self.items: list[object] = []
        self.committed = False

    def add(self, item: object) -> None:
        self.items.append(item)

    def flush(self) -> None:
        return

    def commit(self) -> None:
        self.committed = True


def _override_user():
    return SimpleNamespace(user_id="usr_test")


def test_chat_message_non_sos_success(monkeypatch):
    fake_db = FakeDB()
    captured: dict[str, object] = {}
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        chat_router,
        "get_user_longterm_memories",
        lambda *_args, **_kwargs: ["Lần trước bạn mất ngủ vì deadline.", "Bạn từng thấy đỡ hơn khi đi bộ ngắn."],
    )
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    def fake_turn(**kwargs):
        captured.update(kwargs)
        return {
            "session_fields": SafetySnapshot(
                distress_score=0.15,
                risk_level=0,
                safety_tier="normal",
                conversation_mode="normal",
            ),
            "reply": "Mình luôn ở đây với cậu.",
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": ["Cậu cứ kể đi", "Mình đang nghe", "Cần giúp gì nữa không"],
            "the_dinh_kem": [],
        }

    monkeypatch.setattr(chat_router, "run_non_sos_turn", fake_turn)

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "chao cau"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["sos_triggered"] is False
        assert body["data"]["reply"] == "Mình luôn ở đây với cậu."
        assert captured["long_term_memories"] == []
        assert fake_db.committed is True
    finally:
        app.dependency_overrides.clear()


def test_chat_message_sos_skips_graph(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chat_router, "get_user_longterm_memories", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (True, 0.95))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "get_or_create_clinical_profile",
        lambda _db, _user_id: SimpleNamespace(crisis_level=0, last_scored_at=None),
    )
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("graph should not run for SOS")),
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "Tôi muốn tự tử"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["sos_triggered"] is True
        assert fake_db.committed is True
    finally:
        app.dependency_overrides.clear()


def test_chat_message_non_sos_triggers_proactive_voice(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.72))
    monkeypatch.setattr(chat_router, "get_user_longterm_memories", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(chat_router, "cooldown_active", lambda **_kwargs: (False, 0))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[{"role": "user", "content": "Minh qua met"}], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "compute_escalation_signal",
        lambda **_kwargs: SimpleNamespace(escalate=True, trigger_reason="threshold_crossed", rolling_window_turns=4, delta_score=0.31),
    )
    monkeypatch.setattr(
        chat_router,
        "_build_voice_intervention",
        lambda **_kwargs: {"type": "proactive_voice", "voice": {"tts_job_id": "tts_100", "status": "queued"}},
    )
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: {
            "session_fields": SafetySnapshot(
                distress_score=0.92,
                risk_level=5,
                safety_tier="critical",
                conversation_mode="supportive",
            ),
            "reply": "Mình luôn ở đây với cậu.",
            "tone_cam_xuc": "lam_diu",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
        },
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "Minh qua ap luc, can duoc lang nghe"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["intervention"]["type"] == "proactive_voice"
        assert body["data"]["intervention"]["voice"]["tts_job_id"] == "tts_100"
    finally:
        app.dependency_overrides.clear()


def test_chat_message_triggers_voice_when_graph_raises_distress(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.72))
    monkeypatch.setattr(chat_router, "get_user_longterm_memories", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(chat_router, "cooldown_active", lambda **_kwargs: (False, 0))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    captured: dict[str, object] = {}

    def fake_voice_intervention(**kwargs):
        captured.update(kwargs)
        return {"type": "proactive_voice", "voice": {"tts_job_id": "tts_101", "status": "queued"}}

    monkeypatch.setattr(chat_router, "_build_voice_intervention", fake_voice_intervention)
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: {
            "session_fields": SafetySnapshot(
                distress_score=0.92,
                risk_level=5,
                safety_tier="critical",
                conversation_mode="supportive",
            ),
            "reply": "Mình luôn ở đây với cậu.",
            "tone_cam_xuc": "lam_diu",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
        },
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "Minh dang rat qua tai"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["intervention"]["type"] == "proactive_voice"
        assert captured["snapshot"].distress_score == 0.92
    finally:
        app.dependency_overrides.clear()


def test_chat_message_stream_returns_sse(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(chat_router, "decide_sos", lambda *_args, **_kwargs: (False, 0.2))
    monkeypatch.setattr(chat_router, "get_cached_turn", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_router, "set_cached_turn", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "stream_non_sos_turn_events",
        lambda **_kwargs: iter(
            [
                {"type": "token", "text": "Mình đang "},
                {
                    "type": "final",
                    "turn": {
                        "session_fields": SafetySnapshot(
                            distress_score=0.2,
                            risk_level=0,
                            safety_tier="normal",
                            conversation_mode="normal",
                        ),
                        "reply": "Mình đang ở đây cùng bạn nhé.",
                        "tone_cam_xuc": "xac_nhan",
                        "goi_y_nhanh": [],
                        "the_dinh_kem": [],
                        "routing_history": ["supervisor", "friend"],
                    },
                },
            ]
        ),
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message/stream", json={"message": "chao"})
        assert resp.status_code == 200
        assert "event: status" in resp.text
        assert "event: final" in resp.text
        assert "Mình đang ở đây cùng bạn nhé." in resp.text
    finally:
        app.dependency_overrides.clear()
