from __future__ import annotations

from app.services.schemas.contracts import WorkerJob


def normalize_analyst_event(job: WorkerJob) -> dict:
    payload_ref = str(job.payload_ref or "")
    normalized_type = payload_ref.split(":", 1)[0] if ":" in payload_ref else "unknown"
    return {
        "job_id": job.job_id,
        "status": "succeeded",
        "normalized": True,
        "normalized_event_type": normalized_type,
    }

