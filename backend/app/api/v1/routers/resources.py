from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import Bookmark, PlayEvent, Resource, User
from app.db.session import get_db
from app.schemas.payloads import PlayEventRequest
from app.services.utils import make_id, now_plus, utc_now

router = APIRouter(prefix="/resources", tags=["resources"])

CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]


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
    category: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if category not in CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)

    total = (
        db.scalar(
            select(func.count(Resource.resource_id)).where(
                Resource.category == category,
                Resource.is_active.is_(True),
            )
        )
        or 0
    )

    rows = db.scalars(
        select(Resource)
        .where(Resource.category == category, Resource.is_active.is_(True))
        .order_by(Resource.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = []
    for row in rows:
        bookmarked = db.scalar(
            select(Bookmark).where(Bookmark.user_id == current_user.user_id, Bookmark.resource_id == row.resource_id)
        )
        expires_at = now_plus(seconds=3600).isoformat().replace("+00:00", "Z")
        items.append(
            {
                "id": row.resource_id,
                "category": row.category,
                "title": row.title,
                "duration_sec": row.duration_sec,
                "format": row.format,
                "url": f"https://cdn.example.com/{row.storage_key}?sig=dummy",
                "url_expires_at": expires_at,
                "thumbnail": f"https://cdn.example.com/{row.thumbnail_key}" if row.thumbnail_key else None,
                "bookmarked": bookmarked is not None,
            }
        )

    return ok({"items": items, "total": total, "has_more": offset + len(items) < total})


@router.get("/{resource_id}")
def resource_detail(resource_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Resource).where(Resource.resource_id == resource_id, Resource.is_active.is_(True)))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    bookmarked = db.scalar(
        select(Bookmark).where(Bookmark.user_id == current_user.user_id, Bookmark.resource_id == row.resource_id)
    )
    expires_at = now_plus(seconds=3600).isoformat().replace("+00:00", "Z")
    return ok(
        {
            "id": row.resource_id,
            "category": row.category,
            "title": row.title,
            "description": row.description,
            "duration_sec": row.duration_sec,
            "format": row.format,
            "url": f"https://cdn.example.com/{row.storage_key}?sig=dummy",
            "url_expires_at": expires_at,
            "thumbnail": f"https://cdn.example.com/{row.thumbnail_key}" if row.thumbnail_key else None,
            "bookmarked": bookmarked is not None,
            "tags": row.tags,
        }
    )


@router.post("/{resource_id}/play-event")
def track_play_event(
    resource_id: str,
    payload: PlayEventRequest,
    current_user: User = Depends(get_current_user),
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
    )
    db.add(ev)
    db.commit()
    return ok({"tracked_at": ev.tracked_at.isoformat() + "Z"})


@router.post("/{resource_id}/bookmark")
def create_bookmark(resource_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resource = db.scalar(select(Resource).where(Resource.resource_id == resource_id, Resource.is_active.is_(True)))
    if not resource:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    existing = db.scalar(
        select(Bookmark).where(Bookmark.user_id == current_user.user_id, Bookmark.resource_id == resource_id)
    )
    if not existing:
        existing = Bookmark(bookmark_id=make_id("bm"), user_id=current_user.user_id, resource_id=resource_id)
        db.add(existing)
        db.commit()

    return ok({"bookmarked_at": existing.bookmarked_at.isoformat() + "Z"}, status_code=201)


@router.delete("/{resource_id}/bookmark")
def remove_bookmark(resource_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Bookmark).where(Bookmark.user_id == current_user.user_id, Bookmark.resource_id == resource_id))
    if row:
        db.delete(row)
        db.commit()
    return ok({"removed_at": utc_now().isoformat().replace("+00:00", "Z")})
