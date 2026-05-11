"""Escalation helpers — bridge between content surfaces and the safety flow.

When a letter verdict is `safety_escalate`, the letter router calls
`record_safety_escalation_event()` to persist a safety event row and
enqueue a signal for the safety flow worker.

No direct LLM calls here. No direct SafetyFinalizer import to avoid
circular deps — the signal is passed via the outbox.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.utils import make_id


def _utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def record_safety_escalation_event(
    db: Session,
    *,
    user_id: str,
    source_surface: str,
    source_id: str,
    reason_codes: list[str],
) -> str:
    """Write a safety escalation marker to the outbox and return event_id.

    The outbox worker picks this up and routes it to the safety flow.
    We avoid writing to crisis_logs here — that's owned by SafetyFinalizer.
    """
    from app.services.db.models import SyncOutbox

    event_id = make_id("sev")
    payload = {
        "event_type": "safety_escalation",
        "event_id": event_id,
        "user_id": user_id,
        "source_surface": source_surface,
        "source_id": source_id,
        "reason_codes": reason_codes,
        "occurred_at": _utc_naive().isoformat(),
    }

    outbox_row = SyncOutbox(
        event_id=make_id("obx"),
        user_id=user_id,
        event_type="safety_escalation",
        payload=payload,
        created_at=_utc_naive(),
    )
    db.add(outbox_row)
    return event_id
