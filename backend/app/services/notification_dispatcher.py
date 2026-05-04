"""
Notification Dispatcher
Monitors SyncOutbox events and broadcasts them to connected WebSocket clients
"""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import SyncOutbox, UserNotification
from app.services.db.session import get_session_factory
from app.services.utils import make_id
from app.services.ws_manager import connection_manager

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Processes outbox events and routes them to WebSocket clients"""

    # Event type -> (notification type, title template, body template)
    NOTIFICATION_TEMPLATES = {
        "letter.replied": {
            "notification_type": "letter.replied",
            "title": "📬 You have a new reply!",
            "body": "Someone replied to your anonymous letter",
        },
        "letter.reported": {
            "notification_type": "letter.reported",
            "title": "⚠️ Your letter was reported",
            "body": "Your letter has been reported by another user",
        },
        "letter.received": {
            "notification_type": "letter.received",
            "title": "💌 You received a letter",
            "body": "Someone sent you an anonymous letter",
        },
        "reward.earned": {
            "notification_type": "reward.earned",
            "title": "❤️ You earned hearts!",
            "body": "You received hearts for your activity",
        },
        "memory.completed": {
            "notification_type": "memory.completed",
            "title": "📚 Memory card completed!",
            "body": "You've completed a memory card review",
        },
        "persona.unlocked": {
            "notification_type": "persona.unlocked",
            "title": "🎭 New persona unlocked!",
            "body": "You've unlocked a new persona",
        },
        "letter.reacted": {
            "notification_type": "letter.reacted",
            "title": "✨ Someone reacted to your reply",
            "body": "A user sent a reaction to your letter reply",
        },
        "crisis.detected": {
            "notification_type": "crisis.detected",
            "title": "🛡️ Safety Check",
            "body": "We detected you might be going through a hard time. We're here to help.",
        },
    }

    async def dispatch(self, event: SyncOutbox, db: Session) -> bool:
        """
        Process a single outbox event and send notifications to user
        Returns True if successfully handled, False if unknown event type
        """
        event_type = event.event_type
        payload = event.payload or {}
        user_id = event.user_id

        # Get template for event type
        template = self.NOTIFICATION_TEMPLATES.get(event_type)
        if not template:
            logger.debug(f"No notification template for event type: {event_type}")
            return False  # Unknown event, let outbox_worker mark as failed

        try:
            # Create notification record in DB
            notification_id = make_id("notif")
            notification = UserNotification(
                notification_id=notification_id,
                user_id=user_id,
                notification_type=template["notification_type"],
                title=template["title"],
                body=template["body"],
                data_json=payload,
                is_read=False,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(notification)
            db.commit()

            # Send via WebSocket if user is connected
            notification_payload = {
                "notification_id": notification_id,
                "notification_type": template["notification_type"],
                "title": template["title"],
                "body": template["body"],
                "data": payload,
                "created_at": notification.created_at.isoformat(),
            }

            await connection_manager.send_notification(user_id, notification_payload)
            logger.info(f"Notification dispatched: user_id={user_id}, type={event_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to dispatch notification: {e}")
            return False

    async def dispatch_batch(self, events: list[SyncOutbox], db: Session) -> dict:
        """
        Process a batch of events
        Returns: {"succeeded": count, "failed": count, "unknown": count}
        """
        results = {"succeeded": 0, "failed": 0, "unknown": 0}

        for event in events:
            try:
                handled = await self.dispatch(event, db)
                if handled:
                    results["succeeded"] += 1
                else:
                    results["unknown"] += 1
            except Exception as e:
                logger.error(f"Error processing event {event.outbox_id}: {e}")
                results["failed"] += 1

        return results


# Global dispatcher instance
dispatcher = NotificationDispatcher()


# Integration point: This should be called by outbox_worker.py _dispatch() function
async def dispatch_notification_event(event: SyncOutbox, db: Session) -> bool:
    """
    Entry point for outbox worker to dispatch notification events
    Called by outbox_worker._dispatch() when processing SyncOutbox events
    """
    return await dispatcher.dispatch(event, db)
