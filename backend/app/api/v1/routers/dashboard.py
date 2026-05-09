from collections import defaultdict
from datetime import timedelta
from enum import Enum

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.dashboard.service import (
    build_checkin_history,
    build_reflect_summary,
    build_safe_insights_payload,
)
from app.services.db.models import ClinicalProfile, Conversation, MoodCheckin, User, UserProfile
from app.services.db.session import get_db
from app.services.utils import (
    local_date_utc7,
    get_now,
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


def _top_items(counter_map: dict, *, limit: int = 3) -> list[dict]:
    ranked: list[dict] = []
    for label, raw in list((counter_map or {}).items()):
        row = raw if isinstance(raw, dict) else {}
        ranked.append(
            {
                "label": str(label),
                "count": int(row.get("count") or 0),
                "last_seen": row.get("last_seen"),
            }
        )
    ranked.sort(key=lambda item: item["count"], reverse=True)
    return ranked[:limit]


def _build_dashboard_insights(profile_data: dict | None) -> dict:
    profile = dict(profile_data or {})
    summaries = list(profile.get("session_summaries") or [])
    latest_summary = summaries[-1] if summaries else {}
    stats = dict(profile.get("stats") or {})
    triggers = _top_items(dict(profile.get("trigger_tags") or {}), limit=3)
    coping_history = list(profile.get("coping_history") or [])
    coping_ranked = sorted(
        [
            {
                "action": str(item.get("action") or ""),
                "tried_count": int(item.get("tried_count") or 0),
                "self_reported_effective": int(item.get("self_reported_effective") or 0),
            }
            for item in coping_history
            if str(item.get("action") or "").strip()
        ],
        key=lambda row: (row["self_reported_effective"], row["tried_count"]),
        reverse=True,
    )[:3]
    return {
        "latest_session_summary": str(latest_summary.get("summary") or "").strip() or None,
        "dominant_emotion": latest_summary.get("dominant_emotion"),
        "top_triggers": triggers,
        "effective_coping": coping_ranked,
        "active_goals": [
            str((goal or {}).get("text") or "").strip()
            for goal in list(profile.get("goals") or [])
            if str((goal or {}).get("status") or "active").strip().lower() == "active"
        ][:3],
        "memory_stats": {
            "total_sessions_summarized": len(summaries),
            "days_active_last_30": int(stats.get("days_active_last_30") or 0),
            "streak_days": int(stats.get("streak_days") or 0),
        },
    }


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
    mood_today_row = db.scalars(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == current_user.user_id, MoodCheckin.logged_date == today)
        .order_by(MoodCheckin.logged_at.desc())
    ).first()

    last_session_at = db.scalar(
        select(func.max(Conversation.last_message_at)).where(
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )

    clin = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == current_user.user_id))
    user_profile = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    assessment = None
    if clin:
        assessment = {
            "phq9_score": clin.phq9_score,
            "gad7_score": clin.gad7_score,
            "crisis_level": clin.crisis_level,
            "last_scored_at": clin.last_scored_at.isoformat() if clin.last_scored_at else None,
            "profile_updated_at": clin.updated_at.isoformat() if clin.updated_at else None,
        }

    refreshed_at = get_now().isoformat()

    payload: dict = {
        "user_id": current_user.user_id,
        "timezone": "Asia/Ho_Chi_Minh",
        "refreshed_at": refreshed_at,
        "session_count": sessions_total,
        "last_session_at": last_session_at.isoformat() if last_session_at else None,
        "mood_today": {
            "checked_in": mood_today_row is not None,
            "mood": mood_today_row.mood if mood_today_row else None,
        },
        "assessment": assessment,
        "analyst_insights": _build_dashboard_insights(user_profile.profile if user_profile else {}),
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
        by_day_win: dict = defaultdict(list)
        for r in mood_rows:
            by_day_win[r.logged_date].append(_mood_score(r.mood)[0])
        daily_avgs = [sum(v) / len(v) for v in by_day_win.values()]
        avg_mood = round(sum(daily_avgs) / len(daily_avgs), 2) if daily_avgs else None
        payload["window"] = {
            "kind": window.value,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sessions_with_activity": sessions_in_window,
            "mood_checkin_days": len(by_day_win),
            "avg_mood_score": avg_mood,
        }

    return ok(payload)


_DAILY_NUTRITION_TIPS = [
    {
        "day_index": 0,
        "dish": "Yến mạch + chuối + hạt óc chó",
        "benefit": "Carb chậm và omega-3 giúp ổn định năng lượng, giảm dao động cảm xúc đầu tuần.",
    },
    {
        "day_index": 1,
        "dish": "Cơm gạo lứt, cá hồi áp chảo, rau xanh",
        "benefit": "Đạm chất lượng và folate hỗ trợ tổng hợp serotonin, giúp đầu óc tập trung hơn.",
    },
    {
        "day_index": 2,
        "dish": "Bún ức gà, rau củ luộc, 1 quả cam",
        "benefit": "Protein nạc + vitamin C giúp giảm mệt mỏi tinh thần khi áp lực giữa tuần tăng cao.",
    },
    {
        "day_index": 3,
        "dish": "Đậu hũ sốt nấm, khoai lang, salad",
        "benefit": "Chất xơ và magnesium hỗ trợ giấc ngủ tối, giảm cảm giác bồn chồn kéo dài.",
    },
    {
        "day_index": 4,
        "dish": "Phở bò nạc + rau thơm + sữa chua",
        "benefit": "Bổ sung sắt và lợi khuẩn đường ruột để tinh thần bền hơn sau tuần làm việc dài.",
    },
    {
        "day_index": 5,
        "dish": "Bánh mì nguyên cám, trứng, bơ, cà chua",
        "benefit": "Bữa gọn nhẹ nhưng đủ dưỡng chất, giúp cơ thể phục hồi và giảm cáu gắt cuối tuần.",
    },
    {
        "day_index": 6,
        "dish": "Canh bí đỏ, cá thu, rau luộc, trái cây ít ngọt",
        "benefit": "Giữ đường huyết ổn định và chuẩn bị giấc ngủ tốt để bước vào tuần mới nhẹ hơn.",
    },
]


@router.get("/nutrition-daily")
def nutrition_daily(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    _ = db, current_user
    today_index = local_date_utc7().weekday()
    tip = next((item for item in _DAILY_NUTRITION_TIPS if item["day_index"] == today_index), _DAILY_NUTRITION_TIPS[0])
    return ok(
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "day_index": today_index,
            "dish": tip["dish"],
            "benefit": tip["benefit"],
            "tip": "Uống đủ nước và ăn đúng giờ để giữ nhịp cảm xúc ổn định.",
        }
    )


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
    by_day: dict = defaultdict(list)
    for row in rows:
        by_day[row.logged_date].append(row)
    points = []
    missing = []
    for idx in range(span):
        day = start + timedelta(days=idx)
        day_rows = by_day.get(day)
        if not day_rows:
            missing.append(day.isoformat())
            continue
        scores = [_mood_score(r.mood)[0] for r in day_rows]
        avg_score = round(sum(scores) / len(scores), 2)
        latest = max(day_rows, key=lambda r: r.logged_at or r.logged_date)
        _, label = _mood_score(latest.mood)
        points.append(
            {
                "date": day.isoformat(),
                "mood_score": avg_score,
                "label": label,
                "emoji": latest.emoji,
                "checkin_count": len(day_rows),
            }
        )

    return ok(
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "refreshed_at": get_now().isoformat(),
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
            "refreshed_at": get_now().isoformat(),
            "window": window.value if window else None,
            "sessions": [
                {
                    "session_id": r.session_id,
                    "last_message_at": r.last_message_at.isoformat(),
                    "message_count": r.message_count,
                }
                for r in rows
            ],
        }
    )


@router.get("/reflect-summary")
def reflect_summary_dashboard(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    summary = build_reflect_summary(db, user_id=current_user.user_id)
    return ok(summary.model_dump(mode="json"))


@router.get("/checkin-history")
def dashboard_checkin_history(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
    range_: str = Query("30d", alias="range", description="all | 30d | 90d"),
):
    if range_ not in {"30d", "90d", "all"}:
        range_ = "30d"
    days = None if range_ == "all" else (90 if range_ == "90d" else 30)
    rows = db.scalars(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == current_user.user_id)
        .order_by(MoodCheckin.logged_date.asc(), MoodCheckin.logged_at.asc())
    ).all()
    history = build_checkin_history(list(rows), days=days)
    return ok(
        {
            "timezone": "Asia/Ho_Chi_Minh",
            "range": range_,
            "history": [h.model_dump(mode="json") for h in history],
        }
    )


@router.get("/safe-insights")
def dashboard_safe_insights(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    return ok(build_safe_insights_payload(db, user_id=current_user.user_id))


@router.get("/follow-up")
def follow_up(current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    _ = db
    return ok({"items": [], "user_id": current_user.user_id})
