from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.schemas.payloads import AdminLoginRequest
from app.services.auth_latency_metrics import get_auth_latency_snapshot
from app.services.security import issue_admin_token, verify_password, verify_totp
from app.services.utils import make_id
from app.services.cookies import set_auth_cookies
from .shared import router, _audit

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

    return ok({"admin_id": admin_id, "expires_in": 7200}, response=response)

@router.get("/auth/latency-sla")
def admin_auth_latency_sla(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    login = get_auth_latency_snapshot(flow="login")
    signup = get_auth_latency_snapshot(flow="signup")

    _audit(db, claims["sub"], "GET_AUTH_LATENCY_SLA", request)

    return ok(
        {
            "login": {
                "window": login.count,
                "success_rate": login.success_rate,
                "avg_ms": login.avg_ms,
                "p95_ms": login.p95_ms,
                "target_p95_ms": login.target_p95_ms,
                "within_sla": login.within_sla,
            },
            "signup": {
                "window": signup.count,
                "success_rate": signup.success_rate,
                "avg_ms": signup.avg_ms,
                "p95_ms": signup.p95_ms,
                "target_p95_ms": signup.target_p95_ms,
                "within_sla": signup.within_sla,
            },
        }
    )
