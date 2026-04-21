from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from functools import lru_cache

import bcrypt
from jose import jwt as jose_jwt
import pyotp

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _jwt_material() -> tuple[str, str, str]:
    """(signing_key, verifying_key, algorithm). RS256: priv/pub. HS256: same secret twice."""
    settings = get_settings()
    priv = (settings.jwt_private_key or "").strip()
    pub = (settings.jwt_public_key or "").strip()
    if priv and pub:
        alg = (settings.jwt_algorithm or "RS256").strip().upper()
        return priv, pub, alg
    secret = (settings.jwt_dev_secret or "").strip()
    if len(secret) >= 16:
        return secret, secret, "HS256"
    raise RuntimeError(
        "Thiếu cấu hình JWT: đặt JWT_PRIVATE_KEY và JWT_PUBLIC_KEY (RS256), "
        "hoặc JWT_DEV_SECRET (chuỗi >= 16 ký tự) để ký bằng HS256 trên máy local."
    )


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    # bcrypt works on max 72 bytes; pre-hash long inputs to keep deterministic behavior.
    if len(raw) > 72:
        raw = hashlib.sha256(raw).hexdigest().encode("utf-8")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    raw = plain.encode("utf-8")
    if len(raw) > 72:
        raw = hashlib.sha256(raw).hexdigest().encode("utf-8")
    if hashed and not hashed.startswith("$") and hashed.startswith(("2a$", "2b$", "2y$")):
        hashed = f"${hashed}"
    return bcrypt.checkpw(raw, hashed.encode("utf-8"))


def verify_totp(code: str, secret: str) -> bool:
    if not code or not secret:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code, valid_window=1))
    except Exception:
        return False


def issue_access_token(subject: str, role: str = "user", scope: str = "user") -> str:
    settings = get_settings()
    sign_key, _, algorithm = _jwt_material()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "scope": scope,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.access_token_ttl_seconds,
    }
    return jose_jwt.encode(payload, sign_key, algorithm=algorithm)


def issue_admin_token(subject: str) -> str:
    settings = get_settings()
    sign_key, _, algorithm = _jwt_material()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": "admin",
        "scope": "admin_only",
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.admin_token_ttl_seconds,
    }
    return jose_jwt.encode(payload, sign_key, algorithm=algorithm)


def decode_token(token: str) -> dict:
    _, verify_key, algorithm = _jwt_material()
    return jose_jwt.decode(token, verify_key, algorithms=[algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
