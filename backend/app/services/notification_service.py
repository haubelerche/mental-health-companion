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
    Saves UserNotification directly and triggers WebSocket push (fire-and-forget).
    """
    from app.services.notification_dispatcher import dispatcher
    
    template = dispatcher.NOTIFICATION_TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"No notification template for event type: {event_type}")
        return

    body = payload.get("message") or template["body"]
    title = payload.get("title") or template["title"]

    try:
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
        db.flush()
        
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

async def async_send_instant_notification(db: Session, user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Async version of send_instant_notification.
    Saves UserNotification directly and awaits WebSocket push.
    """
    from app.services.notification_dispatcher import dispatcher
    from app.services.ws_manager import connection_manager
    
    template = dispatcher.NOTIFICATION_TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"No notification template for event type: {event_type}")
        return

    body = payload.get("message") or template["body"]
    title = payload.get("title") or template["title"]

    try:
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
        db.flush()
        
        notification_payload = {
            "notification_id": notification_id,
            "notification_type": template["notification_type"],
            "title": title,
            "body": body,
            "data": payload,
            "created_at": notification.created_at.isoformat(),
        }
        
        await connection_manager.send_notification(user_id, notification_payload)
        
    except Exception as e:
        logger.error(f"Failed to create async instant notification: {e}")

def _trigger_ws_push(user_id: str, payload: dict):
    """Internal helper to fire-and-forget the WS push from both sync/async contexts"""
    from app.services.ws_manager import connection_manager
    try:
        # Get the running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, might be in a thread
            loop = asyncio.get_event_loop()

        if loop.is_running():
            # If we are in a different thread (like a sync FastAPI endpoint), 
            # we must use run_coroutine_threadsafe
            asyncio.run_coroutine_threadsafe(connection_manager.send_notification(user_id, payload), loop)
        else:
            # Fallback for scripts or non-running loops
            asyncio.run(connection_manager.send_notification(user_id, payload))
    except Exception as e:
        logger.warning(f"Could not trigger WS push: {e}")
