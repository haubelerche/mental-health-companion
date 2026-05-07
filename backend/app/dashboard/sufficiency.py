from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dashboard.types import DashboardDataSufficiency, DashboardReadinessLevel
from app.services.db.models import Conversation, MoodCheckin, Message
from app.services.utils import VN_TZ

_MESSAGES_VI: dict[DashboardReadinessLevel, str] = {
    "no_data": "Serene chưa có dữ liệu. Hãy check-in hoặc trò chuyện để bắt đầu.",
    "first_signals": (
        "Serene đã có tín hiệu đầu tiên — đây là trạng thái hiện tại, chưa phải xu hướng."
    ),
    "early_insight": "Đã có đủ dữ liệu ban đầu. Serene chỉ chia sẻ vài tín hiệu nhẹ, chưa vội kết luận.",
    "weekly_trend": "Serene có thể nhận ra xu hướng trong khoảng 7 ngày qua.",
    "stable_pattern": "Dữ liệu khá ổn định hơn — Serene thấy một số xu hướng rõ hơn qua 14+ ngày.",
}


def _vn_date(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(VN_TZ).date()


def _session_duration_minutes(conv: Conversation) -> float:
    if conv.started_at is None or conv.last_message_at is None:
        return 0.0
    return max(0.0, (conv.last_message_at - conv.started_at).total_seconds() / 60.0)


def _is_deep_conv(conv: Conversation, user_turns: int) -> bool:
    if conv.message_count >= 16:
        return True
    if user_turns >= 8:
        return True
    if conv.anonymous_summary:
        return True
    if _session_duration_minutes(conv) >= 10:
        return True
    return False


def _user_turn_counts(db: Session, *, user_id: str) -> dict[str, int]:
    rows = db.execute(
        select(Message.session_id, func.count()).where(
            Message.user_id == user_id,
            Message.role == "user",
        ).group_by(Message.session_id)
    ).all()
    return {str(sid): int(cnt) for sid, cnt in rows}


def _resolve_level(
    *,
    n_sessions: int,
    deep_count: int,
    n_checkins: int,
    checkin_distinct_days: int,
    active_days: int,
    calendar_days: int,
) -> DashboardReadinessLevel:
    if n_sessions == 0 and n_checkins == 0:
        return "no_data"

    early_insight = deep_count >= 3 or (n_checkins >= 5 and checkin_distinct_days >= 3)

    if calendar_days >= 14 and active_days >= 6 and n_sessions >= 5:
        return "stable_pattern"
    if calendar_days >= 7 and active_days >= 4 and n_sessions >= 2:
        return "weekly_trend"
    if early_insight:
        return "early_insight"
    if n_sessions >= 1 or n_checkins >= 1:
        return "first_signals"
    return "no_data"


def _hints(
    level: DashboardReadinessLevel,
    *,
    deep_count: int,
    n_checkins: int,
    checkin_distinct_days: int,
    active_days: int,
    calendar_days: int,
    n_sessions: int,
) -> list[str]:
    out: list[str] = []
    if level == "no_data":
        out.append("Thêm 1 check-in cảm xúc hoặc mở một phiên trò chuyện ngắn với Serene.")
        return out[:3]
    if level == "first_signals":
        if n_checkins < 3:
            out.append("Check-in thêm vài lần vào các ngày khác nhau để Serene thấy nhịp rõ hơn.")
        if n_sessions < 2:
            out.append("Trò chuyện thêm một chút khi bạn sẵn sàng — không cần dài.")
        return out[:3]
    if level == "early_insight":
        if calendar_days < 7:
            out.append("Tiếp tục vài ngày nữa để Serene có thể nói về xu hướng tuần một cách nhẹ nhàng.")
        if active_days < 4:
            out.append("Serene cần thêm vài ngày có hoạt động (check-in hoặc trò chuyện).")
        return out[:3]
    if level == "weekly_trend":
        if calendar_days < 14:
            out.append("Thêm vài ngày nữa để Serene nhận ra xu hướng ổn định hơn.")
        if deep_count < 5:
            out.append("Vài phiên trò chuyện đủ sâu hơn sẽ giúp insight sinh động hơn.")
        return out[:3]
    out.append("Bạn có thể giữ nhịp nhẹ: một check-in mỗi ngày là đủ; thêm buổi trò chuyện khi cần.")
    return out[:3]


def compute_data_sufficiency(db: Session, *, user_id: str) -> DashboardDataSufficiency:
    checkins = db.scalars(select(MoodCheckin).where(MoodCheckin.user_id == user_id)).all()
    convs = db.scalars(
        select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
    ).all()

    turn_map = _user_turn_counts(db, user_id=user_id)
    deep_count = sum(1 for c in convs if _is_deep_conv(c, turn_map.get(c.session_id, 0)))

    checkin_dates = {r.logged_date for r in checkins}
    conv_dates = {_vn_date(c.started_at) for c in convs}
    conv_dates.discard(None)
    all_dates = checkin_dates | set(conv_dates)
    active_days = len(all_dates)
    n_checkins = len(checkins)
    n_sessions = len(convs)
    checkin_distinct_days = len(checkin_dates)

    calendar_days = 0
    evidence_start: date | None = None
    evidence_end: date | None = None
    if all_dates:
        evidence_start = min(all_dates)
        evidence_end = max(all_dates)
        calendar_days = (evidence_end - evidence_start).days + 1

    level = _resolve_level(
        n_sessions=n_sessions,
        deep_count=deep_count,
        n_checkins=n_checkins,
        checkin_distinct_days=checkin_distinct_days,
        active_days=active_days,
        calendar_days=calendar_days,
    )

    return DashboardDataSufficiency(
        readiness_level=level,
        active_days=active_days,
        mood_checkin_count=n_checkins,
        total_session_count=n_sessions,
        deep_session_count=deep_count,
        calendar_days_observed=calendar_days,
        evidence_window_start=evidence_start,
        evidence_window_end=evidence_end,
        message=_MESSAGES_VI[level],
        next_data_needed=_hints(
            level,
            deep_count=deep_count,
            n_checkins=n_checkins,
            checkin_distinct_days=checkin_distinct_days,
            active_days=active_days,
            calendar_days=calendar_days,
            n_sessions=n_sessions,
        ),
    )
