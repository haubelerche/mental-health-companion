"""Ring-buffer for recent chat turn traces stored in Redis.

Records are kept for admin observability only. No PII or raw user text.
The list is capped at _MAX_TRACES entries; each record expires via list-level TTL.
"""
from __future__ import annotations

import json
import logging

from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

_REDIS_KEY = "admin:turn_traces"
_MAX_TRACES = 200
_TTL_SECONDS = 86_400  # 24 h


def record_trace(record: dict) -> None:
    """Push one turn trace record into the Redis ring-buffer. Fail silently."""
    r = get_redis()
    if not r:
        return
    try:
        serialized = json.dumps(record, default=str)
        r.lpush(_REDIS_KEY, serialized)
        r.ltrim(_REDIS_KEY, 0, _MAX_TRACES - 1)
        r.expire(_REDIS_KEY, _TTL_SECONDS)
    except Exception:
        logger.debug("turn_trace_store: redis write failed", exc_info=True)


def get_recent_traces(limit: int = 50) -> list[dict]:
    """Return the most recent `limit` traces (newest first). Returns [] if Redis unavailable."""
    r = get_redis()
    if not r:
        return []
    try:
        raw_list = r.lrange(_REDIS_KEY, 0, limit - 1)
    except Exception:
        logger.debug("turn_trace_store: redis read failed", exc_info=True)
        return []
    result = []
    for raw in raw_list:
        try:
            result.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return result
