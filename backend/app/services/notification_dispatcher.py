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
            "title": "📬 Bạn có phản hồi mới!",
            "body": "Ai đó vừa trả lời lá thư ẩn danh của bạn.",
        },
        "letter.reported": {
            "notification_type": "letter.reported",
            "title": "⚠️ Lá thư bị báo cáo",
            "body": "Lá thư của bạn đã bị một người dùng khác báo cáo.",
        },
        "letter.received": {
            "notification_type": "letter.received",
            "title": "💌 Bạn nhận được thư",
            "body": "Có một lá thư ẩn danh mới dành cho bạn.",
        },
        "reward.earned": {
            "notification_type": "reward.earned",
            "title": "❤️ Bạn nhận được Tim!",
            "body": "Số dư Tim của bạn vừa tăng thêm từ hoạt động hệ thống.",
        },
        "memory.completed": {
            "notification_type": "memory.completed",
            "title": "📚 Ký ức mới được ghi lại",
            "body": "AI vừa hoàn thành việc ghi nhớ thêm thông tin về bạn.",
        },
        "persona.unlocked": {
            "notification_type": "persona.unlocked",
            "title": "🎭 Nhân vật mới đã sẵn sàng!",
            "body": "Chúc mừng! Bạn đã mở khóa thành công một nhân vật mới.",
        },
        "letter.reacted": {
            "notification_type": "letter.reacted",
            "title": "✨ Phản hồi được yêu thích",
            "body": "Ai đó vừa thả tim vào phản hồi thư của bạn.",
        },
        "crisis.detected": {
            "notification_type": "crisis.detected",
            "title": "🛡️ Friend luôn ở đây",
            "body": "Mình nhận thấy bạn đang gặp khó khăn. Đừng quên mình luôn sẵn sàng lắng nghe nhé.",
        },
        "admin.broadcast": {
            "notification_type": "admin.broadcast",
            "title": "📢 Thông báo hệ thống",
            "body": "Bạn có một thông báo mới từ ban quản trị.",
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

        # Use message from payload if available, else use template body
        body = payload.get("message") or template["body"]
        title = payload.get("title") or template["title"]

        try:
            # Create notification record in DB
            notification_id = make_id("notif")
            notification = UserNotification(
                notification_id=notification_id,
                user_id=user_id,
                notification_type=template["notification_type"],
                title=title,
                body=body,
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
                "title": title,
                "body": body,
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
