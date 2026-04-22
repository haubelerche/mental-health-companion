import logging
import time

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_csrf
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.product_constants import CURRENT_POLICY_VERSION
from app.core.responses import ok
from app.db.models import EmailVerificationToken, PasswordResetToken, RefreshToken, User
from app.db.session import get_db
from app.schemas.payloads import (
    ForgotPasswordRequest,
    LoginRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.services.auth_email import send_password_reset_email, send_verification_email
from app.services.cookies import clear_auth_cookies, set_auth_cookies, set_csrf_cookie
from app.services.auth_latency_metrics import observe_auth_latency
from app.services.rate_limit import get_rate_limiter
from app.services.security import (
    generate_csrf_token,
    generate_one_time_token,
    generate_refresh_token,
    hash_password,
    hash_one_time_token,
    hash_refresh_token,
    issue_access_token,
    verify_password,
)
from app.services.utils import make_id, now_plus, utc_now

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _utc_naive_now():
    return utc_now().replace(tzinfo=None)


def _issue_login_session(user: User, response: Response, request: Request, db: Session):
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
    user.last_active = _utc_naive_now()
    db.commit()
    set_auth_cookies(response, access_token=access, refresh_token=refresh)
    set_csrf_cookie(response, generate_csrf_token())


def _create_email_verification_token(db: Session, user_id: str, resend_count: int = 0) -> str:
    token = generate_one_time_token()
    token_row = EmailVerificationToken(
        token_id=make_id("evt"),
        user_id=user_id,
        token_hash=hash_one_time_token(token),
        expires_at=now_plus(seconds=get_settings().auth_email_verify_ttl_minutes * 60),
        resend_count=resend_count,
        last_sent_at=_utc_naive_now(),
    )
    db.add(token_row)
    return token


def _create_password_reset_token(db: Session, user_id: str) -> str:
    token = generate_one_time_token()
    token_row = PasswordResetToken(
        token_id=make_id("prt"),
        user_id=user_id,
        token_hash=hash_one_time_token(token),
        expires_at=now_plus(seconds=get_settings().auth_password_reset_ttl_minutes * 60),
    )
    db.add(token_row)
    return token


@router.get("/csrf-token")
def csrf_token(response: Response):
    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return ok({"csrf_token": token}, response=response)


@router.post("/signup")
def signup(payload: SignupRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    total_start = time.perf_counter()
    db_ms = 0.0
    bcrypt_ms = 0.0
    redis_ms = 0.0
    success = False
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    redis_start = time.perf_counter()
    limiter.enforce_per_minute(
        key=f"auth:signup:{ip}",
        limit=settings.auth_rate_limit_per_minute,
        code="RATE_LIMIT_AUTH",
        message="Bạn đã vượt quá giới hạn thử xác thực",
    )
    redis_ms += _elapsed_ms(redis_start)

    if not payload.disclaimer_accepted:
        raise AppError("DISCLAIMER_NOT_ACCEPTED", "Bạn cần chấp nhận disclaimer", 400)

    db_start = time.perf_counter()
    exists = db.scalar(select(User).where(User.email == payload.email))
    db_ms += _elapsed_ms(db_start)
    if exists:
        raise AppError("INVALID_PARAMETER", "Email đã tồn tại", 400)

    now = utc_now().replace(tzinfo=None)
    bcrypt_start = time.perf_counter()
    password_hash = hash_password(payload.password)
    bcrypt_ms += _elapsed_ms(bcrypt_start)
    user = User(
        user_id=make_id("usr"),
        display_name=payload.display_name,
        email=payload.email,
        password_hash=password_hash,
        is_active=False,
        email_verified_at=None,
        disclaimer_accepted=True,
        policy_acknowledged_at=now,
        policy_version_ack=CURRENT_POLICY_VERSION,
    )
    db.add(user)
    try:
        db.flush()
        verify_token = _create_email_verification_token(db=db, user_id=user.user_id)
        send_verification_email(to_email=user.email, display_name=user.display_name, token=verify_token)
        db_start = time.perf_counter()
        db.commit()
        db_ms += _elapsed_ms(db_start)
        success = True
    except AppError:
        db.rollback()
        raise
    except RuntimeError as exc:
        db.rollback()
        raise AppError("CONFIG_ERROR", str(exc), 500) from exc
    except Exception as exc:
        db.rollback()
        raise AppError("SCHEMA_VALIDATION_FAILED", "Đăng ký thất bại, vui lòng thử lại", 500) from exc

    total_ms = _elapsed_ms(total_start)
    signup_snapshot = observe_auth_latency(flow="signup", duration_ms=total_ms, success=success)
    if signup_snapshot.should_log:
        logger.info(
            "auth.benchmark flow=%s window=%d success_rate=%.2f avg_ms=%.2f p95_ms=%.2f target_p95_ms=%.2f within_sla=%s",
            signup_snapshot.flow,
            signup_snapshot.count,
            signup_snapshot.success_rate,
            signup_snapshot.avg_ms,
            signup_snapshot.p95_ms,
            signup_snapshot.target_p95_ms,
            signup_snapshot.within_sla,
        )
    logger.info(
        "auth.signup metrics success=%s db_ms=%.2f bcrypt_ms=%.2f redis_ms=%.2f auth_total_ms=%.2f",
        success,
        db_ms,
        bcrypt_ms,
        redis_ms,
        total_ms,
    )
    return ok(
        {
            "user_id": user.user_id,
            "verification_required": True,
            "message": "Vui lòng kiểm tra email để xác nhận tài khoản",
        },
        status_code=202,
        response=response,
    )


@router.post("/login")
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    total_start = time.perf_counter()
    db_ms = 0.0
    bcrypt_ms = 0.0
    redis_ms = 0.0
    success = False
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    identity = f"{payload.email.lower()}:{ip}"
    try:
        redis_start = time.perf_counter()
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
        redis_ms += _elapsed_ms(redis_start)

        db_start = time.perf_counter()
        user = db.scalar(select(User).where(User.email == payload.email))
        db_ms += _elapsed_ms(db_start)

        is_valid_password = False
        if user:
            bcrypt_start = time.perf_counter()
            is_valid_password = verify_password(payload.password, user.password_hash)
            bcrypt_ms += _elapsed_ms(bcrypt_start)

        if not user or not is_valid_password:
            redis_start = time.perf_counter()
            limiter.record_auth_failure(
                identity=identity,
                threshold=settings.auth_lockout_threshold,
                lock_minutes=settings.auth_lockout_minutes,
            )
            redis_ms += _elapsed_ms(redis_start)
            raise AppError("AUTH_INVALID_TOKEN", "Email hoặc mật khẩu không đúng", 401)

        redis_start = time.perf_counter()
        limiter.clear_auth_failure(identity)
        redis_ms += _elapsed_ms(redis_start)

        now = utc_now().replace(tzinfo=None)
        if user.policy_version_ack != CURRENT_POLICY_VERSION:
            user.policy_acknowledged_at = now
            user.policy_version_ack = CURRENT_POLICY_VERSION

        if not user.is_active:
            raise AppError(
                "AUTH_EMAIL_NOT_VERIFIED",
                "Tài khoản chưa xác nhận email. Vui lòng kiểm tra hộp thư hoặc gửi lại email xác nhận.",
                403,
            )

        db_start = time.perf_counter()
        _issue_login_session(user=user, response=response, request=request, db=db)
        db_ms += _elapsed_ms(db_start)
        success = True

        return ok({"user_id": user.user_id, "expires_in": get_settings().access_token_ttl_seconds}, response=response)
    finally:
        total_ms = _elapsed_ms(total_start)
        login_snapshot = observe_auth_latency(flow="login", duration_ms=total_ms, success=success)
        if login_snapshot.should_log:
            logger.info(
                "auth.benchmark flow=%s window=%d success_rate=%.2f avg_ms=%.2f p95_ms=%.2f target_p95_ms=%.2f within_sla=%s",
                login_snapshot.flow,
                login_snapshot.count,
                login_snapshot.success_rate,
                login_snapshot.avg_ms,
                login_snapshot.p95_ms,
                login_snapshot.target_p95_ms,
                login_snapshot.within_sla,
            )
        logger.info(
            "auth.login metrics success=%s db_ms=%.2f bcrypt_ms=%.2f redis_ms=%.2f auth_total_ms=%.2f",
            success,
            db_ms,
            bcrypt_ms,
            redis_ms,
            total_ms,
        )


@router.get("/verify-email")
def verify_email(token: str, request: Request, db: Session = Depends(get_db)):
    if not token:
        raise AppError("AUTH_VERIFY_TOKEN_INVALID", "Liên kết xác nhận không hợp lệ", 400)

    now = _utc_naive_now()
    hashed = hash_one_time_token(token)
    row = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == hashed))
    if not row:
        raise AppError("AUTH_VERIFY_TOKEN_INVALID", "Liên kết xác nhận không hợp lệ", 400)

    user = db.get(User, row.user_id)
    if not user:
        raise AppError("AUTH_VERIFY_TOKEN_INVALID", "Liên kết xác nhận không hợp lệ", 400)

    if row.used_at is None and row.expires_at < now:
        raise AppError("AUTH_VERIFY_TOKEN_EXPIRED", "Liên kết xác nhận đã hết hạn", 400)

    user.is_active = True
    if row.used_at is None:
        row.used_at = now
    if user.email_verified_at is None:
        user.email_verified_at = now

    response = RedirectResponse(url=get_settings().frontend_home_url, status_code=302)
    _issue_login_session(user=user, response=response, request=request, db=db)
    return response


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    limiter.enforce_per_minute(
        key=f"auth:resend:{ip}",
        limit=settings.auth_rate_limit_per_minute,
        code="RATE_LIMIT_AUTH",
        message="Bạn đã vượt quá giới hạn thử xác thực",
    )

    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or user.is_active:
        return ok({"resent": True, "message": "Nếu email tồn tại, chúng tôi đã gửi lại email xác nhận"})

    now = _utc_naive_now()
    latest = db.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.user_id)
        .order_by(EmailVerificationToken.created_at.desc())
    )
    if latest and latest.last_sent_at and (now - latest.last_sent_at).total_seconds() < settings.auth_email_resend_cooldown_seconds:
        return ok({"resent": True, "message": "Nếu email tồn tại, chúng tôi đã gửi lại email xác nhận"})

    active_tokens = db.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.user_id,
            EmailVerificationToken.used_at.is_(None),
        )
    ).all()
    for item in active_tokens:
        item.used_at = now

    resend_count = latest.resend_count + 1 if latest else 1
    verify_token = _create_email_verification_token(db=db, user_id=user.user_id, resend_count=resend_count)

    try:
        send_verification_email(to_email=user.email, display_name=user.display_name, token=verify_token)
        db.commit()
    except RuntimeError as exc:
        db.rollback()
        raise AppError("CONFIG_ERROR", str(exc), 500) from exc
    except Exception as exc:
        db.rollback()
        raise AppError("SCHEMA_VALIDATION_FAILED", "Không thể gửi lại email xác nhận", 500) from exc

    return ok({"resent": True, "message": "Nếu email tồn tại, chúng tôi đã gửi lại email xác nhận"})


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    limiter = get_rate_limiter()
    ip = request.client.host if request.client else "unknown"
    limiter.enforce_per_minute(
        key=f"auth:forgot:{ip}",
        limit=settings.auth_rate_limit_per_minute,
        code="RATE_LIMIT_AUTH",
        message="Bạn đã vượt quá giới hạn thử xác thực",
    )

    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        return ok({"sent": True, "message": "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu"})

    now = _utc_naive_now()
    pending = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for item in pending:
        item.used_at = now

    token = _create_password_reset_token(db=db, user_id=user.user_id)
    try:
        send_password_reset_email(to_email=user.email, display_name=user.display_name, token=token)
        db.commit()
    except RuntimeError as exc:
        db.rollback()
        raise AppError("CONFIG_ERROR", str(exc), 500) from exc
    except Exception as exc:
        db.rollback()
        raise AppError("SCHEMA_VALIDATION_FAILED", "Không thể gửi email đặt lại mật khẩu", 500) from exc

    return ok({"sent": True, "message": "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu"})


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = _utc_naive_now()
    hashed = hash_one_time_token(payload.token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hashed))
    if not row:
        raise AppError("AUTH_RESET_TOKEN_INVALID", "Liên kết đặt lại mật khẩu không hợp lệ", 400)
    if row.used_at is not None:
        raise AppError("AUTH_RESET_TOKEN_USED", "Liên kết đặt lại mật khẩu đã được sử dụng", 400)
    if row.expires_at < now:
        raise AppError("AUTH_RESET_TOKEN_EXPIRED", "Liên kết đặt lại mật khẩu đã hết hạn", 400)

    user = db.get(User, row.user_id)
    if not user:
        raise AppError("AUTH_RESET_TOKEN_INVALID", "Liên kết đặt lại mật khẩu không hợp lệ", 400)

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = now
    row.used_at = now

    active_refresh_tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    for token_row in active_refresh_tokens:
        token_row.revoked_at = now

    db.commit()
    return ok({"reset": True, "message": "Đặt lại mật khẩu thành công"})


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
            "policy_version_ack": current_user.policy_version_ack,
        }
    )
