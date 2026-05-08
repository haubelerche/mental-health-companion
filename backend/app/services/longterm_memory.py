"""Long-term memory helpers for per-user chat personalization."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import UserProfile
from app.services.mem0_service import MemoryManager
from app.services.memory_enrichment import _fallback_extract, apply_to_profile
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_get_json, cache_set_json, profile_cache_key

logger = logging.getLogger(__name__)


@dataclass
class UserMemoryContext:
    mem0_facts: list[str]
    recent_summaries: list[str]
    top_triggers: list[str]
    traits: dict[str, Any]
    active_goals: list[str]
    effective_coping: list[str]
    clinical_trajectory: str


def _memory_context_cache_key(user_id: str, current_query: str) -> str:
    digest = hashlib.sha1((current_query or "").encode("utf-8")).hexdigest()[:16]
    return f"user_memory:{user_id}:{digest}"


def _compute_clinical_trajectory(profile_data: dict[str, Any]) -> str:
    safety = dict(profile_data.get("safety_flags") or {})
    clinical = dict(profile_data.get("clinical_snapshot") or {})
    trigger_tags = dict(profile_data.get("trigger_tags") or {})

    parts: list[str] = []
    if safety.get("ever_sos_triggered"):
        last_sos = str(safety.get("last_sos_at") or "").strip()
        if last_sos:
            try:
                dt = datetime.fromisoformat(last_sos.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                days = max(0, int((now - dt).total_seconds() // 86400))
                parts.append(f"Đã có sự kiện khủng hoảng, gần nhất {days} ngày trước")
            except Exception:
                parts.append("Đã từng có sự kiện khủng hoảng")
        else:
            parts.append("Đã từng có sự kiện khủng hoảng")

    trend = str(clinical.get("trend_7d") or "").strip()
    if trend:
        parts.append(f"Xu hướng 7 ngày: {trend}")

    if trigger_tags:
        ordered = sorted(
            trigger_tags.items(),
            key=lambda kv: int((kv[1] or {}).get("count") or 0),
            reverse=True,
        )
        labels = [str(k) for k, _ in ordered[:2]]
        if labels:
            parts.append(f"Chủ đề thường gặp: {', '.join(labels)}")

    if not parts:
        return "Chưa đủ dữ liệu để kết luận hành trình tâm lý."
    return ". ".join(parts)


def build_user_memory_context(
    db: Session,
    *,
    user_id: str,
    current_query: str = "",
) -> UserMemoryContext:
    cache_key = _memory_context_cache_key(user_id, current_query)
    cached = cache_get_json(cache_key)
    if isinstance(cached, dict):
        return UserMemoryContext(
            mem0_facts=list(cached.get("mem0_facts") or []),
            recent_summaries=list(cached.get("recent_summaries") or []),
            top_triggers=list(cached.get("top_triggers") or []),
            traits=dict(cached.get("traits") or {}),
            active_goals=list(cached.get("active_goals") or []),
            effective_coping=list(cached.get("effective_coping") or []),
            clinical_trajectory=str(cached.get("clinical_trajectory") or ""),
        )

    cache_key = profile_cache_key(user_id)
    profile_data = cache_get_json(cache_key)
    if profile_data is None:
        row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        profile_data = dict(row.profile or {}) if row else {}
        cache_set_json(cache_key, profile_data, ttl_sec=15)

    summaries = list(profile_data.get("session_summaries") or [])
    recent_summaries: list[str] = []
    for item in reversed(summaries):
        if isinstance(item, dict):
            text = str(item.get("summary") or item.get("text") or "").strip()
        elif isinstance(item, str):
            text = item.strip()
        else:
            text = ""
            
        if not text:
            continue
        recent_summaries.append(text[:400])
        if len(recent_summaries) >= 3:
            break

    trigger_tags = dict(profile_data.get("trigger_tags") or {})
    top_triggers = [
        str(tag)
        for tag, _ in sorted(
            trigger_tags.items(),
            key=lambda kv: int((kv[1] or {}).get("count") or 0),
            reverse=True,
        )[:3]
    ]
    traits = dict(profile_data.get("traits") or {})
    active_goals = []
    for g in list(profile_data.get("goals") or []):
        if isinstance(g, dict):
            text = str(g.get("text") or "").strip()
            status = str(g.get("status") or "active").strip().lower()
            if status == "active" and text:
                active_goals.append(text)
        elif isinstance(g, str):
            text = g.strip()
            if text:
                active_goals.append(text)
    active_goals = active_goals[:3]

    effective_coping = []
    for c in list(profile_data.get("coping_history") or []):
        if isinstance(c, dict):
            action = str(c.get("action") or "").strip()
            effective = int(c.get("self_reported_effective") or 0)
            if effective > 0 and action:
                effective_coping.append(action)
        elif isinstance(c, str):
            text = c.strip()
            if text:
                effective_coping.append(text)
    effective_coping = effective_coping[:3]

    mem0_facts = MemoryManager.instance().search(user_id=user_id, query=current_query, limit=5)
    if not mem0_facts:
        mem0_facts = recent_summaries[:2]

    context = UserMemoryContext(
        mem0_facts=mem0_facts,
        recent_summaries=recent_summaries,
        top_triggers=top_triggers,
        traits=traits,
        active_goals=active_goals,
        effective_coping=effective_coping,
        clinical_trajectory=_compute_clinical_trajectory(profile_data),
    )
    cache_set_json(
        _memory_context_cache_key(user_id, current_query),
        {
            "mem0_facts": context.mem0_facts,
            "recent_summaries": context.recent_summaries,
            "top_triggers": context.top_triggers,
            "traits": context.traits,
            "active_goals": context.active_goals,
            "effective_coping": context.effective_coping,
            "clinical_trajectory": context.clinical_trajectory,
        },
        ttl_sec=5,
    )
    return context


def get_user_longterm_memories(db: Session, *, user_id: str, limit: int = 3) -> list[str]:
    """Backward-compatible wrapper used by existing callers."""
    return build_user_memory_context(db, user_id=user_id).recent_summaries[:limit]


def persist_turn_memory(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    sos_triggered: bool = False,
) -> None:
    """Persist lightweight structured memory after each completed turn.

    This keeps profile memory warm across active sessions instead of waiting for `/chat/end`.
    """
    safe_user_message = mask_pii(user_message)[:1200]
    safe_assistant_reply = mask_pii(assistant_reply)[:1200]
    transcript = (
        f"user: {safe_user_message}\n"
        f"assistant: {safe_assistant_reply}"
    )
    try:
        # Turn-level memory update should stay low-latency and deterministic.
        extract = _fallback_extract(transcript, sos_triggered=sos_triggered)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("turn memory extract failed for %s: %s", user_id, exc)
        return

    # Test doubles may not implement SQLAlchemy's scalar() API; skip persistence in that case.
    if not hasattr(db, "scalar"):
        logger.debug("persist_turn_memory skipped for %s: db adapter has no scalar()", user_id)
        return

    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not row:
        row = UserProfile(user_id=user_id, profile={})
        db.add(row)
        db.flush()

    now_iso = datetime.now(timezone.utc).isoformat()
    base = dict(row.profile or {})
    updated = apply_to_profile(
        base,
        extract=extract,
        session_meta={
            "session_id": session_id,
            "started_at": now_iso,
            "ended_at": now_iso,
            "turn_count": 2,
            "crisis_level_peak": 5 if sos_triggered else 0,
        },
        summary_text=(safe_assistant_reply or safe_user_message)[:400],
        max_items=120,
    )
    row.profile = updated
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    cache_set_json(profile_cache_key(user_id), updated, ttl_sec=15)
