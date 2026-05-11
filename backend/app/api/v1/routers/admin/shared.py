from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.services.db.models import AdminAuditLog

from app.services.utils import get_now

router = APIRouter(prefix="/admin", tags=["admin"])

RESOURCE_CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]
RESOURCE_FORMATS = ["audio", "video", "article"]

def _audit(db: Session, admin_id: str, action: str, request: Request):
    db.add(
        AdminAuditLog(
            admin_id=admin_id,
            action=action,
            resource_accessed=str(request.url.path),
            ip_address=request.client.host if request.client else "0.0.0.0",
            metadata_json={},
            created_at=get_now()
        )
    )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Log error but don't crash the request for an audit failure
        print(f"Audit log failed: {e}")

def _validate_resource_payload(category: str, format_value: str):
    if category not in RESOURCE_CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)
    if format_value not in RESOURCE_FORMATS:
        raise AppError("INVALID_PARAMETER", "Format không hợp lệ", 400)
