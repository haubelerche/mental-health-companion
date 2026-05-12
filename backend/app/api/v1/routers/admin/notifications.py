from fastapi import Depends, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import User
from .shared import router, _audit

class BroadcastPayload(BaseModel):
    title: str | None = None
    body: str
    category: str = "general" # morning, reminder, etc.

@router.post("/notifications/broadcast")
async def admin_broadcast_notification(
    request: Request,
    payload: BroadcastPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    from app.services.notification_service import bulk_send_instant_notifications
    
    # Get all active users
    users = db.scalars(select(User.user_id).where(User.is_active == True)).all()
    
    if users:
        bulk_send_instant_notifications(
            db,
            user_ids=list(users),
            event_type="admin.broadcast",
            payload={
                "title": payload.title,
                "message": payload.body,
                "category": payload.category
            },
            background_tasks=background_tasks
        )
    
    db.commit()
    
    _audit(db, claims["sub"], f"BROADCAST_NOTIFICATION_{payload.category}", request)
    
    return ok({
        "sent_to_count": len(users),
        "category": payload.category
    })
