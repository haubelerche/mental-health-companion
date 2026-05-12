import asyncio
import logging
from typing import Any, Dict
from sqlalchemy.orm import Session
from app.services.db.models import SyncOutbox, UserNotification
from app.services.utils import make_id, get_now

logger = logging.getLogger(__name__)

def enqueue_notification(db: Session, user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    OBSOLETE: Do not use for new features.
    Legacy method that uses SyncOutbox (processed by background worker).
    """
    logger.warning(f"Legacy enqueue_notification called for user {user_id}, type {event_type}. Migration to instant delivery recommended.")
    notification = SyncOutbox(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
        status="pending"
    )
    db.add(notification)

from fastapi import BackgroundTasks

def send_instant_notification(
    db: Session, 
    user_id: str, 
    event_type: str, 
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks | None = None
) -> None:
    """
    Saves UserNotification directly and triggers WebSocket push.
    If background_tasks is provided, push is deferred until after response/commit.
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
            created_at=get_now(),
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
        
        if background_tasks:
            background_tasks.add_task(_trigger_ws_push, user_id, notification_payload)
        else:
            _trigger_ws_push(user_id, notification_payload)
            
        logger.info(f"Instant notification prepared: user={user_id} type={event_type}")
        
    except Exception as e:
        logger.error(f"Failed to create instant notification: {e}")

async def async_send_instant_notification(
    db: Session, 
    user_id: str, 
    event_type: str, 
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks | None = None
) -> None:
    """
    Async version. If background_tasks is provided, push is deferred.
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
            created_at=get_now(),
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
        
        if background_tasks:
            background_tasks.add_task(connection_manager.send_notification, user_id, notification_payload)
        else:
            await connection_manager.send_notification(user_id, notification_payload)
            
        logger.info(f"Async instant notification prepared: user={user_id} type={event_type}")
        
    except Exception as e:
        logger.error(f"Failed to create async instant notification: {e}")

def bulk_send_instant_notifications(
    db: Session, 
    user_ids: list[str], 
    event_type: str, 
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks | None = None
) -> None:
    """
    Efficiently sends notifications to multiple users.
    If background_tasks is provided, pushes are deferred.
    """
    from app.services.notification_dispatcher import dispatcher
    
    template = dispatcher.NOTIFICATION_TEMPLATES.get(event_type)
    if not template:
        logger.warning(f"No notification template for event type: {event_type}")
        return

    body = payload.get("message") or template["body"]
    title = payload.get("title") or template["title"]
    now = get_now()

    notifications = []
    push_data = []

    for user_id in user_ids:
        notification_id = make_id("notif")
        notif = UserNotification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=template["notification_type"],
            title=title,
            body=body,
            data_json=payload,
            is_read=False,
            created_at=now,
        )
        notifications.append(notif)
        push_data.append((user_id, {
            "notification_id": notification_id,
            "notification_type": template["notification_type"],
            "title": title,
            "body": body,
            "data": payload,
            "created_at": now.isoformat(),
        }))

    try:
        db.add_all(notifications)
        db.flush()
        
        for user_id, notification_payload in push_data:
            if background_tasks:
                background_tasks.add_task(_trigger_ws_push, user_id, notification_payload)
            else:
                _trigger_ws_push(user_id, notification_payload)
            
        logger.info(f"Bulk instant notifications prepared: count={len(user_ids)} type={event_type}")
    except Exception as e:
        logger.error(f"Failed to send bulk instant notifications: {e}")


def _trigger_ws_push(user_id: str, payload: dict):

    """Internal helper to fire-and-forget the WS push from both sync/async contexts"""
    from app.services.ws_manager import connection_manager
    try:
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not in an async context, try to get loop from thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                pass

        if loop and loop.is_running():
            # If we have a running loop, schedule the task
            asyncio.run_coroutine_threadsafe(connection_manager.send_notification(user_id, payload), loop)
        else:
            # If no running loop is found, we might be in a purely synchronous worker thread.
            logger.debug(f"No active event loop found for WS push to {user_id}. Real-time delivery might be delayed.")
            
    except Exception as e:
        logger.warning(f"Could not trigger WS push: {e}")

