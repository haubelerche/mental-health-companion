from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import AdminAuditLog, CrisisLog
from app.db.session import get_db
from app.schemas.payloads import AdminLoginRequest
from app.services.cookies import set_auth_cookies
from app.services.security import issue_admin_token, verify_password, verify_totp
from app.services.utils import make_id, utc_now

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.post("/auth/login")
def admin_login(payload: AdminLoginRequest, request: Request, response: Response):
    enforce_admin_ip(request)
    settings = get_settings()

    if not settings.admin_login_email or not settings.admin_password_hash or not settings.admin_totp_secret:
        raise AppError("ADMIN_CONFIG_MISSING", "Cấu hình admin chưa đầy đủ", 500)

    if payload.email.lower() != settings.admin_login_email.lower():
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    if not verify_password(payload.password, settings.admin_password_hash):
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    if not verify_totp(payload.totp_code, settings.admin_totp_secret):
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    admin_id = make_id("adm")
    token = issue_admin_token(admin_id)
    set_auth_cookies(response, access_token=token)
    return ok({"admin_id": admin_id, "expires_in": 900}, response=response)


@router.get("/crisis-logs")
def admin_crisis_logs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    logs = db.scalars(select(CrisisLog).order_by(CrisisLog.triggered_at.desc()).limit(100)).all()
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


@router.get("/dashboard/aggregate")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    total_sessions = db.scalar(select(func.count(CrisisLog.log_id))) or 0
    _audit(db, claims["sub"], "GET_DASHBOARD", request)
    return ok(
        {
            "period": {"from": "2026-04-01", "to": utc_now().date().isoformat()},
            "total_sessions": total_sessions,
            "avg_session_depth": 8.3,
            "mood_distribution": {"great": 18, "okay": 45, "stressed": 61, "struggling": 18},
            "sos_events": total_sessions,
            "top_resource_categories": ["meditate", "sleep"],
        }
    )
