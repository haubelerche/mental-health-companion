from datetime import timedelta
from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import Conversation, CrisisLog, MoodCheckin, Resource, PlayEvent
from app.services.chat_cost_metrics import get_chat_cost_snapshot
from app.services.utils import local_date_utc7
from .shared import router, _audit

@router.get("/dashboard/aggregate")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)

    total_sessions = db.scalar(select(func.count(Conversation.session_id))) or 0
    
    # Calculate real session trend (this week vs last week)
    now = local_date_utc7()
    one_week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    
    this_week_sessions = db.scalar(
        select(func.count(Conversation.session_id))
        .where(Conversation.started_at >= one_week_ago)
    ) or 0
    last_week_sessions = db.scalar(
        select(func.count(Conversation.session_id))
        .where(Conversation.started_at >= two_weeks_ago)
        .where(Conversation.started_at < one_week_ago)
    ) or 0
    
    session_trend = 0
    if last_week_sessions > 0:
        session_trend = round(((this_week_sessions - last_week_sessions) / last_week_sessions) * 100)
    elif this_week_sessions > 0:
        session_trend = 100
        
    sos_events = db.scalar(select(func.count(CrisisLog.log_id))) or 0
    
    # Real mood distribution from checkins (last 30 days)
    thirty_days_ago = local_date_utc7() - timedelta(days=29)
    mood_rows = db.execute(
        select(MoodCheckin.mood, func.count(MoodCheckin.checkin_id))
        .where(MoodCheckin.logged_date >= thirty_days_ago)
        .group_by(MoodCheckin.mood)
    ).all()
    
    mood_dist = {row[0]: row[1] for row in mood_rows}

    # Top resource categories by play events
    top_cats_rows = db.execute(
        select(Resource.category, func.count(PlayEvent.event_id))
        .join(PlayEvent, PlayEvent.resource_id == Resource.resource_id)
        .group_by(Resource.category)
        .order_by(func.count(PlayEvent.event_id).desc())
        .limit(3)
    ).all()
    top_cats = [row[0] for row in top_cats_rows] if top_cats_rows else ["meditate", "sleep"]

    _audit(db, claims["sub"], "GET_DASHBOARD", request)

    return ok(
        {
            "period": {"from": thirty_days_ago.isoformat(), "to": local_date_utc7().isoformat()},
            "total_sessions": total_sessions,
            "session_trend": session_trend,
            "avg_session_depth": 8.3,
            "mood_distribution": mood_dist,
            "sos_events": sos_events,
            "top_resource_categories": top_cats,
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
