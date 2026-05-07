from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import CrisisLog
from app.services.schemas.payloads import CrisisReviewRequest
from app.services.utils import utc_now
from .shared import router, _audit

@router.get("/crisis-logs")
def admin_crisis_logs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    logs = db.scalars(
        select(CrisisLog)
        .order_by(CrisisLog.triggered_at.desc())
        .limit(100)
    ).all()

    _audit(db, claims["sub"], "GET_CRISIS_LOGS", request)

    return ok(
        {
            "logs": [
                {
                    "log_id": row.log_id,
                    "session_id": row.session_id,
                    "triggered_at": row.triggered_at.isoformat() + "Z",
                    "muc_do": row.muc_do,
                    "reviewed": row.reviewed,
                }
                for row in logs
            ],
            "total": len(logs),
            "has_more": False,
        }
    )

@router.patch("/crisis-logs/{log_id}/review")
def review_crisis_log(
    log_id: str,
    payload: CrisisReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    row = db.get(CrisisLog, log_id)
    if not row:
        raise AppError("CRISIS_LOG_NOT_FOUND", "Crisis log không tồn tại", 404)

    row.reviewed = bool(payload.reviewed)
    row.reviewed_at = utc_now().replace(tzinfo=None)
    row.reviewed_by = claims.get("sub")

    db.commit()

    _audit(db, claims["sub"], "PATCH_CRISIS_REVIEW", request)

    return ok(
        {
            "log_id": row.log_id,
            "reviewed": row.reviewed,
            "reviewed_at": row.reviewed_at.isoformat() + "Z" if row.reviewed_at else None,
            "reviewed_by": row.reviewed_by,
            "note": payload.note,
        }
    )
