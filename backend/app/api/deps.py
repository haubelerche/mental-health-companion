from __future__ import annotations

import ipaddress

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models import User
from app.db.session import get_db
from app.services.security import decode_token


ALLOWED_CSRF_METHODS = {"POST", "PATCH", "DELETE"}


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_token_cookie: str | None = Cookie(default=None, alias="csrf_token"),
):
    if request.method not in ALLOWED_CSRF_METHODS:
        return
    if not x_csrf_token or not csrf_token_cookie or x_csrf_token != csrf_token_cookie:
        raise AppError("CSRF_TOKEN_INVALID", "CSRF token thiếu hoặc không hợp lệ", 403)


def get_current_user(
    access_token: str | None = Cookie(default=None, alias="access_token"),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise AppError("AUTH_INVALID_TOKEN", "Token không hợp lệ", 401)
    try:
        payload = decode_token(access_token)
    except Exception as exc:
        raise AppError("AUTH_INVALID_TOKEN", "Token không hợp lệ", 401) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AppError("AUTH_INVALID_TOKEN", "Token không hợp lệ", 401)

    user = db.scalar(select(User).where(User.user_id == user_id, User.is_active.is_(True)))
    if not user:
        raise AppError("AUTH_INVALID_TOKEN", "Token không hợp lệ", 401)
    return user


def get_admin_claims(access_token: str | None = Cookie(default=None, alias="access_token")) -> dict:
    if not access_token:
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)
    try:
        payload = decode_token(access_token)
    except Exception as exc:
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403) from exc
    if payload.get("role") != "admin" or payload.get("scope") != "admin_only":
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)
    return payload


def enforce_admin_ip(request: Request) -> None:
    settings = get_settings()
    allowed_raw = [item.strip() for item in settings.admin_allowed_ips.split(",") if item.strip()]
    if not allowed_raw:
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    client_ip = request.client.host if request.client else ""
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError as exc:
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403) from exc

    for cidr in allowed_raw:
        if addr in ipaddress.ip_network(cidr, strict=False):
            return

    raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)
