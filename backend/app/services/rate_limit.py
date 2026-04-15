from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

try:
    import redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # pragma: no cover
    redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass

from app.core.config import get_settings
from app.core.errors import AppError


@dataclass
class RateLimiter:
    client: Any

    def enforce_per_minute(self, key: str, limit: int, code: str, message: str) -> None:
        bucket = int(time.time() // 60)
        redis_key = f"rl:{key}:{bucket}"
        try:
            count = self.client.incr(redis_key)
            if count == 1:
                self.client.expire(redis_key, 70)
            if count > limit:
                raise AppError(code, message, 429)
        except RedisError:
            return

    def enforce_auth_lockout(
        self,
        identity: str,
        threshold: int,
        lock_minutes: int,
        code: str,
        message: str,
    ) -> None:
        lock_key = f"auth:lock:{identity}"
        try:
            if self.client.exists(lock_key):
                raise AppError(code, message, 429)

            fail_key = f"auth:fail:{identity}"
            current = int(self.client.get(fail_key) or 0)
            if current >= threshold:
                self.client.setex(lock_key, lock_minutes * 60, "1")
                self.client.delete(fail_key)
                raise AppError(code, message, 429)
        except RedisError:
            return

    def record_auth_failure(self, identity: str, threshold: int, lock_minutes: int) -> None:
        fail_key = f"auth:fail:{identity}"
        lock_key = f"auth:lock:{identity}"
        try:
            count = self.client.incr(fail_key)
            if count == 1:
                self.client.expire(fail_key, lock_minutes * 60)
            if count >= threshold:
                self.client.setex(lock_key, lock_minutes * 60, "1")
                self.client.delete(fail_key)
        except RedisError:
            return

    def clear_auth_failure(self, identity: str) -> None:
        try:
            self.client.delete(f"auth:fail:{identity}")
            self.client.delete(f"auth:lock:{identity}")
        except RedisError:
            return


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    if redis is None:
        # Fail-open: app vẫn chạy nếu environment thiếu redis package.
        return RateLimiter(client=None)

    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return RateLimiter(client=client)
