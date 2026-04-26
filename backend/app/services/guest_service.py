"""Guest trial sessions (Redis with in-memory fallback)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from redis.exceptions import RedisError

from app.core.product_constants import GUEST_TRIAL_MAX_DURATION_SEC
from app.services.redis_client import get_redis
from app.services.utils import make_id

_FALLBACK: dict[str, dict[str, Any]] = {}
logger = logging.getLogger(__name__)


def _now() -> float:
    return time.time()


def start_session() -> tuple[str, float]:
    sid = make_id("gst")
    payload = {"started_at": _now(), "actions": 0, "branch": None}
    r = get_redis()
    if r:
        try:
            r.setex(f"guest:{sid}", GUEST_TRIAL_MAX_DURATION_SEC, json.dumps(payload))
            return sid, GUEST_TRIAL_MAX_DURATION_SEC
        except RedisError as exc:
            logger.warning("Guest session Redis unavailable, using in-memory fallback: %s", exc)
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
        try:
            r.expire(f"guest:{sid}", GUEST_TRIAL_MAX_DURATION_SEC)
        except RedisError as exc:
            logger.warning("Guest heartbeat Redis expire failed, continuing with fallback: %s", exc)
    return True


def _get_raw(sid: str) -> dict[str, Any] | None:
    r = get_redis()
    if r:
        try:
            blob = r.get(f"guest:{sid}")
            if blob:
                return json.loads(blob)
        except RedisError as exc:
            logger.warning("Guest session Redis read failed, trying fallback cache: %s", exc)
        except json.JSONDecodeError:
            return None
    return _FALLBACK.get(sid)


def record_choice(sid: str, choice: str) -> bool:
    raw = _get_raw(sid)
    if not raw:
        return False
    raw["branch"] = choice
    raw["actions"] = int(raw.get("actions") or 0) + 1
    r = get_redis()
    if r:
        try:
            ttl = r.ttl(f"guest:{sid}")
            if ttl < 0:
                ttl = GUEST_TRIAL_MAX_DURATION_SEC
            r.setex(f"guest:{sid}", ttl, json.dumps(raw))
            return True
        except RedisError as exc:
            logger.warning("Guest session Redis write failed, using fallback cache: %s", exc)
    _FALLBACK[sid] = raw
    return True
