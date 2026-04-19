from types import SimpleNamespace

from app.services import proactive_voice


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
