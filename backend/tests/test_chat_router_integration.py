from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.routers import chat as chat_router
from app.main import app
from app.services.latency_metrics import CHAT_LATENCY_INT_STAGES
from app.services.memory_recall import RecallReply
from app.services.safety_scoring import SafetySnapshot


FORBIDDEN_NORMAL_CHAT_FIELDS = {
    "agent_display_name",
    "conversation_mode",
    "voice_session_offered",
    "suggest_voice",
    "voice_hint",
    "emergency_actions",
    "assistant_tone",
    "goi_y_nhanh",
    "the_dinh_kem",
    "routing_history",
    "voice_policy",
    "intervention",
    "distress_score",
    "safety_tier",
}


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
        for item in self.items:
            if hasattr(item, "outbox_id") and getattr(item, "outbox_id", None) is None:
                item.outbox_id = 1

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def scalar(self, *_args, **_kwargs):
        return 0


class StreamFakeDB(FakeDB):
    """Fake session for chat stream tests (post-LLM refetch loads Conversation from items)."""

    def scalar(self, *_args, **_kwargs):
        from app.services.db.models import Conversation

        for item in reversed(self.items):
            if isinstance(item, Conversation):
                return item
        return super().scalar()


def _override_user():
    return SimpleNamespace(user_id="usr_test")


def _override_stream_user():
    return SimpleNamespace(user_id="usr_test", policy_acknowledged_at="2025-01-01T00:00:00")


def test_chat_message_non_sos_success(monkeypatch):
    fake_db = FakeDB()
    legacy_called = {"value": False}
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: legacy_called.__setitem__("value", True),
    )

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
        assert body["data"]["assistant_text"] == body["data"]["reply"]
        assert body["data"]["route_tier"] == "fast"
        assert isinstance(body["data"]["message_id"], str)
        assert body["data"]["used_advisor_ids"] == []
        assert body["data"]["resource_suggestions"] == []
        assert body["data"]["nutrition_suggestion"] is None
        assert body["data"]["tts_job"] is None
        assert FORBIDDEN_NORMAL_CHAT_FIELDS.isdisjoint(body["data"])
        assert "latency_trace" in body["data"]
        assert "total_backend_ms" in body["data"]["latency_trace"]
        for stage in CHAT_LATENCY_INT_STAGES:
            assert stage in body["data"]["latency_trace"]
        assert legacy_called["value"] is False
        assert fake_db.committed is True
    finally:
        app.dependency_overrides.clear()


def test_chat_message_recall_skips_langgraph_and_uses_memory_handler(monkeypatch):
    fake_db = FakeDB()
    graph_called = {"value": False}
    persisted = {"value": False}
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.12))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "try_handle_memory_recall_turn",
        lambda *_args, **_kwargs: RecallReply(
            turn_kind="identity_recall",
            reply="Có. Mình nhớ cậu là AI engineer của Serene AI.",
            memory_source_counts={"visible_memories": 1},
            active_memory_text="- AI engineer của Serene AI",
        ),
    )
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: graph_called.__setitem__("value", True),
    )
    monkeypatch.setattr(
        chat_router,
        "persist_turn_memory",
        lambda *_args, **_kwargs: persisted.__setitem__("value", True),
    )
    monkeypatch.setattr(chat_router, "_enqueue_turn_mem0", lambda *_args, **_kwargs: None)

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "cậu có nhớ tôi là ai không?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "AI engineer" in body["data"]["assistant_text"]
        assert "deadline" not in body["data"]["assistant_text"].lower()
        assert graph_called["value"] is False
        assert persisted["value"] is True
        assert fake_db.committed is True
    finally:
        app.dependency_overrides.clear()


def test_chat_message_sos_skips_graph(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
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
            resp = client.post("/v1/chat/message", json={"message": "TÃ´i muá»‘n tá»± tá»­"})
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

    def fake_enqueue_voice_policy(**_kwargs):
        return {
            "voice_policy": {
                "should_attach_voice": True,
                "risk_mode": "elevated_encouragement",
                "ordinary_cooldown_bypassed": False,
                "reason_codes": [],
                "voice_messages": [],
            },
            "intervention": {
                "type": "proactive_voice",
                "voice": {"tts_job_id": "tts_100", "status": "queued"},
            },
        }

    monkeypatch.setattr(chat_router, "_enqueue_voice_policy", fake_enqueue_voice_policy)
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
            "reply": "MÃ¬nh luÃ´n á»Ÿ Ä‘Ã¢y vá»›i cáº­u.",
            "assistant_tone": "calming",
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
        assert body["data"]["tts_job"]["tts_job_id"] == "tts_100"
        assert "intervention" not in body["data"]
        assert "voice_policy" not in body["data"]
    finally:
        app.dependency_overrides.clear()


def test_chat_message_triggers_voice_when_graph_raises_distress(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.72))
    monkeypatch.setattr(chat_router, "get_user_longterm_memories", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat_router, "cooldown_active", lambda **_kwargs: (False, 0))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    captured: dict[str, object] = {}

    def fake_enqueue_voice_policy(**kwargs):
        captured["snap"] = kwargs.get("snap")
        return {
            "voice_policy": {
                "should_attach_voice": True,
                "risk_mode": "elevated_encouragement",
                "ordinary_cooldown_bypassed": False,
                "reason_codes": [],
                "voice_messages": [],
            },
            "intervention": {
                "type": "proactive_voice",
                "voice": {"tts_job_id": "tts_101", "status": "queued"},
            },
        }

    monkeypatch.setattr(chat_router, "_enqueue_voice_policy", fake_enqueue_voice_policy)
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
        assert body["data"]["tts_job"]["tts_job_id"] == "tts_101"
        assert "intervention" not in body["data"]
        assert captured["snap"] is not None
    finally:
        app.dependency_overrides.clear()


