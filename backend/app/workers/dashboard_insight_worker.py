from __future__ import annotations

from app.services.observability import record_event, record_metric
from app.services.schemas.contracts import WorkerJob


def process_dashboard_job(job: WorkerJob) -> dict:
    payload_ref = str(job.payload_ref or "")
    evidence_ok = ":" in payload_ref and len(payload_ref.split(":", 1)[1]) > 0
    if not evidence_ok:
        record_event("dashboard.insight_skipped_insufficient_evidence", metadata={"worker_type": "dashboard_insight", "reason_code": "insufficient_payload_ref"})
    record_metric("dashboard_insight_materialized_total", 1 if evidence_ok else 0, labels={"worker_type": "dashboard_insight", "status": "succeeded" if evidence_ok else "failed"})
    return {
        "job_id": job.job_id,
        "status": "succeeded" if evidence_ok else "failed",
        "insight_written": evidence_ok,
        "reason_code": "dashboard_insight_materialized" if evidence_ok else "insufficient_payload_ref",
    }
