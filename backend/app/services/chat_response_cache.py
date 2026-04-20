from __future__ import annotations

import copy
import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    expires_at: float
    value: dict[str, Any]


_LOCK = threading.Lock()
_CACHE: dict[str, _CacheEntry] = {}
_MAX_ITEMS = 2048


def hash_message(message: str) -> str:
    text = (message or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cache_key(session_id: str, message_hash: str) -> str:
    return f"{session_id}:{message_hash}"


def _cleanup_expired(now_ts: float) -> None:
    expired_keys = [k for k, v in _CACHE.items() if v.expires_at <= now_ts]
    for key in expired_keys:
        _CACHE.pop(key, None)


def get_cached_turn(session_id: str, message_hash: str) -> dict[str, Any] | None:
    key = _cache_key(session_id, message_hash)
    now_ts = time.time()
    with _LOCK:
        _cleanup_expired(now_ts)
        entry = _CACHE.get(key)
        if not entry:
            return None
        if entry.expires_at <= now_ts:
            _CACHE.pop(key, None)
            return None
        return copy.deepcopy(entry.value)


def set_cached_turn(
    session_id: str,
    message_hash: str,
    turn: dict[str, Any],
    *,
    ttl_seconds: int,
) -> None:
    if ttl_seconds <= 0:
        return
    now_ts = time.time()
    key = _cache_key(session_id, message_hash)
    entry = _CacheEntry(expires_at=now_ts + float(ttl_seconds), value=copy.deepcopy(turn))
    with _LOCK:
        _cleanup_expired(now_ts)
        if len(_CACHE) >= _MAX_ITEMS:
            # Evict oldest by expiry to keep memory bounded.
            oldest_key = min(_CACHE, key=lambda k: _CACHE[k].expires_at)
            _CACHE.pop(oldest_key, None)
        _CACHE[key] = entry