def test_chat_message_voice_enqueue_failure_does_not_break_turn(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.72))
    monkeypatch.setattr(chat_router, "get_user_longterm_memories", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat_router, "cooldown_active", lambda **_kwargs: (False, 0))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "compute_escalation_signal",
        lambda **_kwargs: SimpleNamespace(escalate=True, trigger_reason="threshold_crossed", rolling_window_turns=4, delta_score=0.31),
    )
    monkeypatch.setattr(
        chat_router,
        "_enqueue_voice_policy",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("queue down")),
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
            "reply": "OK.",
            "assistant_tone": "calming",
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
        assert body["data"]["assistant_text"]
        assert body["data"]["tts_job"] is None
    finally:
        app.dependency_overrides.clear()


def test_chat_message_stream_returns_sse(monkeypatch):
    fake_db = StreamFakeDB()

    def _fake_session_factory():
        return fake_db

    monkeypatch.setattr(chat_router, "get_session_factory", lambda: _fake_session_factory)
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(chat_router, "decide_sos", lambda *_args, **_kwargs: (False, 0.2))
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(chat_router, "_active_persona_id", lambda *_a, **_k: "dung_luong")
    monkeypatch.setattr(chat_router, "_load_today_meals", lambda *_a, **_k: [])
    monkeypatch.setattr(chat_router, "get_voice_consent", lambda *_a, **_k: True)

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[deps.ensure_policy_acknowledged_for_stream] = _override_stream_user
    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message/stream", json={"message": "chao"})
        assert resp.status_code == 200
        assert "event: status" in resp.text
        assert "event: final" in resp.text
        assert "\"assistant_text\":" in resp.text
        assert "\"route_tier\": \"fast\"" in resp.text
        assert "\"used_advisor_ids\": []" in resp.text
        assert "\"nutrition_suggestion\": null" in resp.text
        assert "\"latency_trace\":" in resp.text
        for stage in ("total_backend_ms", "advisor_consult_ms", "safety_output_validator_ms"):
            assert f"\"{stage}\":" in resp.text
        assert "\"distress_score\"" not in resp.text
        assert "\"safety_tier\"" not in resp.text
        assert "\"routing_history\"" not in resp.text
        assert "\"the_dinh_kem\"" not in resp.text
        assert "\"voice_policy\"" not in resp.text
        assert "\"intervention\"" not in resp.text
    finally:
        app.dependency_overrides.clear()


def test_chat_message_non_sos_passes_routed_persona_to_langgraph(monkeypatch):
    fake_db = FakeDB()
    legacy_called = {"value": False}
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(chat_router, "decide_sos", lambda _message, **_kw: (False, 0.12))

    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: legacy_called.__setitem__("value", True),
    )
    monkeypatch.setattr(
        chat_router,
        "_active_persona_id",
        lambda _db, _uid, distress=0.0, requested_persona_id=None: "dat_le",
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "chao ban"})
        assert resp.status_code == 200
        assert legacy_called["value"] is False
    finally:
        app.dependency_overrides.clear()

def test_chat_message_harmful_instruction_blocks_before_graph(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(chat_router, "get_rate_limiter", lambda: DummyLimiter())
    monkeypatch.setattr(
        chat_router,
        "load_chat_context_sync",
        lambda *_args, **_kwargs: SimpleNamespace(recent_messages=[], mood_today=None),
    )
    monkeypatch.setattr(
        chat_router,
        "run_non_sos_turn",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("graph should not run for harmful instruction block")),
    )

    def override_db():
        yield fake_db

    app.dependency_overrides[chat_router.ensure_policy_acknowledged] = _override_user
    app.dependency_overrides[chat_router.get_db] = override_db

    try:
        with TestClient(app) as client:
            resp = client.post("/v1/chat/message", json={"message": "How to kill myself without pain?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["assistant_text"]
        assert "graph should not run" not in body["data"]["assistant_text"]
        assert body["data"]["message_id"]
        assert body["data"]["used_advisor_ids"] == []
        assert body["data"]["resource_suggestions"] == []
        assert body["data"]["pending_human_review"] is True
        assert body["data"]["route_tier"] == "fast"
        assert FORBIDDEN_NORMAL_CHAT_FIELDS.isdisjoint(body["data"])
    finally:
        app.dependency_overrides.clear()
