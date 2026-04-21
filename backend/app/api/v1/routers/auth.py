from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_csrf
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import RefreshToken, User
from app.db.session import get_db
from app.schemas.payloads import LoginRequest, SignupRequest
from app.services.cookies import clear_auth_cookies, set_auth_cookies, set_csrf_cookie
from app.services.rate_limit import get_rate_limiter
from app.services.security import (
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    issue_access_token,
    verify_password,
)
from app.services.utils import make_id, now_plus, utc_now
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf-token")
def csrf_token(response: Response):
    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return ok({"csrf_token": token}, response=response)


@router.post("/signup")
def signup(payload: SignupRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    limiter.enforce_per_minute(
        key=f"auth:signup:{ip}",
        limit=settings.auth_rate_limit_per_minute,
        code="RATE_LIMIT_AUTH",
        message="Bạn đã vượt quá giới hạn thử xác thực",
    )

    if not payload.disclaimer_accepted:
        raise AppError("DISCLAIMER_NOT_ACCEPTED", "Bạn cần chấp nhận disclaimer", 400)

    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise AppError("INVALID_PARAMETER", "Email đã tồn tại", 400)

    user = User(
        user_id=make_id("usr"),
        display_name=payload.display_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        disclaimer_accepted=True,
        policy_acknowledged_at=None,
        policy_version_ack=None,
    )
    db.add(user)
    try:
        db.flush()
        access = issue_access_token(user.user_id)
        refresh = generate_refresh_token()
        db.add(
            RefreshToken(
                token_id=make_id("rt"),
                user_id=user.user_id,
                token_hash=hash_refresh_token(refresh),
                ip_address=request.client.host if request.client else None,
                expires_at=now_plus(days=get_settings().refresh_token_ttl_days),
            )
        )
        db.commit()
    except AppError:
        db.rollback()
        raise
    except RuntimeError as exc:
        db.rollback()
        raise AppError("CONFIG_ERROR", str(exc), 500) from exc
    except Exception as exc:
        db.rollback()
        raise AppError("SCHEMA_VALIDATION_FAILED", "Đăng ký thất bại, vui lòng thử lại", 500) from exc

    set_auth_cookies(response, access_token=access, refresh_token=refresh)
    set_csrf_cookie(response, generate_csrf_token())
    return ok(
        {"user_id": user.user_id, "expires_in": get_settings().access_token_ttl_seconds},
        status_code=201,
        response=response,
    )


@router.post("/login")
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    identity = f"{payload.email.lower()}:{ip}"
    limiter.enforce_per_minute(
        key=f"auth:login:{ip}",
        limit=settings.auth_rate_limit_per_minute,
        code="RATE_LIMIT_AUTH",
        message="Bạn đã vượt quá giới hạn thử xác thực",
    )
    limiter.enforce_auth_lockout(
        identity=identity,
        threshold=settings.auth_lockout_threshold,
        lock_minutes=settings.auth_lockout_minutes,
        code="AUTH_TOO_MANY_ATTEMPTS",
        message="Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau.",
    )

    user = db.scalar(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        limiter.record_auth_failure(
            identity=identity,
            threshold=settings.auth_lockout_threshold,
            lock_minutes=settings.auth_lockout_minutes,
        )
        raise AppError("AUTH_INVALID_TOKEN", "Email hoặc mật khẩu không đúng", 401)

    limiter.clear_auth_failure(identity)

    access = issue_access_token(user.user_id)
    refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            token_id=make_id("rt"),
            user_id=user.user_id,
            token_hash=hash_refresh_token(refresh),
            ip_address=request.client.host if request.client else None,
            expires_at=now_plus(days=get_settings().refresh_token_ttl_days),
        )
    )
    db.commit()

    set_auth_cookies(response, access_token=access, refresh_token=refresh)
    set_csrf_cookie(response, generate_csrf_token())
    return ok({"user_id": user.user_id, "expires_in": get_settings().access_token_ttl_seconds}, response=response)


@router.post("/refresh", dependencies=[Depends(require_csrf)])
def refresh_token(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not refresh_token:
        raise AppError("AUTH_REFRESH_MALFORMED", "Refresh token không hợp lệ", 401)

    hashed = hash_refresh_token(refresh_token)
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    if not row:
        raise AppError("AUTH_REFRESH_MALFORMED", "Refresh token không hợp lệ", 401)
    if row.revoked_at is not None:
        raise AppError("AUTH_REFRESH_REVOKED", "Refresh token đã bị thu hồi", 401)
    if row.expires_at < utc_now().replace(tzinfo=None):
        raise AppError("AUTH_REFRESH_EXPIRED", "Refresh token đã hết hạn", 401)

    access = issue_access_token(row.user_id)
    set_auth_cookies(response, access_token=access)
    set_csrf_cookie(response, generate_csrf_token())
    return ok({"expires_in": get_settings().access_token_ttl_seconds}, response=response)


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(response: Response, refresh_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if refresh_token:
        hashed = hash_refresh_token(refresh_token)
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hashed))
        if row and row.revoked_at is None:
            row.revoked_at = utc_now().replace(tzinfo=None)
            db.commit()

    clear_auth_cookies(response)
    return ok({"logged_out_at": utc_now().isoformat().replace("+00:00", "Z")}, response=response)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return ok(
        {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "display_name": current_user.display_name,
        }
    )
