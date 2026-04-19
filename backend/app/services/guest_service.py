"""Guest trial sessions (Redis with in-memory fallback)."""

from __future__ import annotations

import json
import time
from typing import Any

from app.core.product_constants import GUEST_TRIAL_MAX_DURATION_SEC
from app.services.redis_client import get_redis
from app.services.utils import make_id

_FALLBACK: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def start_session() -> tuple[str, float]:
    sid = make_id("gst")
    payload = {"started_at": _now(), "actions": 0, "branch": None}
    r = get_redis()
    if r:
        r.setex(f"guest:{sid}", GUEST_TRIAL_MAX_DURATION_SEC, json.dumps(payload))
    else:
        _FALLBACK[sid] = payload
    return sid, GUEST_TRIAL_MAX_DURATION_SEC


def heartbeat(sid: str) -> bool:
    raw = _get_raw(sid)
    if not raw:
        return False
    if _now() - float(raw["started_at"]) > GUEST_TRIAL_MAX_DURATION_SEC:
        return False
    r = get_redis()
    if r:
        r.expire(f"guest:{sid}", GUEST_TRIAL_MAX_DURATION_SEC)
    return True


def _get_raw(sid: str) -> dict[str, Any] | None:
    r = get_redis()
    if r:
        blob = r.get(f"guest:{sid}")
        if not blob:
            return None
        return json.loads(blob)
    return _FALLBACK.get(sid)


def record_choice(sid: str, choice: str) -> bool:
    raw = _get_raw(sid)
    if not raw:
        return False
    raw["branch"] = choice
    raw["actions"] = int(raw.get("actions") or 0) + 1
    r = get_redis()
    if r:
        ttl = r.ttl(f"guest:{sid}")
        if ttl < 0:
            ttl = GUEST_TRIAL_MAX_DURATION_SEC
        r.setex(f"guest:{sid}", ttl, json.dumps(raw))
    else:
        _FALLBACK[sid] = raw
    return True
