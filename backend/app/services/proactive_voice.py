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
_VOICE_PROVIDER_BLOCKED_CODE: str | None = None
_SESSION_ACTIVE_JOB: dict[str, str] = {}
_AUDIO_DIR = Path(__file__).resolve().parents[2] / "generated_voice"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VOICE_JOB_EVENT_TYPE = "voice.tts_request"
VOICE_MAX_RETRIES = 3


class PermanentTtsError(Exception):
    """Non-retryable TTS error (e.g. paid plan required)."""


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
    normalized = str(user_message or "").lower()
    if any(k in normalized for k in ("giet", "kill", "tra thu", "dam", "ban")):
        return (
            "Mình cần bạn ưu tiên an toàn ngay bây giờ: hãy tạm rời mọi vật có thể gây hại, "
            "đi đến nơi có người tin cậy, và gọi hotline khẩn cấp ở màn hình này."
        )
    if any(k in normalized for k in ("muon chet", "tu tu", "khong muon song", "end my life")):
        return (
            "Mình đang ở đây với bạn. Nếu được, hãy đặt điện thoại xuống một nhịp thở, "
            "rời khỏi các vật có thể gây hại và gọi ngay hotline để có người hỗ trợ trực tiếp."
        )
    if distress_score >= 0.8 or safety_tier in {"critical", "voice_recommended"}:
        return (
            "Mình nghe bạn và muốn đi cùng bạn từng bước. "
            "Mình mời bạn thử hít vào 4 giây, thở ra 6 giây, rồi nói với mình điều khó nhất ngay lúc này."
        )
    return "Mình ở đây với bạn. Mình mời bạn hít một nhịp chậm và chia sẻ điều đang làm bạn nặng lòng nhất lúc này."


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
    global _VOICE_PROVIDER_BLOCKED_CODE
    settings = get_settings()
    provider = str(getattr(settings, "tts_provider", "blaze") or "blaze").lower()
    if _VOICE_PROVIDER_BLOCKED_CODE:
        return {
            "provider": provider,
            "tts_job_id": None,
            "audio_url": None,
            "status": "failed",
            "model_id": settings.blaze_tts_model,
            "error_code": _VOICE_PROVIDER_BLOCKED_CODE,
            "error_message": "Voice provider hiện không khả dụng với cấu hình hiện tại. Hiển thị script text thay thế.",
        }
    with _INFLIGHT_LOCK:
        existing_tts_id = _SESSION_ACTIVE_JOB.get(session_id)
    if existing_tts_id:
        existing_job = get_voice_job(db, existing_tts_id)
        if existing_job and existing_job.get("status") in ("queued", "processing"):
            return {
                "provider": provider,
                "tts_job_id": existing_tts_id,
                "audio_url": None,
                "status": existing_job["status"],
                "model_id": settings.blaze_tts_model,
            }
    outbox = SyncOutbox(
        event_type=VOICE_JOB_EVENT_TYPE,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "voice_script": voice_script,
            "trigger_reason": trigger_reason,
            "trigger_snapshot": trigger_snapshot,
            "voice": {"status": "queued", "provider": provider},
        },
        status="pending",
    )
    db.add(outbox)
    db.flush()
    job_id = int(outbox.outbox_id)
    db.commit()
    tts_job_id = f"tts_{job_id}"
    with _INFLIGHT_LOCK:
        _SESSION_ACTIVE_JOB[session_id] = tts_job_id
    if settings.voice_tts_auto_process_on_enqueue:
        _start_voice_job_worker(job_id)
    return {
        "provider": provider,
        "tts_job_id": tts_job_id,
        "audio_url": None,
        "status": "queued",
        "model_id": settings.blaze_tts_model,
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
    global _VOICE_PROVIDER_BLOCKED_CODE
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

        try:
            audio_path = _render_tts_audio(job_id, voice_script)
            permanent_error_code = None
        except PermanentTtsError as exc:
            audio_path = None
            permanent_error_code = str(exc) or "tts_permanent_error"
            _VOICE_PROVIDER_BLOCKED_CODE = permanent_error_code
        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        if audio_path:
            payload["voice"]["status"] = "ready"
            payload["voice"]["audio_path"] = str(audio_path)
            payload["voice"]["audio_url"] = f"/v1/chat/voice-jobs/tts_{job_id}/audio"
            row.status = "done"
            row.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            payload["voice"]["status"] = "failed"
            if permanent_error_code:
                payload["voice"]["error_code"] = permanent_error_code
                row.status = "failed"
            else:
                row.retry_count = int(row.retry_count or 0) + 1
                if row.retry_count >= VOICE_MAX_RETRIES:
                    row.status = "failed"
                else:
                    row.status = "pending"
        if permanent_error_code:
            payload["voice"]["error_message"] = (
                "Nhà cung cấp voice từ chối yêu cầu ở gói hiện tại. Hiển thị script text thay thế."
            )
            row.status = "failed"
        elif not audio_path and row.retry_count >= VOICE_MAX_RETRIES:
            row.status = "failed"
        elif not audio_path:
            row.status = "pending"
        row.payload = payload
        db.commit()
    except Exception as exc:
        logger.warning("voice tts job %s failed: %s", job_id, exc)
    finally:
        db.close()
        tts_id = f"tts_{job_id}"
        with _INFLIGHT_LOCK:
            _INFLIGHT_JOBS.discard(job_id)
            for sid, tid in list(_SESSION_ACTIVE_JOB.items()):
                if tid == tts_id:
                    del _SESSION_ACTIVE_JOB[sid]
                    break


def _render_tts_audio(job_id: int, voice_script: str) -> Path | None:
    settings = get_settings()
    provider = str(getattr(settings, "tts_provider", "blaze") or "blaze").lower()
    if provider != "blaze":
        logger.info("tts_provider=%s is deprecated; forcing blaze", provider)
    return _render_blaze_audio(job_id, voice_script)


def _render_blaze_audio(job_id: int, voice_script: str) -> Path | None:
    """Call Blaze TTS API (https://blaze.vn) and save the returned audio."""
    settings = get_settings()
    api_key = (settings.blaze_api_key or "").strip()
    if not api_key:
        logger.warning("blaze tts: BLAZE_API key is not configured")
        return None

    url = (settings.blaze_tts_url or "").strip()
    model = (settings.blaze_tts_model or "blaze-tts-1").strip()
    output_format = (settings.blaze_tts_output_format or "mp3").strip().lower()
    timeout = float(getattr(settings, "tts_timeout_seconds", 4.0))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": voice_script,
        "model": model,
    }

    try:
        import httpx

        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code == 402:
                    raise PermanentTtsError("blaze_paid_plan_required")
                if response.status_code == 401:
                    raise PermanentTtsError("blaze_unauthorized")
                if not response.is_success:
                    logger.warning(
                        "blaze tts: HTTP %s — %s",
                        response.status_code,
                        response.read().decode(errors="replace")[:200],
                    )
                    return None

                audio_chunks: list[bytes] = []
                for chunk in response.iter_bytes(chunk_size=4096):
                    if chunk:
                        audio_chunks.append(chunk)

        audio_bytes = b"".join(audio_chunks)
        if not audio_bytes:
            logger.warning("blaze tts: empty audio response for job %s", job_id)
            return None

        ext = "mp3" if output_format == "mp3" else output_format
        out = _AUDIO_DIR / f"tts_{job_id}.{ext}"
        out.write_bytes(audio_bytes)
        logger.info("blaze tts: saved %d bytes to %s", len(audio_bytes), out)
        return out

    except PermanentTtsError:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "paid" in message or "payment" in message:
            raise PermanentTtsError("blaze_paid_plan_required") from exc
        logger.warning("blaze tts synthesis failed (job %s): %s", job_id, exc)
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
        "user_id": payload.get("user_id"),
        "status": str(voice.get("status") or row.status),
        "audio_url": voice.get("audio_url"),
        "trigger_reason": payload.get("trigger_reason"),
        "error_code": voice.get("error_code"),
        "error_message": voice.get("error_message"),
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
