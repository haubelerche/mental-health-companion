from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import SyncOutbox
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT_JOBS: set[int] = set()
_LAST_TRIGGER_AT: dict[str, datetime] = {}
_AUDIO_DIR = Path(__file__).resolve().parents[2] / "generated_voice"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VOICE_JOB_EVENT_TYPE = "voice.tts_request"
VOICE_MAX_RETRIES = 3


def _normalize_audio_bytes(raw: Any) -> bytes:
    if isinstance(raw, bytes):
        return raw
    if hasattr(raw, "__iter__"):
        chunks: list[bytes] = []
        for chunk in raw:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        return b"".join(chunks)
    return b""


def build_voice_script(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    distress_score: float,
    risk_level: int,
    safety_tier: str,
    conversation_mode: str,
) -> str:
    settings = get_settings()
    recent_summary = "\n".join(
        f"{m.get('role', '')}: {str(m.get('content', '')).strip()[:120]}" for m in recent_messages[-6:]
    )
    default_script = "Mình đang ở đây với cậu. Nếu được, mình muốn cậu thử hít chậm một nhịp và ở lại với mình thêm một chút nhé."
    if not settings.openai_api_key:
        return default_script
    try:
        from openai import OpenAI

        system_prompt = (
            "Bạn là Safety Voice Writer cho ứng dụng hỗ trợ tâm lý Serene. "
            "Viết 1-2 câu tiếng Việt, tối đa 45 từ, giọng ấm áp, chân thành, không phán xét, không chẩn đoán, "
            "không mô tả phương thức tự hại, có lời mời hành động an toàn ngắn. "
            "Trả về JSON duy nhất với khóa: voice_script."
        )
        user_prompt = (
            f"User message: {user_message}\n"
            f"Recent: {recent_summary}\n"
            f"distress_score: {distress_score}\n"
            f"risk_level: {risk_level}\n"
            f"safety_tier: {safety_tier}\n"
            f"conversation_mode: {conversation_mode}"
        )
        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)
        resp = client.chat.completions.create(
            model=settings.openai_model_analyst,
            temperature=0.2,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("{"):
            parsed = json.loads(raw)
            text = str(parsed.get("voice_script") or "").strip()
            if text:
                return text[:260]
        return raw[:260] if raw else default_script
    except Exception as exc:
        logger.warning("voice script llm failed: %s", exc)
        return default_script


def cooldown_active(*, user_id: str, session_id: str | None) -> tuple[bool, int]:
    settings = get_settings()
    key = f"{user_id}:{session_id or '-'}"
    now = datetime.now(timezone.utc)
    last = _LAST_TRIGGER_AT.get(key)
    if not last:
        return False, 0
    remaining = int((last + timedelta(seconds=settings.proactive_voice_cooldown_seconds) - now).total_seconds())
    if remaining > 0:
        return True, remaining
    return False, 0


def mark_cooldown(*, user_id: str, session_id: str | None) -> None:
    key = f"{user_id}:{session_id or '-'}"
    _LAST_TRIGGER_AT[key] = datetime.now(timezone.utc)


def enqueue_voice_job(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    voice_script: str,
    trigger_reason: str,
    trigger_snapshot: dict[str, Any],
) -> dict[str, Any]:
    outbox = SyncOutbox(
        event_type=VOICE_JOB_EVENT_TYPE,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "voice_script": voice_script,
            "trigger_reason": trigger_reason,
            "trigger_snapshot": trigger_snapshot,
            "voice": {"status": "queued", "provider": "elevenlabs"},
        },
        status="pending",
    )
    db.add(outbox)
    db.flush()
    job_id = int(outbox.outbox_id)
    db.commit()
    # Dev-friendly inline worker; production should run dedicated voice worker.
    if settings.voice_tts_auto_process_on_enqueue:
        _start_voice_job_worker(job_id)
    return {
        "provider": "elevenlabs",
        "tts_job_id": f"tts_{job_id}",
        "audio_url": None,
        "status": "queued",
        "voice_id": get_settings().elevenlabs_voice_id,
        "model_id": get_settings().elevenlabs_model_id,
    }


def _start_voice_job_worker(job_id: int) -> None:
    with _INFLIGHT_LOCK:
        if job_id in _INFLIGHT_JOBS:
            return
        _INFLIGHT_JOBS.add(job_id)
    th = threading.Thread(target=_process_job, args=(job_id,), daemon=True)
    th.start()


