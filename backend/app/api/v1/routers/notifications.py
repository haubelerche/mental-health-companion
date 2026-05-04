from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import ok
from app.services.db.models import UserNotification, User
from app.services.db.session import get_db

router = APIRouter(tags=["notifications"])

@router.get("/notifications")
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0
):
    """Lấy danh sách thông báo của người dùng hiện tại."""
    query = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == current_user.user_id)
        .order_by(desc(UserNotification.created_at))
    )
    
    total = query.count()
    items = query.limit(limit).offset(offset).all()
    
    unread_count = (
        db.query(func.count(UserNotification.notification_id))
        .filter(UserNotification.user_id == current_user.user_id, UserNotification.is_read == False)
        .scalar()
    ) or 0

    return ok({
        "notifications": [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "body": n.body,
                "notification_type": n.notification_type,
                "payload": n.data_json,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() + "Z",
            }
            for n in items
        ],
        "total": total,
        "unread_count": unread_count,
        "has_more": (offset + limit) < total
    })

@router.post("/notifications/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đánh dấu một thông báo là đã đọc."""
    notification = (
        db.query(UserNotification)
        .filter(UserNotification.notification_id == notification_id, UserNotification.user_id == current_user.user_id)
        .first()
    )
    if notification:
        notification.is_read = True
        db.commit()
    
    return ok({"status": "success"})

@router.post("/notifications/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đánh dấu tất cả thông báo của user là đã đọc."""
    db.query(UserNotification).filter(
        UserNotification.user_id == current_user.user_id,
        UserNotification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    return ok({"status": "success"})
