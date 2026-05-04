from typing import Any, Dict
from sqlalchemy.orm import Session
from app.services.db.models import SyncOutbox

def enqueue_notification(db: Session, user_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Reusable utility to enqueue a notification into the SyncOutbox.
    The outbox_worker will automatically pick this up and dispatch via WebSocket.
    """
    notification = SyncOutbox(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
        status="pending"
    )
    db.add(notification)
    # Note: We don't commit here, the caller should commit as part of their transaction.