def _process_job(job_id: int) -> None:
    factory = get_session_factory()
    db = factory()
    try:
        row = db.get(SyncOutbox, job_id)
        if not row or row.event_type != VOICE_JOB_EVENT_TYPE:
            return
        payload = dict(row.payload or {})
        voice_script = str(payload.get("voice_script") or "").strip()
        row.status = "processing"
        payload.setdefault("voice", {})
        payload["voice"]["status"] = "processing"
        row.payload = payload
        db.commit()

        audio_path = _render_tts_audio(job_id, voice_script)
        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        if audio_path:
            payload["voice"]["status"] = "ready"
            payload["voice"]["audio_path"] = str(audio_path)
            payload["voice"]["audio_url"] = f"/v1/chat/voice-jobs/tts_{job_id}/audio"
            row.status = "synced"
        else:
            payload["voice"]["status"] = "failed"
            row.retry_count = int(row.retry_count or 0) + 1
            if row.retry_count >= VOICE_MAX_RETRIES:
                row.status = "failed"
            else:
                row.status = "pending"
        row.payload = payload
        db.commit()
    except Exception as exc:
        logger.warning("voice tts job %s failed: %s", job_id, exc)
    finally:
        db.close()
        with _INFLIGHT_LOCK:
            _INFLIGHT_JOBS.discard(job_id)


def _render_tts_audio(job_id: int, voice_script: str) -> Path | None:
    settings = get_settings()
    if not settings.elevenlabs_api_key:
        return None
    try:
        from elevenlabs.client import ElevenLabs
    except Exception:
        return None

    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    try:
        raw = client.text_to_speech.convert(
            text=voice_script,
            voice_id=settings.elevenlabs_voice_id.strip(),
            model_id=settings.elevenlabs_model_id,
            output_format=settings.elevenlabs_output_format,
        )
        audio_bytes = _normalize_audio_bytes(raw)
        if not audio_bytes:
            return None
        out = _AUDIO_DIR / f"tts_{job_id}.mp3"
        out.write_bytes(audio_bytes)
        return out
    except Exception as exc:
        logger.warning("elevenlabs convert failed: %s", exc)
        return None


def get_voice_job(db: Session, tts_job_id: str) -> dict[str, Any] | None:
    if not tts_job_id.startswith("tts_"):
        return None
    try:
        outbox_id = int(tts_job_id.replace("tts_", "", 1))
    except ValueError:
        return None
    row = db.get(SyncOutbox, outbox_id)
    if not row or row.event_type != VOICE_JOB_EVENT_TYPE:
        return None
    payload = dict(row.payload or {})
    voice = dict(payload.get("voice") or {})
    return {
        "tts_job_id": tts_job_id,
        "status": str(voice.get("status") or row.status),
        "audio_url": voice.get("audio_url"),
        "trigger_reason": payload.get("trigger_reason"),
    }


def get_voice_audio_path(db: Session, tts_job_id: str) -> Path | None:
    if not tts_job_id.startswith("tts_"):
        return None
    try:
        outbox_id = int(tts_job_id.replace("tts_", "", 1))
    except ValueError:
        return None
    row = db.get(SyncOutbox, outbox_id)
    if not row or row.event_type != VOICE_JOB_EVENT_TYPE:
        return None
    payload = dict(row.payload or {})
    voice = dict(payload.get("voice") or {})
    p = voice.get("audio_path")
    if not p:
        return None
    path = Path(str(p))
    if not path.exists():
        return None
    return path


def reclaim_stale_processing_jobs(db: Session, *, stale_after_seconds: int = 180) -> int:
    threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=stale_after_seconds)
    rows = db.scalars(
        select(SyncOutbox).where(
            SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE,
            SyncOutbox.status == "processing",
            SyncOutbox.created_at < threshold,
        )
    ).all()
    count = 0
    for row in rows:
        row.status = "pending"
        count += 1
    if count:
        db.commit()
    return count


def lease_pending_voice_jobs(db: Session, *, limit: int = 20) -> list[int]:
    rows = db.scalars(
        select(SyncOutbox)
        .where(
            SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE,
            SyncOutbox.status == "pending",
            SyncOutbox.retry_count < VOICE_MAX_RETRIES,
        )
        .order_by(SyncOutbox.created_at.asc())
        .limit(limit)
    ).all()
    job_ids: list[int] = []
    for row in rows:
        row.status = "processing"
        row.retry_count = int(row.retry_count or 0) + 1
        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        payload["voice"]["status"] = "processing"
        row.payload = payload
        job_ids.append(int(row.outbox_id))
    if job_ids:
        db.commit()
    return job_ids


def process_leased_voice_jobs(job_ids: list[int]) -> None:
    for job_id in job_ids:
        _process_job(job_id)


def run_voice_worker_once(*, batch_size: int = 20) -> int:
    factory = get_session_factory()
    db = factory()
    try:
        reclaim_stale_processing_jobs(db)
        job_ids = lease_pending_voice_jobs(db, limit=batch_size)
    finally:
        db.close()
    if not job_ids:
        return 0
    process_leased_voice_jobs(job_ids)
    return len(job_ids)
