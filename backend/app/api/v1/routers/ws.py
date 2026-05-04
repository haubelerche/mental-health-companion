"""
WebSocket Notifications Endpoint
Real-time notification delivery via WebSocket
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, Cookie
from sqlalchemy.orm import Session

from app.services.db.session import get_db
from app.services.db.models import User
from app.api.deps import get_current_user
from app.services.security import decode_token
from app.core.errors import AppError
from app.services.ws_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


async def get_current_user_ws_cookie(
    access_token: str | None = Cookie(default=None, alias="access_token"),
    db: Session = Depends(get_db),
) -> User | None:
    """Authenticate user for WebSocket via HTTP-only cookie (preferred for security)"""
    if not access_token:
        return None
    try:
        payload = decode_token(access_token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    from sqlalchemy import select
    user = db.scalar(select(User).where(User.user_id == user_id, User.is_active.is_(True)))
    return user


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user: User | None = Depends(get_current_user_ws_cookie),
    db: Session = Depends(get_db),
    token: str = Query(default=None),
):
    """
    WebSocket endpoint for real-time notifications
    """
    
    user_id = None
    
    try:
        # Fallback to query parameter if no cookie auth
        if not user and token:
            try:
                payload = decode_token(token)
                user_id = payload.get("sub")
                if user_id:
                    from sqlalchemy import select
                    user = db.scalar(select(User).where(User.user_id == user_id, User.is_active.is_(True)))
            except Exception:
                pass
        
        if not user:
            # We must accept first to be able to send a message before closing
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "message": "Unauthorized"
            })
            await websocket.close(code=4001)
            logger.warning("WebSocket connection rejected: unauthorized")
            return
        
        user_id = user.user_id
        
        # Register connection
        await connection_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connection established: user_id={user_id}")
        
        # Send welcome message
        import datetime
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notification stream",
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        # Listen for messages (client can send heartbeat confirmations or disconnect)
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from {user_id}: {data}")
            # Currently just echo heartbeat responses
            # Could extend with client commands in future
    
    except WebSocketDisconnect:
        if user_id:
            await connection_manager.disconnect(websocket)
            logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await connection_manager.disconnect(websocket)
        except:
            pass


@router.post("/test-notify")
async def trigger_test_notification(
    user_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a test notification for a specific user.
    If no user_id is provided, it uses the ID of the current authenticated user.
    """
    from app.services.db.models import SyncOutbox
    import datetime

    target_id = user_id or current_user.user_id

    # Create a dummy reward event as a test
    event = SyncOutbox(
        user_id=target_id,
        event_type="reward.earned",
        payload={
            "amount": 100,
            "message": "Đây là thông báo kiểm tra hệ thống WebSocket!",
            "test_time": datetime.datetime.utcnow().isoformat()
        },
        status="pending",
    )
    db.add(event)
    db.commit()
    
    return {
        "success": True, 
        "message": f"Test notification queued for user {target_id}",
        "outbox_id": event.outbox_id
    }
