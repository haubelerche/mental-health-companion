from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy import select

from app.services.db.models import SyncOutbox
from app.services.db.session import get_session_factory
from app.services.utils import utc_now

logger = logging.getLogger(__name__)

# Notification event types that should be dispatched via WebSocket
NOTIFICATION_EVENT_TYPES = {
    "letter.replied",
    "letter.reported",
    "letter.received",
    "letter.reacted",
    "reward.earned",
    "memory.completed",
    "persona.unlocked",
    "crisis.detected",
}


def _dispatch(event: SyncOutbox) -> None:
    """
    Dispatch outbox event to appropriate handler.
    Notification events are sent to WebSocket clients via dispatcher.
    Other events are logged for specialized workers.
    """
    event_name = str(event.event_type or "")
    
    # Handle notification events
    if event_name in NOTIFICATION_EVENT_TYPES:
        try:
            # Import here to avoid circular imports
            from app.services.notification_dispatcher import dispatch_notification_event
            
            factory = get_session_factory()
            db = factory()
            try:
                # Run async dispatcher in sync context
                asyncio.run(dispatch_notification_event(event, db))
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to dispatch notification event {event.outbox_id}: {e}")
        return
    
    # Known event types that are handled by specialized workers
    if event_name in {"voice.tts_request", "memory.enrich", "trusted_contact.notify"}:
        return
    
    logger.debug("outbox.unknown_event_type=%s id=%s", event_name, event.outbox_id)


def process_outbox_batch(limit: int = 50) -> int:
    factory = get_session_factory()
    db = factory()
    processed = 0
    try:
        rows = db.scalars(
            select(SyncOutbox)
            .where(SyncOutbox.status == "pending")
            .order_by(SyncOutbox.created_at.asc())
            .limit(limit)
        ).all()
        for row in rows:
            try:
                _dispatch(row)
                row.status = "done"
                row.processed_at = utc_now().replace(tzinfo=None)
                processed += 1
            except Exception:
                row.retry_count = int(row.retry_count or 0) + 1
                row.status = "failed" if row.retry_count >= 3 else "pending"
        db.commit()
        return processed
    finally:
        db.close()


def run_outbox_worker_loop(poll_seconds: int = 10) -> None:
    while True:
        try:
            count = process_outbox_batch()
            if count:
                logger.info("outbox.processed=%d", count)
        except Exception as exc:
            logger.warning("outbox worker loop failed: %s", exc)
        time.sleep(max(1, poll_seconds))
