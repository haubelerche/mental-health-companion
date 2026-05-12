"""
Notification Dispatcher (Constants & Direct Delivery)
Provides templates and direct WebSocket delivery logic for notifications.
Outbox worker logic has been removed as notifications are now real-time.
"""

import logging
from sqlalchemy.orm import Session
from app.services.db.models import UserNotification
from app.services.utils import make_id, get_now
from app.services.ws_manager import connection_manager

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    """Provides templates and direct WebSocket delivery logic for notifications."""

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

    async def dispatch_direct(self, user_id: str, event_type: str, payload: dict, db: Session) -> bool:
        """
        Create a notification and send it via WebSocket immediately.
        Used by notification_service for real-time delivery.
        """
        template = self.NOTIFICATION_TEMPLATES.get(event_type)
        if not template:
            logger.debug(f"No notification template for event type: {event_type}")
            return False

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

            await connection_manager.send_notification(user_id, notification_payload)
            logger.info(f"Instant notification dispatched: user_id={user_id}, type={event_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to dispatch instant notification: {e}")
            return False

# Global dispatcher instance
dispatcher = NotificationDispatcher()

