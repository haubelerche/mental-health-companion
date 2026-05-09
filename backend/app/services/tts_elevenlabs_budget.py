"""Per-user daily character budget for ElevenLabs (cost guard). Redis required to allow EL."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from redis.exceptions import RedisError

from app.core.config import Settings
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)
_LOCAL_LOCK = threading.Lock()
_LOCAL_BUDGET: dict[str, int] = {}


def _usage_key(user_id: str) -> str:
    from app.services.utils import get_now
    day = get_now().strftime("%Y-%m-%d")
    return f"serene:tts:11l:chars:{user_id}:{day}"


def get_elevenlabs_chars_used_today(user_id: str) -> int | None:
    """Return usage from Redis; fall back to local process budget when Redis is unavailable."""
    key = _usage_key(user_id)
    r = get_redis()
    if not r:
        with _LOCAL_LOCK:
            return int(_LOCAL_BUDGET.get(key, 0))
    try:
        raw = r.get(key)
    except RedisError as exc:
        logger.warning("elevenlabs budget redis get failed: %s", exc)
        with _LOCAL_LOCK:
            return int(_LOCAL_BUDGET.get(key, 0))
    if raw is None:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def can_use_elevenlabs_chars(user_id: str, proposed: int, settings: Settings) -> bool:
    if proposed <= 0:
        return True
    used = get_elevenlabs_chars_used_today(user_id)
    if used is None:
        return True
    return used + proposed <= int(settings.elevenlabs_max_chars_per_user_per_day)


def record_elevenlabs_chars_used(user_id: str, chars: int) -> None:
    if chars <= 0:
        return
    r = get_redis()
    key = _usage_key(user_id)
    with _LOCAL_LOCK:
        _LOCAL_BUDGET[key] = int(_LOCAL_BUDGET.get(key, 0)) + int(chars)
    if not r:
        return
    try:
        pipe = r.pipeline()
        pipe.incrby(key, chars)
        pipe.expire(key, 86400 * 2)
        pipe.execute()
    except RedisError as exc:
        logger.warning("elevenlabs budget redis incr failed: %s", exc)
