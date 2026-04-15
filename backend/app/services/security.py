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
def _resolved_keys() -> tuple[str, str]:
    settings = get_settings()
    if not settings.jwt_private_key or not settings.jwt_public_key:
        raise RuntimeError("JWT keys are missing. Set JWT_PRIVATE_KEY and JWT_PUBLIC_KEY.")
    return settings.jwt_private_key, settings.jwt_public_key


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
    private_key, _ = _resolved_keys()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "scope": scope,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.access_token_ttl_seconds,
    }
    return jose_jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)


def issue_admin_token(subject: str) -> str:
    settings = get_settings()
    private_key, _ = _resolved_keys()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": "admin",
        "scope": "admin_only",
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + settings.admin_token_ttl_seconds,
    }
    return jose_jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    _, public_key = _resolved_keys()
    return jose_jwt.decode(token, public_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
