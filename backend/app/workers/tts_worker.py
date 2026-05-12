from __future__ import annotations

from app.services.observability import record_event, record_metric
from app.services.schemas.contracts import WorkerJob


def process_tts_job(job: WorkerJob, *, provider_enabled: bool = True) -> dict:
    if not provider_enabled:
        record_event("tts.provider_disabled", metadata={"worker_type": "tts_render", "reason_code": "provider_disabled"})
        record_metric("tts_terminal_resolution_total", 1, labels={"worker_type": "tts_render", "status": "provider_disabled"})
        return {
            "job_id": job.job_id,
            "status": "failed",
            "reason": "provider_disabled",
            "audio_ready": False,
        }
    payload_ref = str(job.payload_ref or "")
    if not payload_ref:
        record_event("tts.render_failed", metadata={"worker_type": "tts_render", "reason_code": "missing_payload_ref"})
        return {
            "job_id": job.job_id,
            "status": "failed",
            "reason": "missing_payload_ref",
            "audio_ready": False,
        }
    record_metric("tts_terminal_resolution_total", 1, labels={"worker_type": "tts_render", "status": "succeeded"})
    return {
        "job_id": job.job_id,
        "status": "succeeded",
        "audio_ready": True,
        "reason": "tts_rendered",
    }
