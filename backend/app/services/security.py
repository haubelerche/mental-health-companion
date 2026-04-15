from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from functools import lru_cache

import bcrypt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _resolved_keys() -> tuple[str, str]:
    settings = get_settings()
    if settings.jwt_private_key and settings.jwt_public_key:
        return settings.jwt_private_key, settings.jwt_public_key

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


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
    return bcrypt.checkpw(raw, hashed.encode("utf-8"))


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
