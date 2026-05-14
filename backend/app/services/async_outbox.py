from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import SyncOutbox
from app.services.observability import finish_trace, record_event, record_metric, start_span, start_trace
from app.services.schemas.contracts import WorkerJob
from app.services.utils import get_now
from app.analyst.jobs import process_analyst_run_job
from app.workers.analyst_event_worker import normalize_analyst_event
from app.workers.dashboard_insight_worker import process_dashboard_job
from app.workers.memory_worker import process_memory_job
from app.workers.tts_worker import process_tts_job

_TYPE_TO_EVENT = {
    "memory_extraction": "worker.memory_extraction",
    "dashboard_insight": "worker.dashboard_insight",
    "tts_render": "worker.tts_render",
    "analyst_event": "worker.analyst_event",
    "analyst_run": "worker.analyst_run",
}
_EVENT_TO_TYPE = {v: k for k, v in _TYPE_TO_EVENT.items()}
_MAX_ATTEMPTS = 3
_DB_STATUS_PENDING = "pending"
_DB_STATUS_PROCESSING = "processing"
_DB_STATUS_DONE = "done"
_DB_STATUS_FAILED = "failed"

_PROCESSORS = {
    "memory_extraction": process_memory_job,
    "dashboard_insight": process_dashboard_job,
    "tts_render": process_tts_job,
    "analyst_event": normalize_analyst_event,
    "analyst_run": process_analyst_run_job,
}


def _status_for_attempt(*, retry_count: int) -> str:
    return "failed" if retry_count >= _MAX_ATTEMPTS else "retrying"


def _matching_idempotency(row: SyncOutbox, key: str) -> bool:
    payload = dict(row.payload or {})
    return str(payload.get("idempotency_key") or "") == key


def enqueue_worker_job(db: Session, job: WorkerJob) -> int:
    event_type = _TYPE_TO_EVENT[job.job_type]
    rows = db.scalars(select(SyncOutbox).where(SyncOutbox.event_type == event_type)).all()
    for existed in rows:
        if _matching_idempotency(existed, job.idempotency_key):
            return int(existed.outbox_id)
    payload = job.model_dump(mode="json")
    payload["status"] = "queued"
    payload["attempt_count"] = int(payload.get("attempt_count") or 0)
    row = SyncOutbox(
        user_id=job.user_id,
        event_type=event_type,
        payload=payload,
        status=_DB_STATUS_PENDING,
        retry_count=0,
    )
    db.add(row)
    db.flush()
    record_event("worker.enqueued", metadata={"worker_type": job.job_type, "outbox_id": int(row.outbox_id)})
    return int(row.outbox_id)


def claim_pending_jobs(db: Session, *, limit: int = 20) -> list[SyncOutbox]:
    rows = db.scalars(
        select(SyncOutbox)
        .where(SyncOutbox.status == _DB_STATUS_PENDING, SyncOutbox.event_type.in_(tuple(_EVENT_TO_TYPE.keys())))
        .order_by(SyncOutbox.created_at.asc())
        .limit(limit)
    ).all()
    now = get_now().replace(tzinfo=None)
    for row in rows:
        row.status = _DB_STATUS_PROCESSING
        row.processing_started_at = now
        payload = dict(row.payload or {})
        payload["status"] = "processing"
        row.payload = payload
        queue_lag = max(0.0, (now - row.created_at).total_seconds()) if row.created_at else 0.0
        record_metric(
            "worker_lag_seconds",
            queue_lag,
            labels={"worker_type": _EVENT_TO_TYPE.get(str(row.event_type or ""), "unknown"), "status": "processing"},
            unit="seconds",
        )
    db.flush()
    return rows


def mark_job_succeeded(db: Session, row: SyncOutbox, *, metadata: dict | None = None) -> None:
    payload = dict(row.payload or {})
    if metadata:
        payload["result_meta"] = metadata
    payload["status"] = "succeeded"
    row.payload = payload
    row.status = _DB_STATUS_DONE
    row.processed_at = get_now().replace(tzinfo=None)
    db.flush()


def mark_job_failed(db: Session, row: SyncOutbox, *, reason: str) -> None:
    retry_count = int(row.retry_count or 0) + 1
    row.retry_count = retry_count
    safe_reason = (reason or "worker_failure")[:1000]
    row.error_message = safe_reason
    row.processed_at = get_now().replace(tzinfo=None)
    payload = dict(row.payload or {})
    payload["status"] = _status_for_attempt(retry_count=retry_count)
    payload["last_error_reason"] = safe_reason
    row.payload = payload
    row.status = _DB_STATUS_FAILED if retry_count >= _MAX_ATTEMPTS else _DB_STATUS_PENDING
    db.flush()


