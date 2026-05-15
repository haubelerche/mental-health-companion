from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services import proactive_voice
from app.voice.dedup import compute_event_signature, find_dedup_job
from app.voice.types import TTS_REUSABLE_STATUSES


def test_build_voice_script_returns_fallback_without_openai(monkeypatch):
    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(openai_api_key="", llm_timeout_seconds=10, openai_model_analyst="gpt-4o-mini"),
    )
    text = proactive_voice.build_voice_script(
        user_message="Toi dang rat met",
        recent_messages=[{"role": "user", "content": "Minh thay khong on"}],
        distress_score=0.92,
        risk_level=5,
        safety_tier="critical",
        conversation_mode="de_escalation",
    )
    assert isinstance(text, str)
    assert len(text) > 0


def test_cooldown_active_and_remaining(monkeypatch):
    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(proactive_voice_cooldown_seconds=120),
    )
    proactive_voice.mark_cooldown(user_id="usr_a", session_id="sess_1")
    active, remaining = proactive_voice.cooldown_active(user_id="usr_a", session_id="sess_1")
    assert active is True
    assert remaining > 0


def test_get_voice_job_invalid_id_returns_none():
    class DummyDb:
        def get(self, *_args, **_kwargs):
            return None

    db = DummyDb()
    assert proactive_voice.get_voice_job(db, "abc") is None
    assert proactive_voice.get_voice_audio_path(db, "tts_not_number") is None


def test_seconds_since_handles_aware_utc_against_vietnam_now(monkeypatch):
    utc_now = datetime(2026, 5, 9, 15, 0, 10, tzinfo=timezone.utc)
    vietnam_now = utc_now.astimezone(timezone(timedelta(hours=7)))
    monkeypatch.setattr("app.services.utils.get_now", lambda: vietnam_now)

    created_at = datetime(2026, 5, 9, 15, 0, 0, tzinfo=timezone.utc)

    assert proactive_voice._seconds_since(created_at) == 10


def test_get_voice_job_processing_uses_processing_started_at(monkeypatch):
    vietnam_now = datetime(2026, 5, 9, 22, 0, 10, tzinfo=timezone(timedelta(hours=7)))
    monkeypatch.setattr("app.services.utils.get_now", lambda: vietnam_now)
    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(voice_tts_auto_process_on_enqueue=False),
    )

    class Row:
        outbox_id = 9
        event_type = proactive_voice.VOICE_JOB_EVENT_TYPE
        status = "processing"
        retry_count = 0
        created_at = datetime(2026, 5, 9, 15, 0, 0, tzinfo=timezone.utc)
        processing_started_at = datetime(2026, 5, 9, 22, 0, 0)
        payload = {
            "user_id": "usr_1",
            "voice": {"status": "processing"},
        }

    class Db:
        def __init__(self):
            self.row = Row()
            self.committed = False

        def get(self, *_args):
            return self.row

        def commit(self):
            self.committed = True

    db = Db()
    job = proactive_voice.get_voice_job(db, "tts_9")

    assert job is not None
    assert job["status"] == "processing"
    assert job["error_code"] is None
    assert db.row.status == "processing"
    assert db.committed is False


def test_get_voice_job_done_ready_clears_stale_error():
    class Row:
        outbox_id = 10
        event_type = proactive_voice.VOICE_JOB_EVENT_TYPE
        status = "done"
        retry_count = 0
        created_at = datetime(2026, 5, 9, 15, 0, 0, tzinfo=timezone.utc)
        processing_started_at = datetime(2026, 5, 9, 15, 0, 1, tzinfo=timezone.utc)
        payload = {
            "user_id": "usr_1",
            "voice": {
                "status": "ready",
                "audio_url": "/v1/chat/voice-jobs/tts_10/audio",
                "error_code": "stale_lock",
                "error_message": "Voice job xử lý quá lâu; hệ thống đã đánh dấu thất bại.",
            },
        }

    class Db:
        def __init__(self):
            self.row = Row()
            self.committed = False

        def get(self, *_args):
            return self.row

        def commit(self):
            self.committed = True

    db = Db()
    job = proactive_voice.get_voice_job(db, "tts_10")

    assert job is not None
    assert job["status"] == "ready"
    assert job["audio_url"] == "/v1/chat/voice-jobs/tts_10/audio"
    assert job["error_code"] is None
    assert job["error_message"] is None
    assert "error_code" not in db.row.payload["voice"]
    assert "error_message" not in db.row.payload["voice"]


