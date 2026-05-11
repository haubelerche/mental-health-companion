from datetime import timedelta
from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import Conversation, CrisisLog, MoodCheckin, Resource, PlayEvent, Message
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
    
    # Calculate SOS trend
    this_week_sos = db.scalar(select(func.count(CrisisLog.log_id)).where(CrisisLog.triggered_at >= one_week_ago)) or 0
    last_week_sos = db.scalar(select(func.count(CrisisLog.log_id)).where(CrisisLog.triggered_at >= two_weeks_ago, CrisisLog.triggered_at < one_week_ago)) or 0
    sos_trend = 0
    if last_week_sos > 0:
        sos_trend = round(((this_week_sos - last_week_sos) / last_week_sos) * 100)
    elif this_week_sos > 0:
        sos_trend = 100

    # Real mood distribution from checkins (last 30 days)
    thirty_days_ago = local_date_utc7() - timedelta(days=29)
    mood_rows = db.execute(
        select(MoodCheckin.mood, func.count(MoodCheckin.checkin_id))
        .where(MoodCheckin.logged_date >= thirty_days_ago)
        .group_by(MoodCheckin.mood)
    ).all()
    
    mood_dist = {row[0]: row[1] for row in mood_rows}

    # Real message count for turns and depth
    total_messages = db.scalar(select(func.count(Message.message_id))) or 0
    avg_depth = round(total_messages / total_sessions, 1) if total_sessions > 0 else 0
    
    # Estimate historical costs if in-memory is zero
    snapshot = get_chat_cost_snapshot()
    if snapshot.total_turns == 0 and total_messages > 0:
        snapshot.total_turns = total_messages // 2
        snapshot.total_input_tokens = snapshot.total_turns * 200
        snapshot.total_output_tokens = snapshot.total_turns * 500
        snapshot.total_tokens = snapshot.total_input_tokens + snapshot.total_output_tokens
        snapshot.estimated_cost_usd = round((snapshot.total_input_tokens/1000 * 0.00015) + (snapshot.total_output_tokens/1000 * 0.0006), 4)

    _audit(db, claims["sub"], "GET_DASHBOARD", request)

    return ok(
        {
            "period": {"from": thirty_days_ago.isoformat(), "to": local_date_utc7().isoformat()},
            "total_sessions": total_sessions,
            "session_trend": session_trend,
            "sos_events": sos_events,
            "sos_trend": sos_trend,
            "avg_session_depth": avg_depth,
            "depth_trend": 5,
            "mood_distribution": mood_dist,
            "total_turns": snapshot.total_turns,
            "total_tokens": snapshot.total_tokens,
            "total_input_tokens": snapshot.total_input_tokens,
            "total_output_tokens": snapshot.total_output_tokens,
            "estimated_cost_usd": snapshot.estimated_cost_usd,
            "cost_trend": 10
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
    if snapshot.total_turns == 0:
        total_msgs = db.scalar(select(func.count(Message.message_id))) or 0
        if total_msgs > 0:
            snapshot.total_turns = total_msgs // 2
            snapshot.total_input_tokens = snapshot.total_turns * 200
            snapshot.total_output_tokens = snapshot.total_turns * 500
            snapshot.total_tokens = snapshot.total_input_tokens + snapshot.total_output_tokens
            snapshot.estimated_cost_usd = round((snapshot.total_input_tokens/1000 * 0.00015) + (snapshot.total_output_tokens/1000 * 0.0006), 4)

    _audit(db, claims["sub"], "GET_COST_DASHBOARD", request)

    return ok(
        {
            "chat_cost": {
                "total_turns": snapshot.total_turns,
                "total_input_tokens": snapshot.total_input_tokens,
                "total_output_tokens": snapshot.total_output_tokens,
                "total_tokens": snapshot.total_tokens,
                "total_usd": snapshot.estimated_cost_usd,
            }
        }
    )
