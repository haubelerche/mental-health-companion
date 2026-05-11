from __future__ import annotations

import base64
import logging
import os
import re
import unicodedata
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_CR_INSTANCE = os.environ.get("K_REVISION", "local")

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.services.db.models import SyncOutbox
from app.services.db.session import get_session_factory
from app.services.pii_mask import mask_pii
from app.services.tts_exceptions import PermanentTtsError
from app.services.tts_renderer import TTS_AUDIO_OUTPUT_DIR, _normalize_audio_bytes, render_tts_audio
from app.voice.dedup import compute_event_signature, dedup_status_for, find_dedup_job
from app.voice.style_mapping import resolve_active_style

logger = logging.getLogger(__name__)


def _normalize_for_voice_cues(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")
    compact = re.sub(r"[^a-z0-9\s@$]", " ", no_accent)
    return re.sub(r"\s+", " ", compact).strip()


def message_suggests_proactive_voice(user_message: str) -> bool:
    """High-intensity / extremist-leaning phrasing: offer TTS even when SOS gate did not fire."""
    n = _normalize_for_voice_cues(user_message)
    if not n:
        return False
    cues = (
        "cuc doan",
        "cuc dai",
        "thu han",
        "tra thu",
        "giet nguoi",
        "giet ",
        "danh chet",
        "dam chet",
        "bao luc",
        "diet chung",
        "phan no",
        "cuong no",
        "diet bo",
        "thanh chien",
        "khung bo",
        "danh bom",
    )
    return any(c in n for c in cues)


_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT_JOBS: set[int] = set()
_INFLIGHT_STARTED_AT: dict[int, datetime] = {}
_INFLIGHT_OWNER: dict[int, str] = {}
_LAST_TRIGGER_AT: dict[str, datetime] = {}
_VOICE_PROVIDER_BLOCKED_CODE: str | None = None
_AUDIO_DIR = TTS_AUDIO_OUTPUT_DIR
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
VOICE_JOB_EVENT_TYPE = "voice.tts_request"
VOICE_MAX_RETRIES = 3
VOICE_JOB_PENDING_TIMEOUT_SECONDS = 90
VOICE_JOB_PROCESSING_STALE_SECONDS = 180
_PROVIDER_LEVEL_BLOCK_CODES = {
    "elevenlabs_feature_disabled",
    "elevenlabs_credentials_missing",
    "elevenlabs_package_missing",
}


def _assign_payload(row: SyncOutbox, payload: dict[str, Any]) -> None:
    """Assign JSON payload and force SQLAlchemy to persist nested JSON changes."""
    row.payload = payload
    try:
        flag_modified(row, "payload")
    except Exception:
        # Unit-test doubles are not SQLAlchemy-instrumented; direct assignment is enough there.
        pass


def _voice_audio_file(job_id: int) -> Path:
    return _AUDIO_DIR / f"tts_{job_id}.mp3"


def _seconds_since(timestamp: datetime | None) -> int:
    if timestamp is None:
        return 0
    from app.services.utils import get_now
    now = get_now()
    if timestamp.tzinfo is not None and timestamp.utcoffset() is not None:
        comparable_now = now.astimezone(timestamp.tzinfo)
        comparable_timestamp = timestamp
    else:
        comparable_now = now.replace(tzinfo=None)
        comparable_timestamp = timestamp.replace(tzinfo=None)
    return max(0, int((comparable_now - comparable_timestamp).total_seconds()))


def _normalize_voice_provider(provider: str | None) -> str:
    p = str(provider or "elevenlabs").strip().lower()
    return "elevenlabs" if p in {"elevenlabs", "auto"} else "elevenlabs"


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
            "Mình nghe bạn, và muốn đi cùng bạn từng bước. ... "
            "Mình mời bạn thử hít vào bốn giây, thở ra sáu giây, ... "
            "rồi nói với mình điều khó nhất ngay lúc này."
        )
    return (
        "Mình ở đây với bạn. ... "
        "Mình mời bạn hít một nhịp chậm, ... "
        "và chia sẻ điều đang làm bạn nặng lòng nhất lúc này."
    )


