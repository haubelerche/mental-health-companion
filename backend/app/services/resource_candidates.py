"""Fetch YouTube resource candidates from DB for chat context injection."""
from __future__ import annotations

import unicodedata
import re
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.services.db.models import Resource

_TOPIC_CATEGORY_MAP: list[tuple[tuple[str, ...], str]] = [
    (("mat ngu", "kho ngu", "ngu khong duoc", "buon ngu", "sleep"), "sleep"),
    (("thien", "meditation", "tho", "chim nilem", "chanh niem"), "meditate"),
    (("met", "kiet suc", "burnout", "can kiet", "duoi suc"), "movement"),
    (("lo", "overthinking", "nghi nhieu", "bất an", "bat an", "stress"), "meditate"),
    (("buon", "khoc", "co don", "mot minh", "thất vọng", "that vong"), "music"),
    (("tuc", "gian", "buc boi", "buc xuc"), "movement"),
    (("hoc", "deadline", "on thi", "bai tap", "tap trung"), "work_study"),
    (("tri tue", "kien thuc", "hieu", "tam ly", "learn"), "wisdom"),
    (("nhac", "music", "nghe nhac", "am nhac"), "music"),
]

_SUGGESTION_PHRASES = [
    "Mình thấy video này có thể giúp cậu một chút: **{title}**",
    "Nếu cậu muốn thử, có một clip phù hợp đây: **{title}**",
    "Có thể cậu sẽ thích video này: **{title}**",
]

_SUGGESTION_IDX = 0


def _fold(text: str) -> str:
    norm = unicodedata.normalize("NFD", text or "")
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    norm = norm.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", norm.lower()).strip()


def _detect_category(user_message: str) -> str:
    folded = _fold(user_message)
    for keywords, category in _TOPIC_CATEGORY_MAP:
        if any(kw in folded for kw in keywords):
            return category
    return "meditate"


def fetch_resource_candidates(
    distress_score: float,
    user_message: str,
    db: Session,
    limit: int = 2,
) -> list[dict]:
    """Return up to `limit` video candidates from DB for injection into ContextPack.

    Returns [] when distress is below threshold or DB has no matching rows.
    """
    if distress_score < 0.35:
        return []

    category = _detect_category(user_message)
    rows = db.scalars(
        select(Resource)
        .where(Resource.is_active.is_(True), Resource.category == category)
        .order_by(func.random())
        .limit(limit)
    ).all()

    if not rows:
        # fallback: any active resource
        rows = db.scalars(
            select(Resource)
            .where(Resource.is_active.is_(True))
            .order_by(func.random())
            .limit(limit)
        ).all()

    results = []
    for row in rows:
        url = row.storage_key
        if not url.startswith(("http://", "https://")):
            url = f"https://www.youtube.com/watch?v={url}"
        results.append({
            "resource_id": row.resource_id,
            "title": row.title,
            "url": url,
            "thumbnail": row.thumbnail_key or "",
            "category": row.category,
            "why_this": f"Phù hợp với tình huống của bạn",
        })
    return results


def make_video_mention(candidates: list[dict]) -> str | None:
    """Return a natural-language mention for the first candidate, or None."""
    if not candidates:
        return None
    global _SUGGESTION_IDX
    phrase = _SUGGESTION_PHRASES[_SUGGESTION_IDX % len(_SUGGESTION_PHRASES)]
    _SUGGESTION_IDX += 1
    title = candidates[0].get("title", "")
    if not title:
        return None
    return phrase.format(title=title)
