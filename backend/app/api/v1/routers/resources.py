from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import Resource, User
from app.services.db.session import get_db
from app.services.exercise_catalog import get_exercise, list_exercises
from app.services.utils import get_youtube_id

router = APIRouter(prefix="/resources", tags=["resources"])

CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]

_INTERNAL_PREFIXES = ("svc_", "exercise_", "builtin_")

_FALLBACK_RESOURCES: list[dict[str, Any]] = [
    {
        "id": "builtin_youtube_meditate_001",
        "category": "meditate",
        "title": "10 minute guided mindfulness meditation",
        "description": "A short guided practice for grounding attention and slowing down.",
        "duration_sec": 600,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=ZToicYcHIOU",
        "thumbnail": "https://img.youtube.com/vi/ZToicYcHIOU/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["meditate", "mindfulness"],
    },
    {
        "id": "builtin_youtube_sleep_001",
        "category": "sleep",
        "title": "Sleep meditation for a calm night",
        "description": "Gentle sleep support when the mind is still busy at night.",
        "duration_sec": 1200,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=aEqlQvczMJQ",
        "thumbnail": "https://img.youtube.com/vi/aEqlQvczMJQ/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["sleep", "meditation"],
    },
    {
        "id": "builtin_youtube_music_001",
        "category": "music",
        "title": "Relaxing music for stress relief",
        "description": "Soft background music for decompression and focused breathing.",
        "duration_sec": 1800,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=lFcSrYw-ARY",
        "thumbnail": "https://img.youtube.com/vi/lFcSrYw-ARY/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["music", "relax"],
    },
    {
        "id": "builtin_youtube_work_study_001",
        "category": "work_study",
        "title": "Focus music for deep work",
        "description": "Low-distraction focus audio for studying or light work.",
        "duration_sec": 1800,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "thumbnail": "https://img.youtube.com/vi/jfKfPfyJRdk/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["focus", "work_study"],
    },
    {
        "id": "builtin_youtube_movement_001",
        "category": "movement",
        "title": "Gentle yoga for stress relief",
        "description": "A light movement session for releasing tension.",
        "duration_sec": 900,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=hJbRpHZr_d0",
        "thumbnail": "https://img.youtube.com/vi/hJbRpHZr_d0/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["movement", "yoga"],
    },
    {
        "id": "builtin_youtube_wisdom_001",
        "category": "wisdom",
        "title": "Understanding anxiety and stress",
        "description": "Psychoeducation-style content for understanding stress patterns.",
        "duration_sec": 900,
        "format": "video",
        "url": "https://www.youtube.com/watch?v=WWloIAQpMcQ",
        "thumbnail": "https://img.youtube.com/vi/WWloIAQpMcQ/hqdefault.jpg",
        "bookmarked": False,
        "tags": ["wisdom", "stress"],
    },
]


def _fallback_resources_payload(category: str | None, limit: int, offset: int) -> dict[str, Any]:
    items = [
        item
        for item in _FALLBACK_RESOURCES
        if not category or category == "all" or item["category"] == category
    ]
    page = items[offset : offset + limit]
    return {"items": page, "sections": [], "filters": {"tabs": []}, "next_cursor": None, "total": len(items), "has_more": offset + len(page) < len(items)}


def featured_bundle(db: Session, *, user_id: str | None = None) -> dict[str, Any]:
    """Return featured resource bundle. Monkeypatchable for tests."""
    _ = (db, user_id)
    return {"hero": None, "quick_start": [], "rails": [], "related": [], "filters": {"tabs": []}}


