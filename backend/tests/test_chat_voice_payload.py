from types import SimpleNamespace
from datetime import datetime, timezone

from app.api.v1.routers import chat
from app.services.proactive_voice import get_voice_job
from app.services.voice_policy import VoiceMessagePolicyEngine, VoicePolicyContext


def test_chat_voice_policy_payload_supports_multiple_sos_cards(monkeypatch):
    calls = []

    def fake_enqueue(_db, **kwargs):
        calls.append(kwargs)
        idx = len(calls)
        return {
            "tts_job_id": f"tts_{idx}",
            "audio_url": None,
            "status": "queued",
            "event_signature": f"sig_{idx}",
            "voice_script_hash": f"sig_{idx}",
        }

    monkeypatch.setattr(chat, "enqueue_voice_job", fake_enqueue)
    monkeypatch.setattr(chat, "mark_cooldown", lambda **_kwargs: None)

    decision = VoiceMessagePolicyEngine.decide(
        VoicePolicyContext(
            user_id="u1",
            session_id="s1",
            distress_score=0.95,
            safety_tier="critical",
            sos_triggered=True,
            visible_text="Minh o day voi ban.",
        )
    )
    result = chat._enqueue_voice_policy(
        db=object(),
        user_id="u1",
        session_id="s1",
        decision=decision,
        snap=SimpleNamespace(distress_score=0.95, risk_level=5, safety_tier="critical"),
        trigger_reason="sos_gate_forced",
    )

    payload = result["voice_policy"]
    assert payload["risk_mode"] == "sos"
    assert payload["ordinary_cooldown_bypassed"] is True
    assert len(payload["voice_messages"]) == 3
    assert all("voice_script" not in item for item in payload["voice_messages"])
    assert [call["voice_intent"] for call in calls] == [
        "sos_grounding",
        "sos_stay_with_user",
        "sos_next_safe_step",
    ]


def test_provider_disabled_sos_payload_has_terminal_card():
    decision = VoiceMessagePolicyEngine.decide(
        VoicePolicyContext(
            user_id="u1",
            session_id="s1",
            distress_score=0.95,
            safety_tier="critical",
            sos_triggered=True,
            provider_enabled=False,
        )
    )
    result = chat._enqueue_voice_policy(
        db=object(),
        user_id="u1",
        session_id="s1",
        decision=decision,
        snap=SimpleNamespace(distress_score=0.95, risk_level=5, safety_tier="critical"),
        trigger_reason="sos_gate_forced",
    )

    messages = result["voice_policy"]["voice_messages"]
    assert messages[0]["status"] == "provider_disabled"
    assert messages[0]["error_code"] == "provider_disabled"


def test_build_voice_script_differs_from_visible_text():
    """Voice script phải khác visible text — không được copy nguyên assistant_content."""
    from app.services.proactive_voice import build_voice_script

    visible = (
        "Mình nghe bạn đang rất mệt. Điều đó hoàn toàn có thể hiểu được. "
        "Bạn có muốn chia sẻ thêm điều gì đang làm bạn nặng nhất không?"
    )
    voice = build_voice_script(
        user_message="toi dang rat met",
        recent_messages=[],
        distress_score=0.75,
        risk_level=3,
        safety_tier="elevated",
        conversation_mode="support",
    )
    assert isinstance(voice, str) and len(voice) > 0

    def word_set(t: str) -> set:
        return set(t.lower().split())

    overlap = len(word_set(voice) & word_set(visible)) / max(len(word_set(voice) | word_set(visible)), 1)
    assert overlap < 0.6, f"Voice script quá giống visible text: overlap={overlap:.2f}"


def test_maybe_enqueue_voice_passes_user_message_to_build_intervention(monkeypatch):
    """_maybe_enqueue_voice phải pass user_message và recent_messages xuống _build_voice_intervention."""
    from types import SimpleNamespace
    from app.api.v1.routers.chat import _maybe_enqueue_voice

    captured = {}

    def fake_build_intervention(**kwargs):
        captured.update(kwargs)
        return {"type": "proactive_voice", "voice": {}}

    monkeypatch.setattr(chat, "_build_voice_intervention", fake_build_intervention)
    monkeypatch.setattr(chat, "compute_escalation_signal", lambda **kw: SimpleNamespace(
        escalate=True,
        trigger_reason="test_escalation",
        rolling_window_turns=3,
        delta_score=0.25,
    ))
    monkeypatch.setattr(chat, "message_suggests_proactive_voice", lambda _: False)
    monkeypatch.setattr(chat, "get_settings", lambda: SimpleNamespace(
        proactive_voice_threshold=0.84,
        proactive_voice_delta_threshold=0.22,
        proactive_voice_window_turns=6,
        proactive_voice_auto_distress_threshold=0.68,
    ))

    _maybe_enqueue_voice(
        db=object(),
        user_id="u1",
        session_id="s1",
        snap=SimpleNamespace(distress_score=0.75, risk_level=3, safety_tier="elevated"),
        assistant_content="Mình nghe bạn đang rất mệt.",
        user_message="toi dang rat met",
        recent_messages=[{"role": "user", "content": "hom nay kho qua"}],
        cooldown_is_active=False,
        cooldown_seconds=0,
        settings=SimpleNamespace(
            proactive_voice_threshold=0.84,
            proactive_voice_delta_threshold=0.22,
            proactive_voice_window_turns=6,
            proactive_voice_auto_distress_threshold=0.68,
        ),
    )

    assert captured.get("user_message") == "toi dang rat met"
    assert isinstance(captured.get("recent_messages"), list)
    assert len(captured["recent_messages"]) == 1


def test_assistant_client_payload_persists_meme_and_tts_metadata():
    assistant = SimpleNamespace(metadata_json={})
    data = {
        "session_id": "s1",
        "message_id": "m1",
        "reply": "Meme nhe.",
        "assistant_text": "Meme nhe.",
        "tts_job": {"tts_job_id": "tts_1", "status": "queued"},
        "meme_suggestion": {"id": "emotion_1", "image_path": "happy.jpg"},
        "voice_policy": {"internal": True},
    }

    chat._persist_assistant_client_payload(SimpleNamespace(add=lambda _obj: None), assistant, data)

    payload = assistant.metadata_json["client_payload"]
    assert payload["tts_job"]["tts_job_id"] == "tts_1"
    assert payload["meme_suggestion"]["image_path"] == "happy.jpg"
    assert "voice_policy" not in payload


def test_voice_job_history_survives_missing_local_audio_file():
    audio_data_uri = "data:audio/mpeg;base64,SUQz"
    row = SimpleNamespace(
        outbox_id=42,
        event_type="voice.tts_request",
        payload={
            "user_id": "u1",
            "trigger_reason": "test",
            "voice": {
                "status": "ready",
                "audio_path": "/tmp/serene-missing-voice-file.mp3",
                "audio_url": "/v1/chat/voice-jobs/tts_42/audio",
                "audio_data_uri": audio_data_uri,
            },
        },
        status="done",
        created_at=datetime.now(timezone.utc),
        processing_started_at=None,
    )

    commits = []
    db = SimpleNamespace(
        get=lambda _model, _pk: row,
        commit=lambda: commits.append(True),
    )

    job = get_voice_job(db, "tts_42")

    assert job["status"] == "ready"
    assert job["audio_data_uri"] == audio_data_uri
    assert row.status == "done"
    assert row.payload["voice"].get("error_code") is None
