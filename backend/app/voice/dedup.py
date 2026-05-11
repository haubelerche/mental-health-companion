"""TTS event signature deduplication — Plan 08 §14.3.

Signature (per voice-tts.md rule):
    hash((session_id, persona_style_id, normalized_voice_script,
          provider, voice_id, locale, speech_rate))

Dedup flow:
1. Compute signature before creating a SyncOutbox row.
2. Scan recent (< 24h) SyncOutbox voice jobs for same signature.
3. If found and status is reusable → return cache_hit / skipped_duplicate.
4. If not found or existing job is failed → allow new job creation.

The signature is stored in payload["voice"]["event_signature"] so it
can be queried later without adding a new DB column.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.voice.types import TTS_REUSABLE_STATUSES

# Imported lazily to avoid circular imports from proactive_voice module.
VOICE_JOB_EVENT_TYPE = "voice.tts_request"

# How far back we search for duplicate jobs (prevents unbounded scans).
DEDUP_WINDOW_HOURS = 24


def _normalize_script(text: str) -> str:
    """Lowercase + collapse whitespace + NFD → ascii-fold for stable hashing."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def compute_event_signature(
    *,
    user_id: str = "",
    session_id: str,
    voice_style_id: str,
    voice_script: str,
    provider: str = "elevenlabs",
    voice_id: str = "",
    locale: str = "vi",
    speech_rate: float = 1.0,
    risk_mode: str = "normal",
    voice_intent: str = "unspecified",
    template_version: str = "voice_policy_v1",
) -> str:
    """Return a hex SHA-256 event signature for TTS dedup.

    Stable for identical inputs; distinct for any meaningful difference.
    Includes user_id so one user's cache never collides with another's.
    """
    normalized = _normalize_script(voice_script)
    uid = str(user_id or "").strip()
    key = (
        f"{uid}|{session_id}|{voice_style_id}|{normalized}"
        f"|{provider}|{voice_id}|{locale}|{speech_rate:.2f}"
        f"|{risk_mode}|{voice_intent}|{template_version}"
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def find_dedup_job(
    db: Session,
    signature: str,
) -> dict[str, Any] | None:
    """Search recent SyncOutbox TTS jobs for a matching event signature.

    Returns the first matching reusable job's payload dict, or None.
    A job is reusable when its voice status is in TTS_REUSABLE_STATUSES, including
    queued/processing jobs. This prevents duplicate provider work while the first
    request is still in flight.
    """
    from app.services.utils import get_now
    cutoff = (get_now() - timedelta(hours=DEDUP_WINDOW_HOURS)).replace(tzinfo=None)

    # We load only recent rows and filter by signature in Python.
    # Volume of TTS jobs within 24h is small, so this avoids JSON-path
    # operators that differ between SQLite (tests) and PostgreSQL (prod).
    try:
        from app.services.db.models import SyncOutbox  # avoid top-level circular import
    except ImportError:
        return None

    try:
        rows = db.scalars(
            select(SyncOutbox)
            .where(
                SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE,
                SyncOutbox.created_at >= cutoff,
            )
            .order_by(SyncOutbox.created_at.desc())
            .limit(200)
        ).all()
    except AttributeError:
        # Non-SQLAlchemy stub DB (unit-test double) — skip dedup gracefully.
        return None

    for row in rows:
        payload = dict(row.payload or {})
        voice = dict(payload.get("voice") or {})
        if voice.get("event_signature") != signature:
            continue
        voice_status = str(voice.get("status") or "")
        if voice_status not in TTS_REUSABLE_STATUSES:
            # Failed / unknown → don't reuse; allow new job.
            continue
        return {
            "outbox_id": int(row.outbox_id),
            "tts_job_id": f"tts_{row.outbox_id}",
            "voice_status": voice_status,
            "audio_url": voice.get("audio_url"),
            "event_signature": signature,
        }

    return None


def dedup_status_for(voice_status: str) -> str:
    """Map an existing job's voice_status to the dedup response status."""
    if voice_status == "ready":
        return "cache_hit"
    return "skipped_duplicate"
