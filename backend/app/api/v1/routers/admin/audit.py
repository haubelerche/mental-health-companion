from fastapi import Depends, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import AdminAuditLog
from .shared import router

@router.get("/audit-logs")
def admin_list_audit_logs(
    request: Request,
    admin_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    where_conditions = []
    if admin_id:
        where_conditions.append(AdminAuditLog.admin_id == admin_id)
        
    stmt = select(AdminAuditLog)
    if where_conditions:
        stmt = stmt.where(*where_conditions)
        
    total = db.scalar(select(func.count(AdminAuditLog.audit_id)).where(*where_conditions)) if where_conditions else db.scalar(select(func.count(AdminAuditLog.audit_id)))
    
    logs = db.scalars(stmt.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit)).all()
    
    return ok({
        "items": [{
            "log_id": str(l.audit_id),
            "admin_id": l.admin_id,
            "action": l.action,
            "resource_accessed": l.resource_accessed,
            "ip_address": str(l.ip_address),
            "created_at": l.created_at.isoformat()
        } for l in logs],
        "total": total or 0
    })
