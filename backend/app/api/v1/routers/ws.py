"""
WebSocket Notifications Endpoint
Real-time notification delivery via WebSocket
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, Cookie
from sqlalchemy.orm import Session

from app.services.db.session import get_db
from app.services.db.models import User
from app.services.security import decode_token
from app.core.errors import AppError
from app.services.ws_manager import connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/ws", tags=["websocket"])


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
    db: Session = Depends(get_db),
    token: str = Query(default=None),  # Optional query param for token fallback
):
    """
    WebSocket endpoint for real-time notifications
    
    Connection methods:
    1. **Cookie-based (Recommended)**: Browser automatically sends HTTP-only access_token cookie
       URL: ws://localhost:8000/v1/ws/notifications
       
    2. **Query parameter (Dev/Testing)**: Pass token explicitly
       URL: ws://localhost:8000/v1/ws/notifications?token={jwt_token}
    
    Events sent to client:
    - type: "notification" - Real-time notification with payload
    - type: "connected" - Welcome message after successful connection
    - type: "ping" - Heartbeat every 30s
    
    Payload examples:
    {
        "notification_id": "notif_xxx",
        "notification_type": "letter.replied",
        "title": "You have a reply!",
        "body": "Someone replied to your letter",
        "data": {"letter_id": "letter_xxx", "reply_id": "reply_xxx"}
    }
    """
    
    user = None
    user_id = None
    
    try:
        # Try cookie-based auth first (recommended)
        user = await get_current_user_ws_cookie(None, db)
        
        # Fallback to query parameter if no cookie
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
            await websocket.close(code=4001, reason="Unauthorized")
            logger.warning(f"WebSocket connection rejected: unauthorized")
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
