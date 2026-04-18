from datetime import timedelta
from enum import Enum

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.db.models import ClinicalProfile, Conversation, MoodCheckin, User
from app.db.session import get_db
from app.services.utils import (
    local_date_utc7,
    utc_now,
    vn_month_chart_range,
    vn_period_utc_range,
    vn_week_chart_range,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardWindow(str, Enum):
    day = "day"
    week = "week"
    month = "month"


# TODO: tạm thời để như này. bao giờ xong scale chi tiết hơn, đổi thành thang 10
_MOOD_TO_SCORE = {
    "stressful": (1, "khó khăn"),
    "sad": (2, "buồn"),
    "neutral": (3, "ổn"),
    "peaceful": (4, "tốt"),
    "delightful": (5, "rất tốt"),
}


def _mood_score(mood: str | None) -> tuple[int, str]:
    if not mood:
        return 3, "ổn"
    return _MOOD_TO_SCORE.get(mood, (3, "ổn"))


@router.get("/overview")
def overview(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
    window: DashboardWindow | None = Query(
        default=None,
        description="Kèm thống kê phiên/check-in theo ngày, tuần (Thứ Hai–Chủ Nhật) hoặc tháng (từ mùng 1 đến hôm nay), theo giờ Việt Nam.",
    ),
):
    sessions_total = (
        db.scalar(select(func.count(Conversation.session_id)).where(Conversation.user_id == current_user.user_id)) or 0
    )
    today = local_date_utc7()
    mood_today = db.scalar(
        select(MoodCheckin).where(MoodCheckin.user_id == current_user.user_id, MoodCheckin.logged_date == today)
    )

    last_session_at = db.scalar(
        select(func.max(Conversation.last_message_at)).where(
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )

    clin = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == current_user.user_id))
    assessment = None
    if clin:
        assessment = {
            "phq9_score": clin.phq9_score,
            "gad7_score": clin.gad7_score,
            "crisis_level": clin.crisis_level,
            "last_scored_at": clin.last_scored_at.isoformat() + "Z" if clin.last_scored_at else None,
            "profile_updated_at": clin.updated_at.isoformat() + "Z" if clin.updated_at else None,
        }

    refreshed_at = utc_now().isoformat()

    payload: dict = {
        "user_id": current_user.user_id,
        "timezone": "Asia/Ho_Chi_Minh",
        "refreshed_at": refreshed_at,
        "session_count": sessions_total,
        "last_session_at": last_session_at.isoformat() + "Z" if last_session_at else None,
        "mood_today": {"checked_in": mood_today is not None, "mood": mood_today.mood if mood_today else None},
        "assessment": assessment,
    }

    if window is not None:
        date_from, date_to, start_utc, end_utc = vn_period_utc_range(window.value)
        sessions_in_window = (
            db.scalar(
                select(func.count(Conversation.session_id)).where(
                    Conversation.user_id == current_user.user_id,
                    Conversation.deleted_at.is_(None),
                    Conversation.last_message_at >= start_utc,
                    Conversation.last_message_at < end_utc,
                )
            )
            or 0
        )
        mood_rows = db.scalars(
            select(MoodCheckin)
            .where(
                MoodCheckin.user_id == current_user.user_id,
                MoodCheckin.logged_date >= date_from,
                MoodCheckin.logged_date <= date_to,
            )
            .order_by(MoodCheckin.logged_date.asc())
        ).all()
        scores = [_mood_score(r.mood)[0] for r in mood_rows]
        avg_mood = round(sum(scores) / len(scores), 2) if scores else None
        payload["window"] = {
            "kind": window.value,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sessions_with_activity": sessions_in_window,
            "mood_checkin_days": len(mood_rows),
            "avg_mood_score": avg_mood,
        }

    return ok(payload)


class MoodTrendPreset(str, Enum):
    week = "week"
    month = "month"


@router.get("/mood-trend")
def dashboard_mood_trend(
    days: int | None = Query(default=None, ge=1, le=90),
    preset: MoodTrendPreset | None = Query(
        default=None,
        description="week = 7 ngày gần nhất; month = từ mùng 1 đến hôm nay (giờ VN). Nếu không gửi preset và không gửi days, mặc định 7 ngày.",
    ),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    today = local_date_utc7()

    if preset == MoodTrendPreset.month:
        start, end, span = vn_month_chart_range()
        mode = "month"
    elif preset == MoodTrendPreset.week:
        start, end, span = vn_week_chart_range()
        mode = "week"
    else:
        n = days if days is not None else 7
        start = today - timedelta(days=n - 1)
        end = today
        span = n
        mode = "days"

    rows = db.scalars(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == current_user.user_id,
            MoodCheckin.logged_date >= start,
            MoodCheckin.logged_date <= end,
        )
        .order_by(MoodCheckin.logged_date.asc())
    ).all()
    point_map = {row.logged_date: row for row in rows}
    points = []
    missing = []
    for idx in range(span):
        day = start + timedelta(days=idx)
        if day not in point_map:
            missing.append(day.isoformat())
            continue
        item = point_map[day]
        score, label = _mood_score(item.mood)
        points.append({"date": day.isoformat(), "mood_score": score, "label": label, "emoji": item.emoji})

    return ok(
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "refreshed_at": utc_now().isoformat(),
            "mode": mode,
            "preset": preset.value if preset else None,
            "period": {"from": start.isoformat(), "to": end.isoformat()},
            "points": points,
            "days_missing": missing,
            "summary": "Xu hướng tâm trạng (dashboard).",
        }
    )


@router.get("/history")
def history(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
    window: DashboardWindow | None = Query(
        default=None,
        description="Lọc phiên có hoạt động trong ngày/tuần/tháng (giờ VN). Mặc định: 20 phiên gần nhất.",
    ),
    limit: int = Query(default=20, ge=1, le=50),
):
    stmt = select(Conversation).where(Conversation.user_id == current_user.user_id, Conversation.deleted_at.is_(None))
    if window is not None:
        _, _, start_utc, end_utc = vn_period_utc_range(window.value)
        stmt = stmt.where(Conversation.last_message_at >= start_utc, Conversation.last_message_at < end_utc)
    stmt = stmt.order_by(Conversation.last_message_at.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    return ok(
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "refreshed_at": utc_now().isoformat(),
            "window": window.value if window else None,
            "sessions": [
                {
                    "session_id": r.session_id,
                    "last_message_at": r.last_message_at.isoformat() + "Z",
                    "message_count": r.message_count,
                }
                for r in rows
            ],
        }
    )


@router.get("/follow-up")
def follow_up(current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    _ = db
    return ok({"items": [], "user_id": current_user.user_id})
