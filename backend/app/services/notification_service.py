import asyncio
import logging
from typing import Any, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.db.models import SyncOutbox, UserNotification
from app.services.utils import make_id, get_now

logger = logging.getLogger(__name__)

def enqueue_notification(db: Session, user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    DEPRECATED: Use send_instant_notification instead for real-time delivery.
    Legacy method that uses SyncOutbox.
    """
    notification = SyncOutbox(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
        status="pending"
    )
    db.add(notification)

def send_instant_notification(db: Session, user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    OPTIMIZED: Saves UserNotification directly and triggers WebSocket push.
    This is synchronous for DB operations but triggers an async task for WS push.
    """
    from app.services.notification_dispatcher import dispatcher
    
    # 1. Get template
    template = dispatcher.NOTIFICATION_TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"No notification template for event type: {event_type}")
        return

    body = payload.get("message") or template["body"]
    title = payload.get("title") or template["title"]

    try:
        # 2. Create UserNotification record (Sync)
        notification_id = make_id("notif")
        notification = UserNotification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=template["notification_type"],
            title=title,
            body=body,
            data_json=payload,
            is_read=False,
            created_at=get_now().replace(tzinfo=None),
        )
        db.add(notification)
        # We don't commit here, the caller handles the transaction
        
        # 3. Trigger WebSocket Push (Async)
        notification_payload = {
            "notification_id": notification_id,
            "notification_type": template["notification_type"],
            "title": title,
            "body": body,
            "data": payload,
            "created_at": notification.created_at.isoformat(),
        }
        
        _trigger_ws_push(user_id, notification_payload)
        
    except Exception as e:
        logger.error(f"Failed to create instant notification: {e}")

def _trigger_ws_push(user_id: str, payload: dict):
    """Internal helper to fire-and-forget the WS push"""
    from app.services.ws_manager import connection_manager
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(connection_manager.send_notification(user_id, payload))
        else:
            # Should not happen in FastAPI but good for safety
            asyncio.run(connection_manager.send_notification(user_id, payload))
    except Exception as e:
        logger.warning(f"Could not trigger WS push: {e}")
