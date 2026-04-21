"""Long-term memory helpers for per-user chat personalization."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserProfile
from app.services.redis_client import cache_get_json, cache_set_json, profile_cache_key


def get_user_longterm_memories(db: Session, *, user_id: str, limit: int = 3) -> list[str]:
    """Return recent session summaries for this user as long-term memory snippets."""
    cache_key = profile_cache_key(user_id)
    profile_data = cache_get_json(cache_key)
    if profile_data is None:
        row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        profile_data = dict(row.profile or {}) if row else {}
        cache_set_json(cache_key, profile_data, ttl_sec=60)

    summaries = list(profile_data.get("session_summaries") or [])
    collected: list[str] = []
    for item in reversed(summaries):
        text = str((item or {}).get("text") or "").strip()
        if not text:
            continue
        collected.append(text[:400])
        if len(collected) >= limit:
            break
    return collected