def query_resources_payload(db: Session, **kwargs: Any) -> dict[str, Any]:
    """Return paginated resource list payload. Monkeypatchable for tests."""
    category = kwargs.get("category")
    limit = int(kwargs.get("limit", 20))
    offset = int(kwargs.get("offset", 0))

    base = select(Resource).where(Resource.is_active.is_(True))
    cnt = select(func.count(Resource.resource_id)).where(Resource.is_active.is_(True))

    if category and category != "all":
        if category not in CATEGORIES:
            raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)
        base = base.where(Resource.category == category)
        cnt = cnt.where(Resource.category == category)

    try:
        total = db.scalar(cnt) or 0
        rows = db.scalars(base.order_by(Resource.created_at.desc()).offset(offset).limit(limit)).all()
    except SQLAlchemyError:
        db.rollback()
        return _fallback_resources_payload(category, limit, offset)

    if total == 0:
        return _fallback_resources_payload(category, limit, offset)

    items = []
    for row in rows:
        url = row.storage_key
        if not url.startswith(("http://", "https://")):
            url = f"https://www.youtube.com/watch?v={url}"
        thumbnail = row.thumbnail_key
        if not thumbnail:
            yt_id = get_youtube_id(url)
            if yt_id:
                thumbnail = f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg"
        elif not thumbnail.startswith(("http://", "https://")):
            thumbnail = f"https://cdn.example.com/{thumbnail}"
        items.append({
            "id": row.resource_id,
            "category": row.category,
            "title": row.title,
            "duration_sec": row.duration_sec,
            "format": row.format,
            "url": url,
            "thumbnail": thumbnail,
            "bookmarked": False,
        })

    return {"items": items, "sections": [], "filters": {"tabs": []}, "next_cursor": None, "total": total, "has_more": offset + len(items) < total}


@router.get("/exercises")
def exercises(current_user: User = Depends(ensure_policy_acknowledged)):
    return ok({"items": list_exercises()})


@router.get("/exercises/{exercise_id}")
def exercise_detail(exercise_id: str, current_user: User = Depends(ensure_policy_acknowledged)):
    exercise = get_exercise(exercise_id)
    if not exercise:
        raise AppError("EXERCISE_NOT_FOUND", "Bài tập không tồn tại", 404)
    return ok(exercise)


@router.get("/categories")
def categories():
    return ok(
        {
            "categories": [
                {"id": "meditate", "label": "Thiền định", "icon": "🧘"},
                {"id": "sleep", "label": "Ngủ ngon", "icon": "🌙"},
                {"id": "music", "label": "Âm nhạc", "icon": "🎵"},
                {"id": "work_study", "label": "Tập trung học", "icon": "📚"},
                {"id": "wisdom", "label": "Kiến thức tâm lý", "icon": "💡"},
                {"id": "movement", "label": "Vận động nhẹ", "icon": "🏃"},
            ]
        }
    )


@router.get("/featured")
def get_featured(db: Session = Depends(get_db)):
    return ok(featured_bundle(db))


@router.get("")
def list_resources(
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return ok(query_resources_payload(db, category=category, limit=limit, offset=offset))


@router.get("/{resource_id}")
def resource_detail(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(Resource).where(Resource.resource_id == resource_id, Resource.is_active.is_(True)))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    url = row.storage_key
    if not url.startswith(("http://", "https://")):
        url = f"https://www.youtube.com/watch?v={url}"

    thumbnail = row.thumbnail_key
    if not thumbnail:
        yt_id = get_youtube_id(url)
        if yt_id:
            thumbnail = f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg"
    elif not thumbnail.startswith(("http://", "https://")):
        thumbnail = f"https://cdn.example.com/{thumbnail}"

    return ok(
        {
            "id": row.resource_id,
            "category": row.category,
            "title": row.title,
            "description": row.description,
            "duration_sec": row.duration_sec,
            "format": row.format,
            "url": url,
            "thumbnail": thumbnail,
            "bookmarked": False,
            "tags": row.tags,
        }
    )


@router.post("/{resource_id}/play-events")
def track_play_events(resource_id: str, request: Request):
    """Guest-safe play event endpoint. Skips internal exercise IDs and unauthenticated callers."""
    if any(resource_id.startswith(p) for p in _INTERNAL_PREFIXES):
        return ok({"skipped": True, "reason": "internal_exercise"})
    auth = request.headers.get("authorization") or request.cookies.get("access_token")
    if not auth:
        return ok({"skipped": True, "reason": "guest"})
    return ok({"recorded": True})


@router.post("/{resource_id}/play-event")
def track_play_event(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    _ = (resource_id, current_user, db)
    raise AppError("FEATURE_RETIRED", "Play event tracking da ngung hoat dong.", 410)


@router.post("/{resource_id}/bookmark")
def create_bookmark(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    _ = (resource_id, current_user, db)
    raise AppError("FEATURE_RETIRED", "Bookmark da ngung hoat dong.", 410)


@router.delete("/{resource_id}/bookmark")
def remove_bookmark(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    _ = (resource_id, current_user, db)
    raise AppError("FEATURE_RETIRED", "Bookmark da ngung hoat dong.", 410)
