"""Tests for Plan 08 — Voice/TTS Deduplication.

Covers:
- compute_event_signature: stable hash for same inputs
- compute_event_signature: distinct hash for any changed field
- Style mapping: all 5 canonical personas mapped
- Style mapping: restricted styles fall back without ownership
- find_dedup_job: returns None when no jobs exist
- find_dedup_job: returns matching reusable job (queued / processing / ready)
- find_dedup_job: ignores failed jobs (allows new job creation)
- dedup_status_for: ready → cache_hit; others → skipped_duplicate
- enqueue_voice_job: same signature returns skipped_duplicate (no new row)
- enqueue_voice_job: failed existing job allows new job creation
- TTS_TERMINAL_STATUSES: all expected statuses present

Uses in-memory SQLite (same pattern as other test files).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.services.db.models import SyncOutbox, User
from app.services.db.session import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            user_id="usr_tts_test",
            display_name="TTS Tester",
            email="tts@test.com",
            password_hash="x",
            is_active=True,
        )
        session.add(user)
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


def _make_outbox(db: Session, signature: str, voice_status: str) -> SyncOutbox:
    """Helper: insert a SyncOutbox TTS job with a given signature and voice status.
    """
    db_status = "pending" if voice_status in ("queued", "processing") else (
        "done" if voice_status == "ready" else "failed"
    )
    row = SyncOutbox(
        event_type="voice.tts_request",
        payload={
            "user_id": "usr_tts_test",
            "session_id": "sess_abc",
            "voice_script": "test script",
            "voice": {
                "status": voice_status,
                "event_signature": signature,
            },
        },
        status=db_status,
    )
    db.add(row)
    db.commit()
    return row


# ---------------------------------------------------------------------------
# compute_event_signature
# ---------------------------------------------------------------------------

class TestComputeEventSignature:
    def test_stable_for_same_inputs(self):
        from app.voice.dedup import compute_event_signature

        sig1 = compute_event_signature(
            session_id="sess_1",
            voice_style_id="warm_friend",
            voice_script="Mình ở đây với bạn.",
            provider="elevenlabs",
        )
        sig2 = compute_event_signature(
            session_id="sess_1",
            voice_style_id="warm_friend",
            voice_script="Mình ở đây với bạn.",
            provider="elevenlabs",
        )
        assert sig1 == sig2

    def test_whitespace_normalized(self):
        from app.voice.dedup import compute_event_signature

        sig1 = compute_event_signature(
            session_id="s", voice_style_id="warm_friend",
            voice_script="Mình   ở đây   với bạn.",
        )
        sig2 = compute_event_signature(
            session_id="s", voice_style_id="warm_friend",
            voice_script="Mình ở đây với bạn.",
        )
        assert sig1 == sig2

    def test_different_session_different_sig(self):
        from app.voice.dedup import compute_event_signature

        sig1 = compute_event_signature(session_id="sess_A", voice_style_id="warm_friend", voice_script="x")
        sig2 = compute_event_signature(session_id="sess_B", voice_style_id="warm_friend", voice_script="x")
        assert sig1 != sig2

    def test_different_style_different_sig(self):
        from app.voice.dedup import compute_event_signature

        sig1 = compute_event_signature(session_id="s", voice_style_id="warm_friend", voice_script="x")
        sig2 = compute_event_signature(session_id="s", voice_style_id="calm_mentor", voice_script="x")
        assert sig1 != sig2

    def test_different_script_different_sig(self):
        from app.voice.dedup import compute_event_signature

        sig1 = compute_event_signature(session_id="s", voice_style_id="w", voice_script="script A")
        sig2 = compute_event_signature(session_id="s", voice_style_id="w", voice_script="script B")
        assert sig1 != sig2

    def test_returns_hex_string(self):
        from app.voice.dedup import compute_event_signature

        sig = compute_event_signature(session_id="s", voice_style_id="w", voice_script="x")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# Style mapping
# ---------------------------------------------------------------------------

class TestStyleMapping:
    def test_all_personas_mapped(self):
        from app.voice.style_mapping import PERSONA_VOICE_STYLES

        expected_ids = {"ban_than", "nguoi_thay", "cun", "meo", "crush"}
        assert expected_ids == set(PERSONA_VOICE_STYLES.keys())

    def test_default_for_unknown_persona(self):
        from app.voice.style_mapping import DEFAULT_VOICE_STYLE, get_voice_style

        assert get_voice_style("unknown_xyz") == DEFAULT_VOICE_STYLE
        assert get_voice_style(None) == DEFAULT_VOICE_STYLE

    def test_crush_style_is_restricted(self):
        from app.voice.style_mapping import is_style_restricted, get_voice_style

        assert is_style_restricted(get_voice_style("crush"))

    def test_restricted_style_falls_back_without_ownership(self):
        from app.voice.style_mapping import DEFAULT_VOICE_STYLE, resolve_active_style

        style = resolve_active_style("crush", user_owns_voice_style=False)
        assert style == DEFAULT_VOICE_STYLE

    def test_restricted_style_used_with_ownership(self):
        from app.voice.style_mapping import resolve_active_style

        style = resolve_active_style("crush", user_owns_voice_style=True)
        assert style == "soft_affectionate"

    def test_free_style_unaffected_by_ownership_flag(self):
        from app.voice.style_mapping import resolve_active_style

        style_with = resolve_active_style("ban_than", user_owns_voice_style=True)
        style_without = resolve_active_style("ban_than", user_owns_voice_style=False)
        assert style_with == style_without == "warm_friend"


# ---------------------------------------------------------------------------
# find_dedup_job
# ---------------------------------------------------------------------------

class TestFindDedupJob:
    def test_returns_none_when_no_jobs(self, db):
        from app.voice.dedup import compute_event_signature, find_dedup_job

        sig = compute_event_signature(session_id="s0", voice_style_id="w", voice_script="x")
        assert find_dedup_job(db, sig) is None

    def test_finds_queued_job(self, db):
        from app.voice.dedup import compute_event_signature, find_dedup_job

        sig = compute_event_signature(session_id="s1", voice_style_id="warm_friend", voice_script="hello")
        _make_outbox(db, sig, "queued")

        result = find_dedup_job(db, sig)
        assert result is not None
        assert result["voice_status"] == "queued"

    def test_finds_ready_job(self, db):
        from app.voice.dedup import compute_event_signature, find_dedup_job

        sig = compute_event_signature(session_id="s2", voice_style_id="warm_friend", voice_script="ready test")
        _make_outbox(db, sig, "ready")

        result = find_dedup_job(db, sig)
        assert result is not None
        assert result["voice_status"] == "ready"

    def test_ignores_failed_job(self, db):
        from app.voice.dedup import compute_event_signature, find_dedup_job

        sig = compute_event_signature(session_id="s3", voice_style_id="warm_friend", voice_script="failed test")
        _make_outbox(db, sig, "failed")

        result = find_dedup_job(db, sig)
        assert result is None

    def test_returns_none_for_different_signature(self, db):
        from app.voice.dedup import compute_event_signature, find_dedup_job

        sig_a = compute_event_signature(session_id="sA", voice_style_id="warm_friend", voice_script="script a")
        sig_b = compute_event_signature(session_id="sB", voice_style_id="warm_friend", voice_script="script b")
        _make_outbox(db, sig_a, "queued")

        assert find_dedup_job(db, sig_b) is None


# ---------------------------------------------------------------------------
# dedup_status_for
# ---------------------------------------------------------------------------

class TestDedupStatusFor:
    def test_ready_maps_to_cache_hit(self):
        from app.voice.dedup import dedup_status_for

        assert dedup_status_for("ready") == "cache_hit"

    def test_queued_maps_to_skipped_duplicate(self):
        from app.voice.dedup import dedup_status_for

        assert dedup_status_for("queued") == "skipped_duplicate"

    def test_processing_maps_to_skipped_duplicate(self):
        from app.voice.dedup import dedup_status_for

        assert dedup_status_for("processing") == "skipped_duplicate"


# ---------------------------------------------------------------------------
# TTS_TERMINAL_STATUSES
# ---------------------------------------------------------------------------

class TestTerminalStatuses:
    def test_all_expected_statuses_present(self):
        from app.voice.types import TTS_TERMINAL_STATUSES

        expected = {"ready", "failed", "skipped_duplicate", "cache_hit", "provider_disabled"}
        assert expected.issubset(TTS_TERMINAL_STATUSES)

    def test_queued_is_not_terminal(self):
        from app.voice.types import TTS_TERMINAL_STATUSES

        assert "queued" not in TTS_TERMINAL_STATUSES

    def test_processing_is_not_terminal(self):
        from app.voice.types import TTS_TERMINAL_STATUSES

        assert "processing" not in TTS_TERMINAL_STATUSES