def cooldown_active(*, user_id: str, session_id: str | None) -> tuple[bool, int]:
    settings = get_settings()
    key = f"{user_id}:{session_id or '-'}"
    from app.services.utils import get_now
    now = get_now()
    last = _LAST_TRIGGER_AT.get(key)
    if not last:
        return False, 0
    remaining = int((last + timedelta(seconds=settings.proactive_voice_cooldown_seconds) - now).total_seconds())
    if remaining > 0:
        return True, remaining
    return False, 0


def mark_cooldown(*, user_id: str, session_id: str | None) -> None:
    key = f"{user_id}:{session_id or '-'}"
    from app.services.utils import get_now
    _LAST_TRIGGER_AT[key] = get_now()


def _model_hint_for_queue(settings: Any) -> str:
    return str(getattr(settings, "elevenlabs_model_id", "") or "eleven_multilingual_v2")


def _is_provider_level_block(code: str | None) -> bool:
    return bool(code and code in _PROVIDER_LEVEL_BLOCK_CODES)


def enqueue_voice_job(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    voice_script: str,
    trigger_reason: str,
    trigger_snapshot: dict[str, Any],
    persona_id: str | None = None,
    user_owns_voice_style: bool = False,
    risk_mode: str = "normal",
    voice_intent: str = "unspecified",
    priority: str = "normal",
    template_version: str = "voice_policy_v1",
) -> dict[str, Any]:
    global _VOICE_PROVIDER_BLOCKED_CODE
    settings = get_settings()
    provider = _normalize_voice_provider(getattr(settings, "tts_provider", "elevenlabs"))
    if _VOICE_PROVIDER_BLOCKED_CODE:
        logger.warning(
            "voice_job_disabled provider=%s reason=%s session_id=%s user_id=%s risk_level=%s tier=%s",
            provider,
            _VOICE_PROVIDER_BLOCKED_CODE,
            session_id,
            user_id,
            (trigger_snapshot or {}).get("risk_level"),
            (trigger_snapshot or {}).get("safety_tier"),
        )
        return {
            "provider": provider,
            "tts_job_id": None,
            "audio_url": None,
            "status": "provider_disabled",
            "voice_disabled": True,
            "model_id": _model_hint_for_queue(settings),
            "error_code": _VOICE_PROVIDER_BLOCKED_CODE,
            "error_message": "Voice provider hiện không khả dụng với cấu hình hiện tại. Hiển thị script text thay thế.",
        }
    # ── Dedup check ────────────────────────────────────────────────────────
    # Compute event signature and look for an existing reusable job before
    # creating a new SyncOutbox row. This prevents repeated identical audio
    # generation for SOS/crisis events and normal chat turns alike.
    voice_style_id = resolve_active_style(
        persona_id, user_owns_voice_style=user_owns_voice_style
    )
    voice_id = str(getattr(settings, "elevenlabs_voice_id", "") or "")
    signature = compute_event_signature(
        user_id=user_id,
        session_id=session_id,
        voice_style_id=voice_style_id,
        voice_script=voice_script,
        provider=provider,
        voice_id=voice_id,
        locale="vi",
        speech_rate=1.0,
        risk_mode=risk_mode,
        voice_intent=voice_intent,
        template_version=template_version,
    )
    existing = find_dedup_job(db, signature)
    if existing:
        dedup_status = dedup_status_for(existing["voice_status"])
        logger.info(
            "voice_job_dedup job_id=%s existing_id=%s voice_status=%s dedup_status=%s session_id=%s",
            f"tts_new",
            existing["tts_job_id"],
            existing["voice_status"],
            dedup_status,
            session_id,
        )
        return {
            "provider": provider,
            "tts_job_id": existing["tts_job_id"],
            "audio_url": existing.get("audio_url"),
            "status": dedup_status,
            "model_id": _model_hint_for_queue(settings),
            "requested_tts_provider": provider,
            "voice_style_id": voice_style_id,
            "event_signature": signature,
            "voice_script_hash": signature,
        }
    # ── Create new job ─────────────────────────────────────────────────────
    # Always create a fresh execution job id. Reuse belongs to result-cache layer,
    # not job identity, to keep lifecycle deterministic in distributed environments.
    outbox = SyncOutbox(
        event_type=VOICE_JOB_EVENT_TYPE,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "voice_script": voice_script,
            "trigger_reason": trigger_reason,
            "trigger_snapshot": trigger_snapshot,
                "voice": {
                    "status": "queued",
                    "requested_tts_provider": provider,
                    "event_signature": signature,
                    "voice_script_hash": signature,
                    "voice_style_id": voice_style_id,
                    "risk_mode": risk_mode,
                    "voice_intent": voice_intent,
                    "priority": priority,
                    "template_version": template_version,
                },
            },
        status="pending",
    )
    db.add(outbox)
    db.flush()
    job_id = int(outbox.outbox_id)
    db.commit()
    logger.info(
        "voice_job_enqueued job_id=%s session_id=%s user_id=%s trigger=%s distress=%s risk_level=%s tier=%s provider=%s auto_process=%s",
        job_id,
        session_id,
        user_id,
        trigger_reason,
        (trigger_snapshot or {}).get("distress_score"),
        (trigger_snapshot or {}).get("risk_level"),
        (trigger_snapshot or {}).get("safety_tier"),
        provider,
        bool(settings.voice_tts_auto_process_on_enqueue),
    )
    tts_job_id = f"tts_{job_id}"
    if settings.voice_tts_auto_process_on_enqueue:
        _start_voice_job_worker(job_id)
    return {
        "provider": provider,
        "tts_job_id": tts_job_id,
        "audio_url": None,
        "status": "queued",
        "model_id": _model_hint_for_queue(settings),
        "requested_tts_provider": provider,
        "voice_style_id": voice_style_id,
        "event_signature": signature,
        "voice_script_hash": signature,
    }


