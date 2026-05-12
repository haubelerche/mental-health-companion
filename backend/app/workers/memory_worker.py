from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import Message
from app.services.longterm_memory import persist_turn_memory
from app.services.observability import record_event, record_metric
from app.services.schemas.contracts import WorkerJob


def _message_id_from_payload(payload_ref: str) -> str:
    if not payload_ref.startswith("messages:"):
        return ""
    return payload_ref.split(":", 1)[1].strip()


def process_memory_job(job: WorkerJob, db: Session | None = None) -> dict:
    # Worker remains internal: it returns structured status, never user-facing text.
    payload_ref = str(job.payload_ref or "")
    created = payload_ref.startswith("messages:") or payload_ref.startswith("conversation:")
    if db is not None and payload_ref.startswith("messages:"):
        assistant_message_id = _message_id_from_payload(payload_ref)
        assistant = db.scalar(select(Message).where(Message.message_id == assistant_message_id))
        if assistant is not None and str(assistant.role or "") == "assistant":
            user = db.scalars(
                select(Message)
                .where(Message.session_id == assistant.session_id, Message.user_id == assistant.user_id)
                .where(Message.role == "user")
                .where(Message.created_at <= assistant.created_at)
                .order_by(Message.created_at.desc())
                .limit(1)
            ).first()
            if user is not None:
                persist_turn_memory(
                    db,
                    user_id=str(assistant.user_id),
                    session_id=str(assistant.session_id),
                    user_message=str(user.content or ""),
                    assistant_reply=str(assistant.content or ""),
                    sos_triggered=bool(assistant.sos_triggered),
                )
                record_metric("memory_card_candidates_total", 1, labels={"worker_type": "memory_extraction", "status": "created"})
                return {
                    "job_id": job.job_id,
                    "status": "succeeded",
                    "created_memory_candidate": True,
                    "reason_code": "memory_candidate_persisted",
                }
    if not created:
        record_event("memory_card.rejected", metadata={"worker_type": "memory_extraction", "reason_code": "no_eligible_payload"})
    record_metric("memory_card_candidates_total", 1 if created else 0, labels={"worker_type": "memory_extraction", "status": "created" if created else "rejected"})
    return {
        "job_id": job.job_id,
        "status": "succeeded",
        "created_memory_candidate": created,
        "reason_code": "memory_candidate_extracted" if created else "no_eligible_payload",
    }
