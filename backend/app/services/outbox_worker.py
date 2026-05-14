from __future__ import annotations

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import SyncOutbox
from app.services.db.session import get_session_factory
from app.services.utils import get_now

logger = logging.getLogger(__name__)

# NOTE: Notification event types are now handled in real-time via notification_service.
# Keep this explicit empty allow-list so the worker never claims graph, voice,
# memory, or other unrelated outbox events by accident.
NOTIFICATION_EVENT_TYPES: tuple[str, ...] = ()

async def _dispatch_async(event: SyncOutbox, db: Session) -> None:
    """
    Dispatch outbox event to appropriate handler (Async version).
    """
    event_name = str(event.event_type or "")
    
    # Placeholder for future notification outbox events
    if event_name in NOTIFICATION_EVENT_TYPES:
        # Handle other events here
        pass
    else:
        logger.warning(f"Outbox event_type is unhandled: {event_name}")
        raise ValueError(f"Unhandled outbox event_type: {event_name}")

async def process_outbox_batch_async(limit: int = 50) -> int:
    """Process a batch of events asynchronously"""
    if not NOTIFICATION_EVENT_TYPES:
        # Optimization: if no event types are registered, don't even query the DB
        return 0
        
    factory = get_session_factory()
    db = factory()
    processed = 0
    try:
        rows = db.scalars(
            select(SyncOutbox)
            .where(
                SyncOutbox.status == "pending",
                SyncOutbox.event_type.in_(NOTIFICATION_EVENT_TYPES),
            )
            .order_by(SyncOutbox.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()

        if not rows:
            return 0

        claimed_at = get_now().replace(tzinfo=None)
        for row in rows:
            row.status = "processing"
            row.processing_started_at = claimed_at
        db.commit()

        for row in rows:
            try:
                await _dispatch_async(row, db)
                row.status = "done"
                row.processed_at = get_now().replace(tzinfo=None)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing outbox {row.outbox_id}: {e}")
                row.retry_count = int(row.retry_count or 0) + 1
                row.error_message = str(e)[:1000]
                row.status = "failed" if row.retry_count >= 3 else "pending"
            finally:
                db.commit()
        return processed
    finally:
        db.close()

async def run_outbox_worker_loop_async(poll_seconds: float = 5.0) -> None:
    """
    High-performance async loop for outbox worker.
    """
    logger.info("Starting Async Outbox Worker (Idle - Notifications migrated to Real-time)...")
    while True:
        try:
            count = await process_outbox_batch_async()
            
            if count > 0:
                await asyncio.sleep(0.05)
            else:
                # Use a longer poll interval when idle
                await asyncio.sleep(poll_seconds)
                
        except Exception as exc:
            logger.error(f"Outbox worker loop error: {exc}")
            await asyncio.sleep(5)

def run_outbox_worker_loop(poll_seconds: float = 5.0) -> None:
    """Entry point to run the async loop from sync code"""
    asyncio.run(run_outbox_worker_loop_async(poll_seconds))
