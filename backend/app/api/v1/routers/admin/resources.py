from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import Resource
from app.services.schemas.payloads import AdminResourceCreateRequest, AdminResourceUpdateRequest, AdminAgentCrawlRequest
from app.services.youtube_agent import run_youtube_crawl_agent
from app.services.utils import make_id, utc_now
from .shared import router, _audit, _validate_resource_payload, RESOURCE_CATEGORIES

@router.get("/resources")
def admin_list_resources(
    request: Request,
    category: str | None = None,
    include_inactive: bool = True,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    if category is not None and category not in RESOURCE_CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)

    if limit < 1 or limit > 100 or offset < 0:
        raise AppError("INVALID_PARAMETER", "limit/offset không hợp lệ", 400)

    where_conditions = []
    if category:
        where_conditions.append(Resource.category == category)
    if not include_inactive:
        where_conditions.append(Resource.is_active.is_(True))

    base_query = select(Resource)
    count_query = select(func.count(Resource.resource_id))

    if where_conditions:
        base_query = base_query.where(*where_conditions)
        count_query = count_query.where(*where_conditions)

    total = db.scalar(count_query) or 0
    rows = db.scalars(
        base_query.order_by(Resource.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    _audit(db, claims["sub"], "LIST_RESOURCES", request)

    return ok(
        {
            "items": [
                {
                    "resource_id": row.resource_id,
                    "category": row.category,
                    "title": row.title,
                    "description": row.description,
                    "format": row.format,
                    "duration_sec": row.duration_sec,
                    "storage_key": row.storage_key,
                    "thumbnail_key": row.thumbnail_key,
                    "tags": row.tags,
                    "is_active": row.is_active,
                    "created_at": row.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                }
                for row in rows
            ],
            "total": total,
            "has_more": offset + len(rows) < total,
        }
    )

@router.post("/resources/agent-crawl")
async def admin_agent_crawl_resources(
    payload: AdminAgentCrawlRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    if payload.category not in RESOURCE_CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)

    _audit(db, claims["sub"], "AGENT_CRAWL_RESOURCES", request)

    return StreamingResponse(
        run_youtube_crawl_agent(payload.category, payload.limit, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/resources")
def admin_create_resource(
    payload: AdminResourceCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    _validate_resource_payload(payload.category, payload.format)

    row = Resource(
        resource_id=make_id("res"),
        category=payload.category,
        title=payload.title,
        description=payload.description,
        format=payload.format,
        duration_sec=payload.duration_sec,
        storage_key=payload.storage_key,
        thumbnail_key=payload.thumbnail_key,
        tags=payload.tags,
        is_active=payload.is_active,
    )

    db.add(row)
    db.commit()

    _audit(db, claims["sub"], "CREATE_RESOURCE", request)

    return ok(
        {
            "resource_id": row.resource_id,
            "created_at": row.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
        },
        status_code=201,
    )

@router.patch("/resources/{resource_id}")
def admin_update_resource(
    resource_id: str,
    payload: AdminResourceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    row = db.scalar(select(Resource).where(Resource.resource_id == resource_id))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    provided = payload.model_fields_set

    next_category = payload.category if "category" in provided else row.category
    next_format = payload.format if "format" in provided else row.format
    _validate_resource_payload(next_category, next_format)

    if "category" in provided:
        row.category = payload.category
    if "title" in provided:
        row.title = payload.title
    if "description" in provided:
        row.description = payload.description
    if "format" in provided:
        row.format = payload.format
    if "duration_sec" in provided:
        row.duration_sec = payload.duration_sec
    if "storage_key" in provided:
        row.storage_key = payload.storage_key
    if "thumbnail_key" in provided:
        row.thumbnail_key = payload.thumbnail_key
    if "tags" in provided:
        row.tags = payload.tags
    if "is_active" in provided:
        row.is_active = payload.is_active

    db.commit()

    _audit(db, claims["sub"], "UPDATE_RESOURCE", request)

    return ok(
        {
            "resource_id": row.resource_id,
            "updated_at": utc_now().isoformat().replace("+00:00", "Z"),
        }
    )

@router.delete("/resources/{resource_id}")
def admin_delete_resource(
    resource_id: str,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    row = db.scalar(select(Resource).where(Resource.resource_id == resource_id))
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Resource không tồn tại", 404)

    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "RESOURCE_IN_USE",
            "Resource đang có dữ liệu liên quan, không thể xóa cứng",
            409,
        ) from exc

    _audit(db, claims["sub"], "DELETE_RESOURCE", request)

    return ok(
        {
            "resource_id": resource_id,
            "deleted_at": utc_now().isoformat().replace("+00:00", "Z"),
        }
    )
