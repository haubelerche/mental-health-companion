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
        if self.client is None:
            return
        bucket = int(time.time() // 60)
        redis_key = f"rl:{key}:{bucket}"
        try:
            pipe = self.client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 70)
            count, _ = pipe.execute()
            if count > limit:
                raise AppError(code, message, 429)
        except AppError:
            raise
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
        if self.client is None:
            return
        lock_key = f"auth:lock:{identity}"
        fail_key = f"auth:fail:{identity}"
        try:
            pipe = self.client.pipeline()
            pipe.exists(lock_key)
            pipe.get(fail_key)
            locked, fail_raw = pipe.execute()
            if locked:
                raise AppError(code, message, 429)
            if int(fail_raw or 0) >= threshold:
                self.client.setex(lock_key, lock_minutes * 60, "1")
                self.client.delete(fail_key)
                raise AppError(code, message, 429)
        except AppError:
            raise
        except RedisError:
            return

    def record_auth_failure(self, identity: str, threshold: int, lock_minutes: int) -> None:
        if self.client is None:
            return
        fail_key = f"auth:fail:{identity}"
        lock_key = f"auth:lock:{identity}"
        try:
            pipe = self.client.pipeline()
            pipe.incr(fail_key)
            pipe.expire(fail_key, lock_minutes * 60)
            count, _ = pipe.execute()
            if count >= threshold:
                self.client.setex(lock_key, lock_minutes * 60, "1")
                self.client.delete(fail_key)
        except RedisError:
            return

    def clear_auth_failure(self, identity: str) -> None:
        if self.client is None:
            return
        try:
            pipe = self.client.pipeline()
            pipe.delete(f"auth:fail:{identity}")
            pipe.delete(f"auth:lock:{identity}")
            pipe.execute()
        except RedisError:
            return


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    if redis is None:
        # Fail-open: app vẫn chạy nếu environment thiếu redis package.
        return RateLimiter(client=None)

    settings = get_settings()
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.15,
            socket_timeout=0.15,
            retry_on_timeout=False,
        )
        # Fail-open quickly when Redis is unavailable to avoid auth latency spikes.
        client.ping()
        return RateLimiter(client=client)
    except RedisError:
        return RateLimiter(client=None)
