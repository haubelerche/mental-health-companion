from fastapi import Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import User, SyncOutbox
from .shared import router, _audit

class BroadcastPayload(BaseModel):
    title: str | None = None
    body: str
    category: str = "general" # morning, reminder, etc.

@router.post("/notifications/broadcast")
def admin_broadcast_notification(
    request: Request,
    payload: BroadcastPayload,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    # Get all active users
    users = db.scalars(select(User).where(User.is_active == True)).all()
    
    outbox_entries = []
    for user in users:
        outbox_entries.append(
            SyncOutbox(
                user_id=user.user_id,
                event_type="admin.broadcast",
                payload={
                    "title": payload.title,
                    "message": payload.body,
                    "category": payload.category
                },
                status="pending"
            )
        )
    
    db.add_all(outbox_entries)
    db.commit()
    
    _audit(db, claims["sub"], f"BROADCAST_NOTIFICATION_{payload.category}", request)
    
    return ok({
        "sent_to_count": len(outbox_entries),
        "category": payload.category
    })
