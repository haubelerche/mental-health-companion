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


async def _dispatch_async(event: SyncOutbox, db: Session) -> None:
    """
    Dispatch outbox event to appropriate handler (Async version).
    """
    event_name = str(event.event_type or "")
    
    if event_name in NOTIFICATION_EVENT_TYPES:
        try:
            from app.services.notification_dispatcher import dispatch_notification_event
            # Call dispatcher directly since we are already in an async context
            await dispatch_notification_event(event, db)
        except Exception as e:
            logger.error(f"Failed to dispatch notification event {event.outbox_id}: {e}")
        return

async def process_outbox_batch_async(limit: int = 50) -> int:
    """Process a batch of events asynchronously"""
    factory = get_session_factory()
    db = factory()
    processed = 0
    try:
        # Fetch and lock pending rows so concurrent workers do not process the same batch.
        rows = db.scalars(
            select(SyncOutbox)
            .where(SyncOutbox.status == "pending")
            .order_by(SyncOutbox.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()

        if not rows:
            return 0

        # Release the DB lock before any network I/O so other workers can claim new rows.
        claimed_at = utc_now().replace(tzinfo=None)
        for row in rows:
            row.status = "processing"
            row.processing_started_at = claimed_at
        db.commit()

        for row in rows:
            try:
                await _dispatch_async(row, db)
                row.status = "done"
                row.processed_at = utc_now().replace(tzinfo=None)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing outbox {row.outbox_id}: {e}")
                row.retry_count = int(row.retry_count or 0) + 1
                row.status = "failed" if row.retry_count >= 3 else "pending"
            finally:
                db.commit()
        return processed
    finally:
        db.close()

async def run_outbox_worker_loop_async(poll_seconds: float = 1.0) -> None:
    """
    High-performance async loop for outbox worker.
    """
    logger.info("Starting Async Outbox Worker (Low Latency)...")
    while True:
        try:
            count = await process_outbox_batch_async()
            
            # Adaptive backoff
            if count > 0:
                # If we are busy, process next batch almost immediately
                await asyncio.sleep(0.05)
            else:
                # If idle, wait for the poll interval
                await asyncio.sleep(poll_seconds)
                
        except Exception as exc:
            logger.error(f"Outbox worker loop error: {exc}")
            await asyncio.sleep(2)

def run_outbox_worker_loop(poll_seconds: float = 1.0) -> None:
    """Entry point to run the async loop from sync code"""
    asyncio.run(run_outbox_worker_loop_async(poll_seconds))
