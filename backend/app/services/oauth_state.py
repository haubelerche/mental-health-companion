from __future__ import annotations

import base64
import hmac
import hashlib
import json
import secrets
import time
from typing import Any

from app.core.config import get_settings
from app.services.redis_client import get_redis


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    rem = len(s) % 4
    if rem:
        s = s + ("=" * (4 - rem))
    return base64.urlsafe_b64decode(s.encode())


def create_oauth_state(payload: dict[str, Any]) -> str:
    """Create a short-lived OAuth state token. Prefer Redis; fall back to signed state.

    Payload will be augmented with `ts` timestamp.
    """
    settings = get_settings()
    payload = dict(payload)
    payload["ts"] = int(time.time())
    r = get_redis()
    state_id = secrets.token_urlsafe(24)
    if r:
        key = f"oauth_state:{state_id}"
        try:
            r.setex(key, settings.oauth_state_ttl_seconds, json.dumps(payload, default=str))
            return state_id
        except Exception:
            pass

    # fallback: signed blob
    secret = settings.jwt_dev_secret or ""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    b64 = _b64u_encode(raw)
    sig = hmac.new(secret.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def pop_oauth_state(state: str) -> dict[str, Any] | None:
    """Validate and consume state. Returns payload or None on failure/expired."""
    settings = get_settings()
    r = get_redis()
    if r and not state.startswith("ey"):
        # when we used token_urlsafe the state is a short id (not base64 blob)
        key = f"oauth_state:{state}"
        try:
            raw = r.get(key)
        except Exception:
            raw = None
        if not raw:
            return None
        try:
            r.delete(key)
        except Exception:
            pass
        try:
            return json.loads(raw)
        except Exception:
            return None

    # fallback: signed blob
    try:
        b64, sig = state.rsplit(".", 1)
    except Exception:
        return None
    secret = settings.jwt_dev_secret or ""
    expected = hmac.new(secret.encode(), b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        raw = _b64u_decode(b64)
        payload = json.loads(raw.decode())
    except Exception:
        return None
    # check TTL
    ts = int(payload.get("ts") or 0)
    if ts == 0 or time.time() - ts > settings.oauth_state_ttl_seconds:
        return None
    return payload
