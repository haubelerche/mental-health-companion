from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import Bookmark, PlayEvent, Resource, User
from app.services.db.session import get_db
from app.services.schemas.payloads import PlayEventRequest
from app.services.exercise_catalog import get_exercise, list_exercises
from app.services.utils import make_id, get_now, get_youtube_id

router = APIRouter(prefix="/resources", tags=["resources"])

CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]


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


@router.get("")
def list_resources(
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    base_query = select(Resource).where(Resource.is_active.is_(True))
    count_query = select(func.count(Resource.resource_id)).where(Resource.is_active.is_(True))

    if category and category != "all":
        if category not in CATEGORIES:
            raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)
        base_query = base_query.where(Resource.category == category)
        count_query = count_query.where(Resource.category == category)

    total = db.scalar(count_query) or 0

    # 🔥 JOIN để tránh N+1
    stmt = (
        select(
            Resource,
            Bookmark.resource_id.isnot(None).label("bookmarked")
        )
        .outerjoin(
            Bookmark,
            and_(
                Bookmark.resource_id == Resource.resource_id,
                Bookmark.user_id == current_user.user_id
            )
        )
        .where(Resource.is_active.is_(True))
    )

    if category and category != "all":
        stmt = stmt.where(Resource.category == category)

    stmt = stmt.order_by(Resource.created_at.desc()).offset(offset).limit(limit)

    results = db.execute(stmt).all()

    items = []
    for row, bookmarked in results:
        # URL
        url = row.storage_key
        if not url.startswith(("http://", "https://")):
            url = f"https://www.youtube.com/watch?v={url}"

        # Thumbnail
        thumbnail = row.thumbnail_key
        if not thumbnail:
            yt_id = get_youtube_id(url)
            if yt_id:
                thumbnail = f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg"
        elif not thumbnail.startswith(("http://", "https://")):
            thumbnail = f"https://cdn.example.com/{thumbnail}"

        items.append(
            {
                "id": row.resource_id,
                "category": row.category,
                "title": row.title,
                "duration_sec": row.duration_sec,
                "format": row.format,
                "url": url,
                "thumbnail": thumbnail,
                "bookmarked": bookmarked,
            }
        )

    return ok({"items": items, "total": total, "has_more": offset + len(items) < total})


@router.get("/{resource_id}")
def resource_detail(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    # 🔥 JOIN luôn cho consistent
    stmt = (
        select(
            Resource,
            Bookmark.resource_id.isnot(None).label("bookmarked")
        )
        .outerjoin(
            Bookmark,
            and_(
                Bookmark.resource_id == Resource.resource_id,
                Bookmark.user_id == current_user.user_id
            )
        )
        .where(Resource.resource_id == resource_id, Resource.is_active.is_(True))
    )

    result = db.execute(stmt).first()

    if not result:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    row, bookmarked = result

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
            "bookmarked": bookmarked,
            "tags": row.tags,
        }
    )


@router.post("/{resource_id}/play-event")
def track_play_event(
    resource_id: str,
    payload: PlayEventRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(Resource).where(Resource.resource_id == resource_id, Resource.is_active.is_(True)))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    if payload.event not in {"started", "paused", "completed"}:
        raise AppError("INVALID_PARAMETER", "event không hợp lệ", 400)

    if payload.duration_sec > row.duration_sec * 2:
        raise AppError("INVALID_PARAMETER", "duration_sec quá lớn", 400)

    final_duration = min(payload.duration_sec, row.duration_sec)

    ev = PlayEvent(
        event_id=make_id("pev"),
        user_id=current_user.user_id,
        resource_id=resource_id,
        event=payload.event,
        duration_sec=final_duration,
        percent=payload.percent,
        tracked_at=get_now(),
    )

    db.add(ev)
    db.commit()

    return ok({"tracked_at": ev.tracked_at.isoformat() + "Z"})


@router.post("/{resource_id}/bookmark")
def create_bookmark(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    resource = db.scalar(select(Resource).where(Resource.resource_id == resource_id, Resource.is_active.is_(True)))
    if not resource:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    existing = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == current_user.user_id,
            Bookmark.resource_id == resource_id
        )
    )

    if not existing:
        existing = Bookmark(
            bookmark_id=make_id("bm"),
            user_id=current_user.user_id,
            resource_id=resource_id,
            bookmarked_at=get_now(),
        )
        db.add(existing)
        db.commit()

    return ok({"bookmarked_at": existing.bookmarked_at.isoformat() + "Z"}, status_code=201)


@router.delete("/{resource_id}/bookmark")
def remove_bookmark(
    resource_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == current_user.user_id,
            Bookmark.resource_id == resource_id
        )
    )

    if row:
        db.delete(row)
        db.commit()

    return ok({"removed_at": get_now().isoformat()})