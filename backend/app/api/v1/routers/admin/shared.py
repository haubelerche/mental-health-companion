from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.services.db.models import AdminAuditLog

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
        )
    )
    db.commit()

def _validate_resource_payload(category: str, format_value: str):
    if category not in RESOURCE_CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)
    if format_value not in RESOURCE_FORMATS:
        raise AppError("INVALID_PARAMETER", "Format không hợp lệ", 400)
