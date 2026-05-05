"""
WebSocket Connection Manager
Manages all active WebSocket connections, routing notifications to specific users
"""

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket client connections by user_id"""

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_sessions: Dict[int, str] = {}  # id(WebSocket) -> user_id mapping

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register new WebSocket connection for a user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.user_sessions[id(websocket)] = user_id
        
        logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.active_connections[user_id])}")

    async def disconnect(self, websocket: WebSocket):
        """Unregister WebSocket connection"""
        ws_id = id(websocket)
        user_id = self.user_sessions.pop(ws_id, None)

        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user_id={user_id}")
            return

        # Fallback cleanup for partially registered sockets.
        for uid, websockets in list(self.active_connections.items()):
            if websocket in websockets:
                websockets.discard(websocket)
                if not websockets:
                    del self.active_connections[uid]
                self.user_sessions.pop(ws_id, None)
                logger.info(f"WebSocket disconnected via fallback cleanup: user_id={uid}")
                return

    async def send_notification(self, user_id: str, notification: dict):
        """Send notification to all WebSocket connections of a user"""
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user_id={user_id}")
            return
        
        message = json.dumps({
            "type": "notification",
            "payload": notification
        })
        
        disconnected = set()
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to user_id={user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected connections
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_notification(self, notification: dict, exclude_user: str = None):
        """Broadcast notification to all connected users"""
        message = json.dumps({
            "type": "notification",
            "payload": notification
        })
        
        disconnected = []
        for user_id, websockets in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            for websocket in websockets:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to user_id={user_id}: {e}")
                    disconnected.append((user_id, websocket))
        
        # Clean up disconnected connections
        for user_id, ws in disconnected:
            await self.disconnect(ws)

    def get_connected_users(self) -> list[str]:
        """Get list of all connected user IDs"""
        return list(self.active_connections.keys())

    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))


# Global singleton instance
connection_manager = ConnectionManager()