def test_dedup_reuses_queued_processing_and_ready_jobs():
    assert "queued" in TTS_REUSABLE_STATUSES
    assert "processing" in TTS_REUSABLE_STATUSES

    signature = compute_event_signature(
        user_id="usr_1",
        session_id="sess_1",
        voice_style_id="style_a",
        voice_script="Mình ở đây với bạn.",
        provider="elevenlabs",
        voice_id="voice_a",
    )

    class Row:
        def __init__(self, outbox_id: int, status: str):
            self.outbox_id = outbox_id
            self.created_at = datetime.now(timezone.utc)
            self.payload = {
                "voice": {
                    "event_signature": signature,
                    "status": status,
                    "audio_url": f"/v1/chat/voice-jobs/tts_{outbox_id}/audio",
                },
            }

    class ScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class Db:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self, *_args, **_kwargs):
            return ScalarResult(self._rows)

    processing = find_dedup_job(Db([Row(21, "processing")]), signature)
    assert processing is not None
    assert processing["tts_job_id"] == "tts_21"

    queued = find_dedup_job(Db([Row(22, "queued")]), signature)
    assert queued is not None
    assert queued["tts_job_id"] == "tts_22"

    ready = find_dedup_job(Db([Row(23, "ready")]), signature)
    assert ready is not None
    assert ready["tts_job_id"] == "tts_23"


def test_dedup_signature_includes_risk_mode_intent_and_template_version():
    base = dict(
        user_id="usr_1",
        session_id="sess_1",
        voice_style_id="style_a",
        voice_script="Minh o day voi ban.",
        provider="elevenlabs",
        voice_id="voice_a",
    )

    sos_grounding = compute_event_signature(
        **base,
        risk_mode="sos",
        voice_intent="sos_grounding",
        template_version="voice_policy_v1",
    )
    sos_next_step = compute_event_signature(
        **base,
        risk_mode="sos",
        voice_intent="sos_next_safe_step",
        template_version="voice_policy_v1",
    )
    elevated = compute_event_signature(
        **base,
        risk_mode="elevated",
        voice_intent="elevated_encouragement",
        template_version="voice_policy_v1",
    )

    assert sos_grounding != sos_next_step
    assert sos_grounding != elevated


def test_normalize_audio_bytes_from_iterable():
    raw = [b"abc", b"123"]
    out = proactive_voice._normalize_audio_bytes(raw)
    assert out == b"abc123"


def test_run_voice_worker_once_processes_jobs(monkeypatch):
    class _Db:
        def close(self):
            return

    class _Factory:
        def __call__(self):
            return _Db()

    monkeypatch.setattr(proactive_voice, "get_session_factory", lambda: _Factory())
    monkeypatch.setattr(proactive_voice, "reclaim_stale_processing_jobs", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(proactive_voice, "lease_pending_voice_jobs", lambda *_args, **_kwargs: [1, 2, 3])
    seen = {"count": 0}

    def _process(job_ids):
        seen["count"] = len(job_ids)

    monkeypatch.setattr(proactive_voice, "process_leased_voice_jobs", _process)
    processed = proactive_voice.run_voice_worker_once(batch_size=10)
    assert processed == 3
    assert seen["count"] == 3


def test_enqueue_voice_job_auto_process_uses_settings(monkeypatch):
    class DummyOutbox:
        def __init__(self, **kwargs):
            self.event_type = kwargs["event_type"]
            self.payload = kwargs["payload"]
            self.status = kwargs["status"]
            self.outbox_id = None

    class DummyDb:
        def __init__(self):
            self._added = []
            self.committed = False

        def add(self, item):
            self._added.append(item)

        def flush(self):
            if self._added:
                self._added[-1].outbox_id = 1

        def commit(self):
            self.committed = True

    monkeypatch.setattr(proactive_voice, "SyncOutbox", DummyOutbox)
    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(
            voice_tts_auto_process_on_enqueue=True,
            tts_provider="blaze",
            blaze_tts_model="blaze-tts-1",
        ),
    )
    monkeypatch.setattr(proactive_voice, "_VOICE_PROVIDER_BLOCKED_CODE", None)
    started = {"job_id": None}
    monkeypatch.setattr(proactive_voice, "_start_voice_job_worker", lambda job_id: started.update(job_id=job_id))

    db = DummyDb()
    result = proactive_voice.enqueue_voice_job(
        db,
        user_id="usr_test",
        session_id="sess_test",
        voice_script="Mình ở đây với cậu.",
        trigger_reason="threshold_crossed",
        trigger_snapshot={"distress_score": 0.9},
    )

    assert db.committed is True
    assert started["job_id"] == 1
    assert result["status"] == "queued"
    assert result["tts_job_id"] == "tts_1"


