from datetime import timedelta
from fastapi import Depends, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import MoodCheckin, ClinicalProfile, Resource, PlayEvent, Bookmark, HeartWallet, User, HeartRewardEvent
from app.services.utils import local_date_utc7
from .shared import router

@router.get("/analytics/mood-distribution")
def admin_analytics_mood_distribution(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    from_date = local_date_utc7() - timedelta(days=days-1)
    rows = db.execute(
        select(MoodCheckin.mood, func.count(MoodCheckin.checkin_id))
        .where(MoodCheckin.logged_date >= from_date)
        .group_by(MoodCheckin.mood)
    ).all()
    dist = {row[0]: row[1] for row in rows}
    return ok({"distribution": dist})

@router.get("/analytics/mood-trend")
def admin_analytics_mood_trend(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    from_date = local_date_utc7() - timedelta(days=days-1)
    rows = db.execute(
        select(MoodCheckin.logged_date, func.count(MoodCheckin.checkin_id))
        .where(MoodCheckin.logged_date >= from_date)
        .group_by(MoodCheckin.logged_date)
        .order_by(MoodCheckin.logged_date.asc())
    ).all()
    trend = [{"date": row[0].isoformat(), "count": row[1]} for row in rows]
    return ok({"trend": trend})

@router.get("/analytics/clinical-overview")
def admin_analytics_clinical_overview(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    phq9_rows = db.execute(
        select(
            func.count(ClinicalProfile.profile_id),
            case(
                (ClinicalProfile.phq9_score < 5, "minimal"),
                (ClinicalProfile.phq9_score < 10, "mild"),
                (ClinicalProfile.phq9_score < 15, "moderate"),
                (ClinicalProfile.phq9_score < 20, "moderately_severe"),
                else_="severe"
            ).label("severity")
        )
        .where(ClinicalProfile.phq9_score.is_not(None))
        .group_by("severity")
    ).all()
    phq9_dist = {row[1]: row[0] for row in phq9_rows}
    crisis_counts = db.execute(
        select(ClinicalProfile.crisis_level, func.count(ClinicalProfile.profile_id))
        .group_by(ClinicalProfile.crisis_level)
    ).all()
    crisis_dist = {row[0]: row[1] for row in crisis_counts}
    return ok({"phq9_distribution": phq9_dist, "crisis_distribution": crisis_dist})

@router.get("/analytics/resources")
def admin_analytics_resources(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    top_played = db.execute(
        select(Resource.title, func.count(PlayEvent.event_id))
        .join(PlayEvent, PlayEvent.resource_id == Resource.resource_id)
        .group_by(Resource.title)
        .order_by(func.count(PlayEvent.event_id).desc())
        .limit(10)
    ).all()
    top_bookmarked = db.execute(
        select(Resource.title, func.count(Bookmark.bookmark_id))
        .join(Bookmark, Bookmark.resource_id == Resource.resource_id)
        .group_by(Resource.title)
        .order_by(func.count(Bookmark.bookmark_id).desc())
        .limit(10)
    ).all()
    return ok({
        "top_played": [{"title": row[0], "count": row[1]} for row in top_played],
        "top_bookmarked": [{"title": row[0], "count": row[1]} for row in top_bookmarked]
    })

@router.get("/analytics/hearts")
def admin_analytics_hearts(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    total_issued = db.scalar(select(func.sum(HeartWallet.lifetime_earned))) or 0
    total_spent = db.scalar(select(func.sum(HeartWallet.lifetime_spent))) or 0
    current_balance = db.scalar(select(func.sum(HeartWallet.balance))) or 0
    top_earners = db.execute(
        select(User.display_name, HeartWallet.lifetime_earned)
        .join(User, User.user_id == HeartWallet.user_id)
        .order_by(HeartWallet.lifetime_earned.desc())
        .limit(10)
    ).all()
    return ok({
        "total_issued": total_issued,
        "total_spent": total_spent,
        "current_balance": current_balance,
        "top_earners": [{"name": row[0], "amount": row[1]} for row in top_earners]
    })

@router.get("/analytics/emotion-resource-suggestion")
def admin_emotion_resource_suggestion(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    # 1. Analyze mood in last 7 days
    seven_days_ago = local_date_utc7() - timedelta(days=6)
    rows = db.execute(
        select(MoodCheckin.mood, func.count(MoodCheckin.checkin_id))
        .where(MoodCheckin.logged_date >= seven_days_ago)
        .group_by(MoodCheckin.mood)
    ).all()
    
    dist = {row[0]: row[1] for row in rows}
    total = sum(dist.values()) or 1
    
    # 2. Logic to suggest category
    # stressful, sad, neutral, peaceful, delightful
    stress_pct = (dist.get("stressful", 0) + dist.get("sad", 0)) / total
    
    suggestions = []
    if stress_pct > 0.4:
        suggestions.append({
            "category": "meditate",
            "priority": "high",
            "reason": f"Có tới {int(stress_pct*100)}% người dùng đang cảm thấy căng thẳng hoặc buồn bã."
        })
        suggestions.append({
            "category": "music",
            "priority": "medium",
            "reason": "Âm nhạc giúp thư giãn tinh thần hiệu quả trong giai đoạn căng thẳng."
        })
    elif dist.get("delightful", 0) / total > 0.3:
         suggestions.append({
            "category": "wisdom",
            "priority": "medium",
            "reason": "Người dùng đang có tâm trạng tốt, thích hợp để tiếp thu kiến thức mới."
        })
    else:
        suggestions.append({
            "category": "sleep",
            "priority": "medium",
            "reason": "Cải thiện giấc ngủ luôn là nhu cầu cơ bản cho sức khỏe tâm thần."
        })
        
    return ok({
        "mood_summary": dist,
        "suggestions": suggestions
    })
