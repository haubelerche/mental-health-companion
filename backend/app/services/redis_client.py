"""Optional Redis client for profile cache and guest sessions."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import redis

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis | None:
    try:
        settings = get_settings()
        if not settings.redis_url:
            return None
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def profile_cache_key(user_id: str) -> str:
    return f"profile:{user_id}"


def cache_get_json(key: str) -> Any | None:
    r = get_redis()
    if not r:
        return None
    raw = r.get(key)
    if not raw:
        return None
    import json

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set_json(key: str, value: Any, ttl_sec: int) -> None:
    r = get_redis()
    if not r:
        return
    import json

    r.setex(key, ttl_sec, json.dumps(value, default=str))


def cache_delete(key: str) -> None:
    r = get_redis()
    if r:
        r.delete(key)