def test_render_tts_audio_routed_via_renderer(monkeypatch):
    """TTS path uses shared render_tts_audio (ElevenLabs); Blaze-specific helper removed."""
    called: dict[str, object] = {}

    def _fake_render(provider, script, job_key, *args, **kwargs):
        called["provider"] = provider
        called["script"] = script
        called["job_key"] = job_key
        return {
            "audio_path": "/tmp/fake.mp3",
            "provider": provider,
            "duration": 1.0,
            "chars": len(script),
            "success": True,
            "fallback": False,
        }

    monkeypatch.setattr(proactive_voice, "render_tts_audio", _fake_render)
    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(tts_provider="elevenlabs"),
    )
    out = proactive_voice.render_tts_audio("elevenlabs", "xin chao", "tts_12", None, None, user_id="u1")
    assert out["success"] is True
    assert called["provider"] == "elevenlabs"
    assert called["script"] == "xin chao"


def test_message_suggests_proactive_voice_detects_intensity_cues():
    assert proactive_voice.message_suggests_proactive_voice("mấy thằng đó cực đoan quá") is True
    assert proactive_voice.message_suggests_proactive_voice("tôi muốn trả thù") is True
    assert proactive_voice.message_suggests_proactive_voice("hôm nay trời đẹp") is False


def test_enqueue_voice_job_stores_conversation_context(monkeypatch):
    """enqueue_voice_job phải lưu user_message và conversation_context vào outbox payload."""
    from app.services.proactive_voice import enqueue_voice_job
    from app.services.db.models import SyncOutbox

    captured_payload = {}

    class FakeRow:
        outbox_id = 42
        event_type = proactive_voice.VOICE_JOB_EVENT_TYPE
        payload = None
        status = "pending"

    fake_row = FakeRow()

    class FakeDb:
        def add(self, obj):
            pass
        def flush(self):
            fake_row.payload = fake_row.payload  # no-op; row is set externally
        def commit(self):
            if fake_row.payload:
                captured_payload.update(dict(fake_row.payload or {}))

    monkeypatch.setattr(
        proactive_voice,
        "get_settings",
        lambda: SimpleNamespace(
            tts_provider="elevenlabs",
            voice_tts_auto_process_on_enqueue=False,
            elevenlabs_model_id="eleven_flash_v2_5",
        ),
    )
    monkeypatch.setattr(proactive_voice, "_VOICE_PROVIDER_BLOCKED_CODE", None)
    monkeypatch.setattr(proactive_voice, "resolve_active_style", lambda *a, **kw: "default")
    monkeypatch.setattr(proactive_voice, "resolve_elevenlabs_voice_id", lambda **kw: "v123")
    monkeypatch.setattr(proactive_voice, "compute_event_signature", lambda **kw: "sig_abc")
    monkeypatch.setattr(proactive_voice, "find_dedup_job", lambda db, sig: None)

    created_rows = []

    def fake_syncoutbox(**kwargs):
        fake_row.payload = kwargs.get("payload")
        fake_row.status = kwargs.get("status", "pending")
        created_rows.append(fake_row)
        return fake_row

    monkeypatch.setattr(proactive_voice, "SyncOutbox", fake_syncoutbox)

    enqueue_voice_job(
        FakeDb(),
        user_id="u1",
        session_id="s1",
        voice_script="Mình ở đây với bạn",
        trigger_reason="test",
        trigger_snapshot={"distress_score": 0.7},
        user_message="Tôi đang rất mệt",
        conversation_context=[{"role": "user", "content": "Hôm nay buồn lắm"}],
    )

    assert captured_payload.get("user_message") == "Tôi đang rất mệt"
    assert isinstance(captured_payload.get("conversation_context"), list)
    assert len(captured_payload["conversation_context"]) == 1
    assert captured_payload["conversation_context"][0]["role"] == "user"
