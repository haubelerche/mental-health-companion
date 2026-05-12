from fastapi import Depends, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import CrisisLog
from app.services.schemas.payloads import CrisisReviewRequest
from .shared import router, _audit

@router.get("/crisis-logs")
def admin_crisis_logs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
    limit: int = 100,
    offset: int = 0
):
    enforce_admin_ip(request)
    try:
        from app.services.db.models import User
        total = db.scalar(select(func.count(CrisisLog.log_id)))
        
        stmt = (
            select(CrisisLog, User.display_name)
            .join(User, CrisisLog.user_id == User.user_id)
            .order_by(CrisisLog.triggered_at.desc())
            .offset(offset)
            .limit(limit)
        )
        results = db.execute(stmt).all()

        _audit(db, claims["sub"], "GET_CRISIS_LOGS", request)

        return ok({
            "logs": [
                {
                    "log_id": row[0].log_id,
                    "session_id": row[0].session_id,
                    "user_id": row[0].user_id,
                    "user_name": row[1],
                    "triggered_at": row[0].triggered_at.isoformat(),
                    "muc_do": row[0].severity_level,
                    "reviewed": row[0].reviewed,
                    "context_summary": row[0].context_summary
                } for row in results
            ],
            "total": total or 0,
            "has_more": offset + limit < (total or 0)
        })
    except Exception as e:
        print(f"Crisis Logs Error: {e}")
        raise AppError("INTERNAL_ERROR", "Lỗi tải nhật ký khủng hoảng", 500)

@router.patch("/crisis-logs/{log_id}/review")
def admin_review_crisis_log(
    log_id: str,
    payload: CrisisReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    row = db.get(CrisisLog, log_id)
    if not row:
        raise AppError("NOT_FOUND", "Nhật ký không tồn tại", 404)
        
    row.reviewed = payload.reviewed
    row.reviewed_at = func.now()
    row.reviewed_by = claims["sub"]
    
    db.commit()
    db.refresh(row)
    
    _audit(db, claims["sub"], f"REVIEW_CRISIS_LOG_{log_id}", request)
    
    return ok({
        "log_id": log_id,
        "reviewed": row.reviewed,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "reviewed_by": row.reviewed_by,
        "note": payload.note
    })