def _start_voice_job_worker(job_id: int) -> None:
    from app.services.utils import get_now
    now = get_now()
    owner_token = uuid.uuid4().hex
    with _INFLIGHT_LOCK:
        if job_id in _INFLIGHT_JOBS:
            started_at = _INFLIGHT_STARTED_AT.get(job_id)
            if started_at and (now - started_at).total_seconds() < VOICE_JOB_PROCESSING_STALE_SECONDS:
                return
            # Stale in-memory lock (thread crashed/hung) — reclaim it.
            _INFLIGHT_JOBS.discard(job_id)
            _INFLIGHT_STARTED_AT.pop(job_id, None)
            _INFLIGHT_OWNER.pop(job_id, None)
            logger.warning("voice_job_reclaim_stale_inflight_lock job_id=%s", job_id)
        _INFLIGHT_JOBS.add(job_id)
        _INFLIGHT_STARTED_AT[job_id] = now
        _INFLIGHT_OWNER[job_id] = owner_token
    th = threading.Thread(target=_process_job, args=(job_id, owner_token), daemon=True)
    th.start()


def _process_job(job_id: int, owner_token: str | None = None) -> None:
    logger.info("voice_job_thread_start job_id=%s instance=%s", job_id, _CR_INSTANCE)
    global _VOICE_PROVIDER_BLOCKED_CODE
    retry_immediately = False
    db = None
    try:
        factory = get_session_factory()
        db = factory()
        row = db.get(SyncOutbox, job_id)
        if not row or row.event_type != VOICE_JOB_EVENT_TYPE:
            logger.warning(
                "voice_job_row_missing job_id=%s row_found=%s event_type=%s instance=%s",
                job_id,
                row is not None,
                getattr(row, "event_type", None) if row else None,
                _CR_INSTANCE,
            )
            return
        payload = dict(row.payload or {})
        voice_script = str(payload.get("voice_script") or "").strip()
        logger.info("voice_job_start job_id=%s instance=%s", job_id, _CR_INSTANCE)
        row.status = "processing"
        from app.services.utils import get_now
        row.processing_started_at = get_now().replace(tzinfo=None)
        payload.setdefault("voice", {})
        payload["voice"]["status"] = "processing"
        _assign_payload(row, payload)
        db.commit()

        trigger_snap = dict(payload.get("trigger_snapshot") or {})
        tier = trigger_snap.get("safety_tier")
        tier_s = str(tier) if tier is not None else None
        raw_d = trigger_snap.get("distress_score")
        distress_f: float | None
        try:
            distress_f = float(raw_d) if raw_d is not None else None
        except (TypeError, ValueError):
            distress_f = None

        # Mask PII before any external TTS.
        safe_script = mask_pii(voice_script)
        settings = get_settings()
        provider = _normalize_voice_provider(getattr(settings, "tts_provider", "elevenlabs"))
        user_id = str(payload.get("user_id") or "")

        permanent_error_code: str | None = None
        try:
            tts_out = render_tts_audio(
                provider,
                safe_script,
                f"tts_{job_id}",
                distress_f,
                tier_s,
                user_id=user_id or None,
            )
        except PermanentTtsError as exc:
            tts_out = {
                "audio_path": "",
                "provider": "elevenlabs",
                "duration": 0.0,
                "chars": len(safe_script),
                "success": False,
                "fallback": False,
            }
            permanent_error_code = str(exc) or "tts_permanent_error"
            # Only provider-level config/auth failures should block future jobs globally.
            if _is_provider_level_block(permanent_error_code):
                _VOICE_PROVIDER_BLOCKED_CODE = permanent_error_code
            logger.warning(
                "voice_job_permanent_error job_id=%s code=%s distress=%s risk_level=%s tier=%s instance=%s",
                job_id,
                permanent_error_code,
                trigger_snap.get("distress_score"),
                trigger_snap.get("risk_level"),
                trigger_snap.get("safety_tier"),
                _CR_INSTANCE,
            )

        audio_path_str = str(tts_out.get("audio_path") or "").strip()
        audio_path = Path(audio_path_str) if audio_path_str else None

        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        payload["voice"]["actual_tts_provider"] = tts_out.get("provider")
        payload["voice"]["tts_chars"] = tts_out.get("chars")
        payload["voice"]["tts_success"] = tts_out.get("success")
        payload["voice"]["tts_fallback"] = tts_out.get("fallback")

        if audio_path and audio_path.exists():
            payload["voice"]["status"] = "ready"
            payload["voice"]["audio_path"] = str(audio_path)
            payload["voice"]["audio_url"] = f"/v1/chat/voice-jobs/tts_{job_id}/audio"
            payload["voice"].pop("error_code", None)
            payload["voice"].pop("error_message", None)
            row.status = "done"
            row.processed_at = get_now().replace(tzinfo=None)
            logger.info(
                "voice_job_complete job_id=%s chars=%s instance=%s",
                job_id,
                tts_out.get("chars"),
                _CR_INSTANCE,
            )
        elif permanent_error_code:
            # Provider is permanently unavailable — mark failed immediately, no retries.
            payload["voice"]["status"] = "failed"
            payload["voice"]["error_code"] = permanent_error_code
            payload["voice"]["error_message"] = (
                "Nhà cung cấp voice từ chối yêu cầu ở gói hiện tại. Hiển thị script text thay thế."
            )
            row.status = "failed"
            logger.warning(
                "voice_job_failed_permanent job_id=%s code=%s instance=%s",
                job_id,
                permanent_error_code,
                _CR_INSTANCE,
            )
        else:
            row.retry_count = int(row.retry_count or 0) + 1
            if row.retry_count >= VOICE_MAX_RETRIES:
                # Exhausted retries — surface failure to frontend.
                payload["voice"]["status"] = "failed"
                row.status = "failed"
                logger.warning(
                    "voice_job_failed_retry_exhausted job_id=%s retry_count=%s instance=%s",
                    job_id,
                    row.retry_count,
                    _CR_INSTANCE,
                )
            else:
                # Transient failure — keep polling-friendly status so frontend waits.
                payload["voice"]["status"] = "queued"
                row.status = "pending"
                if bool(getattr(settings, "voice_tts_auto_process_on_enqueue", False)):
                    retry_immediately = True
                logger.info(
                    "voice_job_retry_scheduled job_id=%s retry_count=%s instance=%s",
                    job_id,
                    row.retry_count,
                    _CR_INSTANCE,
                )
        _assign_payload(row, payload)
        db.commit()
    except Exception as exc:
        logger.exception("voice tts job %s failed unexpectedly", job_id)
        try:
            if db is None:
                raise RuntimeError("db session was never created")
            row = db.get(SyncOutbox, job_id)
            if row and row.event_type == VOICE_JOB_EVENT_TYPE:
                payload = dict(row.payload or {})
                payload.setdefault("voice", {})
                payload["voice"]["status"] = "failed"
                payload["voice"]["error_code"] = "tts_worker_exception"
                payload["voice"]["error_message"] = "Voice worker gặp lỗi nội bộ khi xử lý TTS job."
                _assign_payload(row, payload)
                row.status = "failed"
                db.commit()
        except Exception as write_exc:
            logger.warning("voice tts job %s failed to persist failure state: %s", job_id, write_exc)
    finally:
        if db is not None:
            db.close()
        tts_id = f"tts_{job_id}"
        with _INFLIGHT_LOCK:
            active_owner = _INFLIGHT_OWNER.get(job_id)
            if owner_token is None:
                # Watchdog/leased execution path does not claim in-memory ownership lock.
                # Keep ownership-aware cleanup for thread-dispatched path only.
                pass
            elif active_owner == owner_token:
                _INFLIGHT_JOBS.discard(job_id)
                _INFLIGHT_STARTED_AT.pop(job_id, None)
                _INFLIGHT_OWNER.pop(job_id, None)
        if retry_immediately:
            _start_voice_job_worker(job_id)


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
    voice_status = str(voice.get("status") or row.status)
    created_age_seconds = _seconds_since(getattr(row, "created_at", None))
    processing_age_seconds = _seconds_since(
        getattr(row, "processing_started_at", None) or getattr(row, "created_at", None)
    )

    audio_path_from_payload = Path(str(voice.get("audio_path"))) if voice.get("audio_path") else None
    has_ready_audio = bool(
        voice.get("audio_url")
        or (audio_path_from_payload and audio_path_from_payload.exists())
        or _voice_audio_file(outbox_id).exists()
    )

    if row.status == "done" and (voice_status != "ready" or has_ready_audio):
        if has_ready_audio:
            audio_path = audio_path_from_payload if audio_path_from_payload and audio_path_from_payload.exists() else _voice_audio_file(outbox_id)
            voice["status"] = "ready"
            if audio_path.exists():
                voice["audio_path"] = str(audio_path)
            voice["audio_url"] = voice.get("audio_url") or f"/v1/chat/voice-jobs/tts_{outbox_id}/audio"
            voice.pop("error_code", None)
            voice.pop("error_message", None)
            payload["voice"] = voice
            _assign_payload(row, payload)
            db.commit()
            if voice_status != "ready":
                logger.warning(
                    "voice_job_repaired_done_payload job_id=%s previous_voice_status=%s",
                    outbox_id,
                    voice_status,
                )
            voice_status = "ready"

    if row.status == "done" and voice_status in {"queued", "processing", "pending"}:
        audio_path = _voice_audio_file(outbox_id)
        if audio_path.exists():
            voice["status"] = "ready"
            voice["audio_path"] = str(audio_path)
            voice["audio_url"] = f"/v1/chat/voice-jobs/tts_{outbox_id}/audio"
            payload["voice"] = voice
            _assign_payload(row, payload)
            db.commit()
            logger.warning(
                "voice_job_repaired_done_payload job_id=%s previous_voice_status=%s",
                outbox_id,
                voice_status,
            )
            voice_status = "ready"
        else:
            voice["status"] = "failed"
            voice["error_code"] = "voice_done_missing_audio"
            voice["error_message"] = "Voice job marked done but generated audio was missing."
            payload["voice"] = voice
            _assign_payload(row, payload)
            row.status = "failed"
            db.commit()
            logger.warning("voice_job_done_missing_audio job_id=%s", outbox_id)
            voice_status = "failed"

    if row.status == "processing" and processing_age_seconds >= VOICE_JOB_PROCESSING_STALE_SECONDS:
        voice["status"] = "failed"
        voice["error_code"] = "stale_lock"
        voice["error_message"] = "Voice job xử lý quá lâu; hệ thống đã đánh dấu thất bại."
        payload["voice"] = voice
        _assign_payload(row, payload)
        row.status = "failed"
        db.commit()
        logger.warning(
            "voice_job_failed_stale_processing job_id=%s age_seconds=%s",
            outbox_id,
            processing_age_seconds,
        )
        voice_status = "failed"

    settings = get_settings()
    if row.status == "pending" and voice_status == "queued":
        if created_age_seconds >= VOICE_JOB_PENDING_TIMEOUT_SECONDS:
            voice["status"] = "failed"
            voice["error_code"] = "voice_job_timeout"
            voice["error_message"] = "Voice job xếp hàng quá lâu, hệ thống đã hủy và chuyển fallback text."
            payload["voice"] = voice
            _assign_payload(row, payload)
            row.status = "failed"
            db.commit()
            logger.warning(
                "voice_job_timeout_failed job_id=%s age_seconds=%s",
                outbox_id,
                created_age_seconds,
            )
            voice_status = "failed"
        elif bool(getattr(settings, "voice_tts_auto_process_on_enqueue", False)):
            _start_voice_job_worker(outbox_id)
            logger.info(
                "voice_job_self_heal_kick job_id=%s age_seconds=%s",
                outbox_id,
                created_age_seconds,
            )
    return {
        "tts_job_id": tts_job_id,
        "user_id": payload.get("user_id"),
        "status": str(voice.get("status") or voice_status or row.status),
        "audio_url": voice.get("audio_url"),
        "audio_data_uri": (
            "data:audio/mpeg;base64," + base64.b64encode(Path(str(voice.get("audio_path"))).read_bytes()).decode("ascii")
            if voice.get("audio_path") and Path(str(voice.get("audio_path"))).exists()
            else None
        ),
        "trigger_reason": payload.get("trigger_reason"),
        "error_code": voice.get("error_code"),
        "error_message": voice.get("error_message"),
        "actual_tts_provider": voice.get("actual_tts_provider"),
        "requested_tts_provider": voice.get("requested_tts_provider"),
        "tts_chars": voice.get("tts_chars"),
        "tts_fallback": voice.get("tts_fallback"),
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
    rows = db.scalars(
        select(SyncOutbox).where(
            SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE,
            SyncOutbox.status == "processing",
        )
    ).all()
    count = 0
    for row in rows:
        processing_age_seconds = _seconds_since(
            getattr(row, "processing_started_at", None) or getattr(row, "created_at", None)
        )
        if processing_age_seconds < stale_after_seconds:
            continue
        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        payload["voice"]["status"] = "failed"
        payload["voice"]["error_code"] = "stale_lock"
        payload["voice"]["error_message"] = "Voice job processing quá lâu; worker đã giải phóng lock."
        _assign_payload(row, payload)
        row.status = "failed"
        count += 1
    if count:
        db.commit()
    return count


def lease_pending_voice_jobs(db: Session, *, limit: int = 20) -> list[int]:
    from app.services.utils import get_now
    claimed_at = get_now().replace(tzinfo=None)
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
        row.processing_started_at = claimed_at
        row.retry_count = int(row.retry_count or 0) + 1
        payload = dict(row.payload or {})
        payload.setdefault("voice", {})
        payload["voice"]["status"] = "processing"
        _assign_payload(row, payload)
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
