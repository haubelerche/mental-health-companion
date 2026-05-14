from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.analyst.service import default_window_for_run, run_analyst_pipeline
from app.analyst.types import AnalystRunRequest
from app.services.observability import record_event
from app.services.schemas.contracts import WorkerJob
from app.services.utils import get_now


def process_analyst_run_job(job: WorkerJob, *, db: Session) -> dict:
    payload_ref = str(job.payload_ref or "")
    run_type = "turn"
    if payload_ref.startswith("analyst_run:"):
        run_type = payload_ref.split(":", 1)[1] or "turn"
    start, end = default_window_for_run(run_type, now=get_now())
    request = AnalystRunRequest(
        user_id=job.user_id,
        run_type=run_type,  # type: ignore[arg-type]
        window_start=start,
        window_end=end,
        data_cutoff_at=end,
        force=False,
    )
    result = run_analyst_pipeline(db, request)
    if result.status in {"completed", "skipped_insufficient_data"}:
        return {
            "job_id": job.job_id,
            "status": "succeeded",
            "run_id": result.run_id,
            "analyst_status": result.status,
            "created_insight_count": len(result.created_insight_ids),
        }
    record_event("analyst.run.failed", metadata={"run_id": result.run_id, "status": result.status})
    return {"job_id": job.job_id, "status": "failed", "run_id": result.run_id, "reason_code": result.status}


def build_refresh_job(*, user_id: str, run_type: str, request_id: str | None = None, trace_id: str | None = None) -> WorkerJob:
    now = get_now()
    stamp = now.isoformat()
    return WorkerJob(
        job_id=f"analyst_run_{user_id}_{run_type}_{int(datetime.timestamp(now))}",
        job_type="analyst_run",
        user_id=user_id,
        session_id=None,
        payload_ref=f"analyst_run:{run_type}",
        idempotency_key=f"analyst_run:{user_id}:{run_type}:{stamp[:13]}",
        status="queued",
        attempt_count=0,
        trace_id=trace_id,
        request_id=request_id,
    )
