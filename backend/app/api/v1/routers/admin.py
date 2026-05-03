from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import AdminAuditLog, Conversation, CrisisLog, Resource
from app.services.db.session import get_db
from app.services.schemas.payloads import (
    AdminLoginRequest,
    AdminResourceCreateRequest,
    AdminResourceUpdateRequest,
)
from app.services.schemas.payloads import AdminLoginRequest, CrisisReviewRequest
from app.services.chat_cost_metrics import get_chat_cost_snapshot
from app.services.cookies import set_auth_cookies
from app.services.auth_latency_metrics import get_auth_latency_snapshot
from app.services.security import issue_admin_token, verify_password, verify_totp
from app.services.utils import make_id, utc_now

router = APIRouter(prefix="/admin", tags=["admin"])

RESOURCE_CATEGORIES = ["meditate", "sleep", "music", "work_study", "wisdom", "movement"]
RESOURCE_FORMATS = ["audio", "video", "article"]


def _audit(db: Session, admin_id: str, action: str, request: Request):
    db.add(
        AdminAuditLog(
            admin_id=admin_id,
            action=action,
            resource_accessed=str(request.url.path),
            ip_address=request.client.host if request.client else "0.0.0.0",
            metadata_json={},
        )
    )
    db.commit()


def _validate_resource_payload(category: str, format_value: str):
    if category not in RESOURCE_CATEGORIES:
        raise AppError("INVALID_PARAMETER", "Category không hợp lệ", 400)
    if format_value not in RESOURCE_FORMATS:
        raise AppError("INVALID_PARAMETER", "Format không hợp lệ", 400)


# ================= AUTH =================
@router.post("/auth/login")
def admin_login(payload: AdminLoginRequest, request: Request, response: Response):
    enforce_admin_ip(request)
    settings = get_settings()

    if not settings.admin_login_email or not settings.admin_password_hash or not settings.admin_totp_secret:
        raise AppError("ADMIN_CONFIG_MISSING", "Cấu hình admin chưa đầy đủ", 500)

    if payload.email.lower() != settings.admin_login_email.lower():
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    if not verify_password(payload.password, settings.admin_password_hash):
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    if not verify_totp(payload.totp_code, settings.admin_totp_secret):
        raise AppError("ADMIN_FORBIDDEN", "Bạn không có quyền truy cập", 403)

    admin_id = make_id("adm")
    token = issue_admin_token(admin_id)
    set_auth_cookies(response, access_token=token)

    return ok({"admin_id": admin_id, "expires_in": 900}, response=response)


@router.get("/auth/latency-sla")
def admin_auth_latency_sla(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    login = get_auth_latency_snapshot(flow="login")
    signup = get_auth_latency_snapshot(flow="signup")

    _audit(db, claims["sub"], "GET_AUTH_LATENCY_SLA", request)

    return ok(
        {
            "login": {
                "window": login.count,
                "success_rate": login.success_rate,
                "avg_ms": login.avg_ms,
                "p95_ms": login.p95_ms,
                "target_p95_ms": login.target_p95_ms,
                "within_sla": login.within_sla,
            },
            "signup": {
                "window": signup.count,
                "success_rate": signup.success_rate,
                "avg_ms": signup.avg_ms,
                "p95_ms": signup.p95_ms,
                "target_p95_ms": signup.target_p95_ms,
                "within_sla": signup.within_sla,
            },
        }
    )


# ================= DASHBOARD =================
@router.get("/dashboard/aggregate")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    total_sessions = db.scalar(select(func.count(Conversation.session_id))) or 0
    sos_events = db.scalar(select(func.count(CrisisLog.log_id))) or 0

    _audit(db, claims["sub"], "GET_DASHBOARD", request)

    return ok(
        {
            "period": {"from": "2026-04-01", "to": utc_now().date().isoformat()},
            "total_sessions": total_sessions,
            "avg_session_depth": 8.3,
            "mood_distribution": {
                "great": 18,
                "okay": 45,
                "stressed": 61,
                "struggling": 18,
            },
            "sos_events": sos_events,
            "top_resource_categories": ["meditate", "sleep"],
        }
    )


# ================= CRISIS LOG =================
@router.get("/crisis-logs")
def admin_crisis_logs(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    logs = db.scalars(
        select(CrisisLog)
        .order_by(CrisisLog.triggered_at.desc())
        .limit(100)
    ).all()

    _audit(db, claims["sub"], "GET_CRISIS_LOGS", request)

    return ok(
        {
            "logs": [
                {
                    "log_id": row.log_id,
                    "session_id": row.session_id,
                    "triggered_at": row.triggered_at.isoformat() + "Z",
                    "muc_do": row.muc_do,
                    "reviewed": row.reviewed,
                }
                for row in logs
            ],
            "total": len(logs),
            "has_more": False,
        }
    )


# ================= RESOURCE MANAGEMENT =================
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
                    "created_at": row.created_at.isoformat() + "Z",
                }
                for row in rows
            ],
            "total": total,
            "has_more": offset + len(rows) < total,
        }
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
            "created_at": row.created_at.isoformat() + "Z",
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
  
@router.patch("/crisis-logs/{log_id}/review")
def review_crisis_log(
    log_id: str,
    payload: CrisisReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    row = db.get(CrisisLog, log_id)
    if not row:
        raise AppError("CRISIS_LOG_NOT_FOUND", "Crisis log không tồn tại", 404)

    row.reviewed = bool(payload.reviewed)
    row.reviewed_at = utc_now().replace(tzinfo=None)
    row.reviewed_by = claims.get("sub")

    db.commit()

    _audit(db, claims["sub"], "PATCH_CRISIS_REVIEW", request)

    return ok(
        {
            "log_id": row.log_id,
            "reviewed": row.reviewed,
            "reviewed_at": row.reviewed_at.isoformat() + "Z" if row.reviewed_at else None,
            "reviewed_by": row.reviewed_by,
            "note": payload.note,
        }
    )
  
@router.get("/cost-dashboard")
def admin_cost_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    snapshot = get_chat_cost_snapshot()

    _audit(db, claims["sub"], "GET_COST_DASHBOARD", request)

    return ok(
        {
            "chat_cost": {
                "total_turns": snapshot.total_turns,
                "total_input_tokens": snapshot.total_input_tokens,
                "total_output_tokens": snapshot.total_output_tokens,
                "total_tokens": snapshot.total_tokens,
                "estimated_cost_usd": snapshot.estimated_cost_usd,
            }
        }
    )
  