from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import User, ClinicalProfile, HeartWallet, StreakState, MoodCheckin, Conversation
from app.services.schemas.payloads import AdminUserUpdateRequest
from .shared import router, _audit

@router.get("/users")
def admin_list_users(
    request: Request,
    is_active: bool | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    where_conditions = []
    if is_active is not None:
        where_conditions.append(User.is_active == is_active)
    if query:
        where_conditions.append(User.email.ilike(f"%{query}%") | User.display_name.ilike(f"%{query}%"))
        
    stmt = select(User)
    if where_conditions:
        stmt = stmt.where(*where_conditions)
        
    total = db.scalar(select(func.count(User.user_id)).where(*where_conditions)) if where_conditions else db.scalar(select(func.count(User.user_id)))
    
    users = db.scalars(stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)).all()
    
    _audit(db, claims["sub"], "LIST_USERS", request)
    
    return ok({
        "users": [{
            "user_id": u.user_id,
            "display_name": u.display_name,
            "email": u.email,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "last_active": u.last_active.isoformat()
        } for u in users],
        "total": total or 0
    })

@router.get("/users/{user_id}/detail")
def admin_user_detail(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    user = db.get(User, user_id)
    if not user:
        raise AppError("NOT_FOUND", "Người dùng không tồn tại", 404)
        
    clin = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    wallet = db.scalar(select(HeartWallet).where(HeartWallet.user_id == user_id))
    streak = db.scalar(select(StreakState).where(StreakState.user_id == user_id))
    latest_mood = db.scalar(select(MoodCheckin).where(MoodCheckin.user_id == user_id).order_by(MoodCheckin.logged_at.desc()).limit(1))
    conv_count = db.scalar(select(func.count(Conversation.session_id)).where(Conversation.user_id == user_id))
    
    _audit(db, claims["sub"], f"VIEW_USER_DETAIL_{user_id}", request)
    
    return ok({
        "user": {
            "user_id": user.user_id,
            "display_name": user.display_name,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "last_active": user.last_active.isoformat(),
            "disclaimer_accepted": user.disclaimer_accepted,
        },
        "clinical": {
            "phq9_score": clin.phq9_score if clin else None,
            "gad7_score": clin.gad7_score if clin else None,
            "crisis_level": clin.crisis_level if clin else 0,
            "updated_at": clin.updated_at.isoformat() if clin else None,
        },
        "economy": {
            "heart_balance": wallet.balance if wallet else 0,
            "streak_days": streak.current_mood_checkin_streak if streak else 0,
        },
        "latest_mood": {
            "mood": latest_mood.mood if latest_mood else None,
            "emoji": latest_mood.emoji if latest_mood else None,
            "logged_at": latest_mood.logged_at.isoformat() if latest_mood else None,
        },
        "stats": {
            "total_conversations": conv_count or 0
        }
    })

@router.patch("/users/{user_id}")
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    user = db.get(User, user_id)
    if not user:
        raise AppError("NOT_FOUND", "Người dùng không tồn tại", 404)
        
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.display_name is not None:
        user.display_name = payload.display_name
        
    db.commit()
    
    _audit(db, claims["sub"], f"UPDATE_USER_{user_id}", request)
    
    return ok({"user_id": user_id, "updated": True})