def to_worker_job(row: SyncOutbox) -> WorkerJob | None:
    event_type = str(row.event_type or "")
    job_type = _EVENT_TO_TYPE.get(event_type)
    if not job_type:
        return None
    payload = dict(row.payload or {})
    job_id = str(payload.get("job_id") or f"outbox:{row.outbox_id}")
    return WorkerJob(
        job_id=job_id,
        job_type=job_type,  # type: ignore[arg-type]
        user_id=str(row.user_id or payload.get("user_id") or ""),
        session_id=(str(payload.get("session_id")) if payload.get("session_id") is not None else None),
        payload_ref=str(payload.get("payload_ref") or ""),
        idempotency_key=str(payload.get("idempotency_key") or f"outbox-{row.outbox_id}"),
        status="processing",
        attempt_count=int(payload.get("attempt_count") or 0),
        trace_id=(str(payload.get("trace_id")) if payload.get("trace_id") else None),
        request_id=(str(payload.get("request_id")) if payload.get("request_id") else None),
    )


def touch_job_attempt(row: SyncOutbox, *, now: datetime | None = None) -> None:
    payload = dict(row.payload or {})
    payload["attempt_count"] = int(payload.get("attempt_count") or 0) + 1
    payload["attempted_at"] = (now or get_now()).isoformat()
    row.payload = payload


def process_claimed_job(db: Session, row: SyncOutbox) -> dict:
    """Run one claimed sync_outbox worker job and persist lifecycle outcome."""
    job = to_worker_job(row)
    if job is None:
        mark_job_failed(db, row, reason="unsupported_event_type")
        return {"status": "failed", "reason": "unsupported_event_type"}

    trace = start_trace(
        f"worker.{job.job_type}",
        trace_id=job.trace_id,
        request_id=job.request_id,
        user_id=job.user_id,
        session_id=job.session_id,
        metadata={"worker_type": job.job_type, "status": "processing"},
    )
    touch_job_attempt(row)
    processor = _PROCESSORS.get(job.job_type)
    if processor is None:
        mark_job_failed(db, row, reason="missing_processor")
        record_event("worker.failed", metadata={"worker_type": job.job_type, "reason_code": "missing_processor"})
        finish_trace(status="error", metadata={"worker_type": job.job_type, "status": "failed"})
        return {"job_id": job.job_id, "status": "failed", "reason": "missing_processor"}

    try:
        with start_span("worker.process", metadata={"worker_type": job.job_type, "attempt_count": int(row.retry_count or 0) + 1}):
            if job.job_type in {"memory_extraction", "analyst_run"}:
                result = processor(job, db=db)
            else:
                result = processor(job)
    except Exception as exc:  # pragma: no cover - defensive worker isolation
        mark_job_failed(db, row, reason=type(exc).__name__)
        record_event("worker.failed", metadata={"worker_type": job.job_type, "reason_code": type(exc).__name__})
        finish_trace(status="error", metadata={"worker_type": job.job_type, "status": "failed"})
        return {"job_id": job.job_id, "status": "failed", "reason": type(exc).__name__}

    if str(result.get("status") or "") == "succeeded":
        mark_job_succeeded(db, row, metadata={k: v for k, v in result.items() if k not in {"job_id", "status"}})
        record_metric("worker_terminal_total", 1, labels={"worker_type": job.job_type, "status": "succeeded"})
        finish_trace(status="ok", metadata={"worker_type": job.job_type, "status": "succeeded", "retry_count": int(row.retry_count or 0)})
    else:
        mark_job_failed(db, row, reason=str(result.get("reason") or result.get("reason_code") or "worker_failed"))
        terminal_status = str(dict(row.payload or {}).get("status") or "failed")
        record_event("worker.failed", metadata={"worker_type": job.job_type, "reason_code": str(result.get("reason") or result.get("reason_code") or "worker_failed")})
        record_metric("worker_terminal_total", 1, labels={"worker_type": job.job_type, "status": terminal_status})
        finish_trace(status="error", metadata={"worker_type": job.job_type, "status": terminal_status, "retry_count": int(row.retry_count or 0)})
    del trace
    return result


def run_worker_batch_once(db: Session, *, limit: int = 20) -> dict[str, int]:
    """Claim and process a bounded worker batch without raising into callers."""
    outcomes = {"claimed": 0, "succeeded": 0, "failed": 0, "retrying": 0}
    rows = claim_pending_jobs(db, limit=limit)
    outcomes["claimed"] = len(rows)
    for row in rows:
        result = process_claimed_job(db, row)
        status = str(result.get("status") or "failed")
        if status == "succeeded":
            outcomes["succeeded"] += 1
        elif str(dict(row.payload or {}).get("status")) == "retrying":
            outcomes["retrying"] += 1
        else:
            outcomes["failed"] += 1
    return outcomes
