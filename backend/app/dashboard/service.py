from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

import logging

from app.dashboard.sufficiency import compute_data_sufficiency
from app.safety.dashboard_guardrail import insight_display_allowed

_log = logging.getLogger(__name__)
from app.dashboard.types import (
    CheckinHistoryDay,
    CheckinHistoryItem,
    DashboardDataSufficiency,
    DashboardInsightCard,
    DashboardProgressSnapshot,
    DashboardReadinessLevel,
    DashboardReflectSummary,
    MoodSeriesPoint,
    WellnessDimensionCard,
)
from app.services.db.models import Conversation, InsightHypothesis, MoodCheckin, UserProfile, StreakState
from app.services.utils import VN_TZ, local_date_utc7, get_now

_MOOD_TO_SCORE: dict[str, tuple[int, str]] = {
    "stressful": (1, "khó khăn"),
    "sad": (2, "buồn"),
    "neutral": (3, "ổn"),
    "peaceful": (4, "tốt"),
    "delightful": (5, "rất tốt"),
}

_DIM_LABELS_VI = {
    "emotion": "Cảm xúc",
    "sleep": "Giấc ngủ",
    "mindfulness": "Tỉnh thức",
    "connection": "Kết nối",
    "body": "Thể chất",
    "growth": "Phát triển",
}

_HYPOTHESIS_SOURCE_VI: dict[str, str] = {
    "stress_pattern": "Check-in & phiên trò chuyện",
    "sleep_disruption": "Check-in trong ngày",
    "social_withdrawal": "Phiên trò chuyện",
    "low_mood_trend": "Check-in cảm xúc",
    "anxiety_like_worry_loop": "Phiên trò chuyện",
    "coping_success": "Hoạt động chăm sóc bản thân",
    "engagement_pattern": "Hoạt động trong app",
    "other": "Dữ liệu gần đây",
}
_MAX_FRONTEND_INSIGHT_CARDS = 2


def _mood_score_label(mood: str | None) -> tuple[int, str]:
    if not mood:
        return 3, "ổn"
    return _MOOD_TO_SCORE.get(mood, (3, "ổn"))


def _normalize_bucket(raw: str | None) -> Literal["morning", "afternoon", "evening", "other"]:
    if raw in ("morning", "afternoon", "evening", "other"):
        return raw  # type: ignore[return-value]
    return "other"


def _parse_note_blob(note: str | None) -> tuple[str | None, dict[str, Any]]:
    if not note:
        return None, {}
    try:
        blob = json.loads(note)
        if isinstance(blob, dict):
            user_note = blob.get("note")
            extra = blob.get("extra") if isinstance(blob.get("extra"), dict) else {}
            return (str(user_note).strip() if user_note else None), extra
    except Exception:
        pass
    return note.strip() or None, {}


def _string_list(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    return []


def _confidence_for_cards(
    readiness: DashboardReadinessLevel, *, checkins: int, sessions: int
) -> Literal["low", "medium", "high"]:
    if readiness == "stable_pattern":
        return "high"
    if checkins < 5 or sessions < 3:
        return "low"
    if 5 <= checkins < 14 or 3 <= sessions < 8:
        return "medium"
    return "low"


def _map_db_severity(raw: str | None) -> Literal["neutral", "watch"]:
    if not raw:
        return "neutral"
    low = raw.strip().lower()
    if low in ("low", "neutral", "informational"):
        return "neutral"
    if low in ("moderate", "medium", "watch", "elevated", "high"):
        return "watch"
    return "neutral"


def _map_float_confidence(val: float | None, fallback: Literal["low", "medium", "high"]) -> Literal["low", "medium", "high"]:
    if val is None:
        return fallback
    try:
        x = float(val)
    except (TypeError, ValueError):
        return fallback
    if x < 0.35:
        return "low"
    if x < 0.65:
        return "medium"
    return "high"


def _cap_confidence(
    value: Literal["low", "medium", "high"],
    cap: Literal["low", "medium", "high"],
) -> Literal["low", "medium", "high"]:
    rank = {"low": 0, "medium": 1, "high": 2}
    if rank[value] <= rank[cap]:
        return value
    return cap


def _dt_to_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=VN_TZ)
        return val.astimezone(VN_TZ).date()
    if isinstance(val, date):
        return val
    return None


def _fetch_hypothesis_insights(
    db: Session,
    user_id: str,
    *,
    fallback_confidence: Literal["low", "medium", "high"],
) -> list[DashboardInsightCard]:
    try:
        stmt = (
            select(
                InsightHypothesis.insight_id,
                InsightHypothesis.title,
                InsightHypothesis.user_safe_summary,
                InsightHypothesis.evidence_count,
                InsightHypothesis.confidence,
                InsightHypothesis.severity_band,
                InsightHypothesis.evidence_window_start,
                InsightHypothesis.evidence_window_end,
                InsightHypothesis.updated_at,
                InsightHypothesis.hypothesis_type,
            )
            .where(
                InsightHypothesis.user_id == user_id,
                InsightHypothesis.status == "active",
                InsightHypothesis.display_allowed.is_(True),
                InsightHypothesis.evidence_count > 0,
            )
            .order_by(InsightHypothesis.updated_at.desc())
            .limit(12)
        )
        rows = db.execute(stmt).mappings().all()
    except Exception:
        return []

    out: list[DashboardInsightCard] = []
    for row in rows:
        hid = str(row.get("insight_id") or "")
        ht = str(row.get("hypothesis_type") or "other")
        src = _HYPOTHESIS_SOURCE_VI.get(ht, _HYPOTHESIS_SOURCE_VI["other"])
        ev_start = _dt_to_date(row.get("evidence_window_start"))
        ev_end = _dt_to_date(row.get("evidence_window_end"))
        upd = row.get("updated_at")
        if isinstance(upd, datetime):
            updated_at = upd if upd.tzinfo else upd.replace(tzinfo=VN_TZ)
        else:
            updated_at = get_now()
        conf = _cap_confidence(_map_float_confidence(row.get("confidence"), fallback_confidence), fallback_confidence)
        suggested = None
        if "sleep" in ht:
            suggested = "Thử cố định một giờ nghỉ ngắn trước khi ngủ, không cần hoàn hảo."
        elif "stress" in ht or "anxiety" in ht:
            suggested = "Chọn một việc nhỏ trong 10 phút thay vì gánh hết cùng lúc."
        elif "social" in ht:
            suggested = "Nếu được, nhắn một dòng ngắn cho người bạn tin tưởng — chỉ để kết nối nhẹ."
        else:
            suggested = "Hôm nay có thể check-in thêm một lần vào buổi tối để Serene hiểu nhịp mood rõ hơn."

        summary_text = str(row.get("user_safe_summary") or "").strip()
        raw_conf = row.get("confidence")
        allowed, block_reason = insight_display_allowed(
            user_safe_summary=summary_text,
            confidence=raw_conf,
        )
        if not allowed:
            _log.warning("dashboard guardrail blocked insight %s: %s", hid, block_reason)
            continue

        out.append(
            DashboardInsightCard(
                insight_id=hid,
                title=str(row.get("title") or "Tín hiệu gần đây"),
                user_safe_summary=summary_text,
                evidence_count=int(row.get("evidence_count") or 0),
                evidence_sources=[src],
                confidence=conf,
                severity_band=_map_db_severity(row.get("severity_band")),
                suggested_action=suggested,
                evidence_window_start=ev_start,
                evidence_window_end=ev_end,
                updated_at=updated_at,
            )
        )
    return out


def _profile_insights(
    profile_data: dict[str, Any],
    *,
    readiness: DashboardReadinessLevel,
    checkins: int,
    sessions: int,
) -> list[DashboardInsightCard]:
    cards: list[DashboardInsightCard] = []
    conf = _confidence_for_cards(readiness, checkins=checkins, sessions=sessions)
    now = get_now()

    triggers = dict(profile_data.get("trigger_tags") or {})
    ranked_t = sorted(
        [{"tag": k, **(v if isinstance(v, dict) else {})} for k, v in triggers.items()],
        key=lambda x: int(x.get("count") or 0),
        reverse=True,
    )
    if ranked_t:
        top = ranked_t[0]
        tag = str(top.get("tag") or "").replace("_", " ")
        cnt = int(top.get("count") or 0)
        if tag and cnt > 0:
            cards.append(
                DashboardInsightCard(
                    insight_id=f"heuristic_trigger_{uuid.uuid4().hex[:10]}",
                    title="Một tín hiệu lặp lại trong check-in",
                    user_safe_summary=(
                        f"Dữ liệu gần đây cho thấy bạn hay nhắc đến “{tag}” trong các check-in "
                        f"({cnt} lần ghi nhận). Serene chỉ coi đây là tín hiệu ban đầu."
                    ),
                    evidence_count=cnt,
                    evidence_sources=["Check-in cảm xúc"],
                    confidence=conf,
                    severity_band="watch",
                    suggested_action=(
                        "Thử viết một câu ngắn: “Điều làm mình nặng nhất lúc này là…” rồi check-in lại tối nay."
                    ),
                    evidence_window_start=None,
                    evidence_window_end=None,
                    updated_at=now,
                )
            )

    summaries = list(profile_data.get("session_summaries") or [])[-5:]
    emotions: dict[str, int] = {}
    for s in summaries:
        if not isinstance(s, dict):
            continue
        em = str(s.get("dominant_emotion") or "").strip()
        if em:
            emotions[em] = emotions.get(em, 0) + 1
    if emotions and sessions >= 1:
        dom = max(emotions, key=lambda k: emotions[k])
        n = emotions[dom]
        cards.append(
            DashboardInsightCard(
                insight_id=f"heuristic_emotion_{uuid.uuid4().hex[:10]}",
                title="Tone cảm xúc trong các phiên gần đây",
                user_safe_summary=(
                    f"Trong vài phiên trò chuyện gần đây, Serene thấy bạn thường có không khí “{dom}”. "
                    "Đây chỉ là quan sát nhẹ, không phải kết luận."
                ),
                evidence_count=n,
                evidence_sources=["Phiên trò chuyện"],
                confidence=conf,
                severity_band="neutral",
                suggested_action="Nếu muốn, hãy nói thêm một chút về điều đang chiếm nhiều tâm trí bạn nhất.",
                evidence_window_start=None,
                evidence_window_end=None,
                updated_at=now,
            )
        )

    coping = list(profile_data.get("coping_history") or [])
    breathing_like = [
        c
        for c in coping
        if isinstance(c, dict)
        and "thở" in str(c.get("action") or "").lower()
        and int(c.get("self_reported_effective") or 0) > 0
    ]
    if breathing_like:
        cards.append(
            DashboardInsightCard(
                insight_id=f"heuristic_coping_{uuid.uuid4().hex[:10]}",
                title="Điều có vẻ giúp bạn dễ chịu hơn",
                user_safe_summary=(
                    "Serene nhận thấy bạn có vài lần phản hồi tích cực với hoạt động liên quan đến thở nhẹ. "
                    "Có thể các bước nhỏ, cụ thể hợp với bạn hơn là gợi ý dài."
                ),
                evidence_count=len(breathing_like),
                evidence_sources=["Hoạt động trong app"],
                confidence=conf,
                severity_band="neutral",
                suggested_action="Thử một vòng thở ngắn 2 phút khi thấy đầu óc căng.",
                evidence_window_start=None,
                evidence_window_end=None,
                updated_at=now,
            )
        )

    return cards


def build_safe_insight_cards(
    db: Session,
    *,
    user_id: str,
    sufficiency: DashboardDataSufficiency,
) -> list[DashboardInsightCard]:
    fallback_confidence = _confidence_for_cards(
        sufficiency.readiness_level,
        checkins=sufficiency.mood_checkin_count,
        sessions=sufficiency.total_session_count,
    )
    return _fetch_hypothesis_insights(db, user_id, fallback_confidence=fallback_confidence)[:_MAX_FRONTEND_INSIGHT_CARDS]


def build_checkin_history(
    rows: list[MoodCheckin],
    *,
    days: int | None,
    today: date | None = None,
) -> list[CheckinHistoryDay]:
    today_d = today or local_date_utc7()
    lower: date | None
    if days is None:
        lower = None
    else:
        lower = today_d - timedelta(days=max(1, days) - 1)

    by_date: dict[date, list[MoodCheckin]] = {}
    for r in rows:
        if lower is not None and r.logged_date < lower:
            continue
        by_date.setdefault(r.logged_date, []).append(r)

    for day_rows in by_date.values():
        day_rows.sort(key=lambda x: (x.logged_at or datetime.min))

    sorted_dates = sorted(by_date.keys(), reverse=True)
    out: list[CheckinHistoryDay] = []
    for d in sorted_dates:
        day_rows = by_date[d]
        items: list[CheckinHistoryItem] = []
        for r in day_rows:
            user_note, extra = _parse_note_blob(r.note)
            score_int, label = _mood_score_label(r.mood)
            items.append(
                CheckinHistoryItem(
                    checkin_id=r.checkin_id,
                    logged_at=(
                        la.replace(tzinfo=VN_TZ)
                        if (la := r.logged_at) and la.tzinfo is None
                        else (la or get_now())
                    ),
                    date=r.logged_date,
                    time_bucket=_normalize_bucket(getattr(r, "time_bucket", None)),
                    mood_label=label,
                    mood_score=score_int,
                    emotions=_string_list(r.emotions),
                    triggers=_string_list(r.triggers),
                    note=user_note,
                    reward_granted=None,
                )
            )
        out.append(CheckinHistoryDay(date=d, completed=True, checkins=items, streak_day_index=None))
    return out


def _build_mood_series(checkin_rows: list[MoodCheckin], days: int = 14) -> list[dict[str, Any]]:
    today = local_date_utc7()
    start = today - timedelta(days=days - 1)
    by_day: dict[date, list[MoodCheckin]] = {}
    for r in checkin_rows:
        if r.logged_date < start or r.logged_date > today:
            continue
        by_day.setdefault(r.logged_date, []).append(r)

    points: list[MoodSeriesPoint] = []
    for d in sorted(by_day.keys()):
        rs = by_day[d]
        scores = [_mood_score_label(x.mood)[0] for x in rs]
        avg = sum(scores) / len(scores)
        pct = int(round((avg / 5.0) * 100))
        _, lbl = _mood_score_label(rs[-1].mood)
        points.append(
            MoodSeriesPoint(
                date=d,
                mood_score=round(avg, 2),
                mood_score_pct=max(0, min(100, pct)),
                label=lbl,
                checkin_count=len(rs),
            )
        )
    return [p.model_dump(mode="json") for p in points]


def build_mood_series(checkins: list[MoodCheckin], *, days: int = 14) -> list[dict[str, Any]]:
    return _build_mood_series(checkins, days=days)


def _avg_sleep_hours(rows: list[MoodCheckin]) -> tuple[float | None, int]:
    vals: list[float] = []
    for r in rows:
        _, extra = _parse_note_blob(r.note)
        raw = extra.get("sleep_hours")
        try:
            if raw is not None:
                vals.append(float(raw))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def _effective_coping_stats(coping_history: list[Any]) -> tuple[int, int]:
    tried = 0
    effective = 0
    for item in coping_history:
        if not isinstance(item, dict):
            continue
        t = int(item.get("tried_count") or 0)
        if t <= 0:
            continue
        tried += t
        effective += int(item.get("self_reported_effective") or 0)
    return tried, effective


def _build_wellness_dimensions(
    profile_data: dict[str, Any],
    *,
    checkins: list[MoodCheckin],
    session_count: int,
    sufficiency: DashboardDataSufficiency,
    streak_days: int,
) -> list[WellnessDimensionCard]:
    stats = dict(profile_data.get("stats") or {})
    coping_history = list(profile_data.get("coping_history") or [])
    today = local_date_utc7()
    recent = [r for r in checkins if r.logged_date >= today - timedelta(days=7)]

    cards: list[WellnessDimensionCard] = []

    # Emotion
    if recent:
        scores = [_mood_score_label(r.mood)[0] for r in recent]
        avg = sum(scores) / len(scores)
        score = int(round((avg / 5.0) * 100))
        if avg >= 3.5:
            st: Literal["steady", "needs_attention", "limited_data", "unknown", "improving"] = "steady"
        elif avg >= 3:
            st = "steady"
        else:
            st = "needs_attention"
        cards.append(
            WellnessDimensionCard(
                dimension="emotion",
                label=_DIM_LABELS_VI["emotion"],
                status=st,
                score=score,
                explanation=(
                    f"Dựa trên {len(recent)} check-in trong 7 ngày gần nhất. "
                    "Serene chỉ nhìn nhịp mood tổng thể, không kết luận về sức khỏe tâm thần."
                ),
                evidence_count=len(recent),
                suggested_action="Một check-in mỗi ngày là đủ để giữ chuỗi; có thể thêm buổi tối để thấy nhịp trong ngày.",
            )
        )
    else:
        cards.append(
            WellnessDimensionCard(
                dimension="emotion",
                label=_DIM_LABELS_VI["emotion"],
                status="limited_data",
                score=None,
                explanation="Dữ liệu check-in còn ít trong tuần qua — Serene chưa vội nhận xét xu hướng.",
                evidence_count=0,
                suggested_action="Check-in thêm một lần khi bạn thấy phù hợp.",
            )
        )

    # Sleep
    avg_sleep, n_sleep = _avg_sleep_hours(recent)
    if avg_sleep is not None and n_sleep > 0:
        if avg_sleep >= 7:
            st2 = "steady"
            score_s = min(100, int(60 + (avg_sleep - 7) * 10))
        elif avg_sleep >= 6:
            st2 = "needs_attention"
            score_s = int(45 + (avg_sleep - 6) * 15)
        else:
            st2 = "needs_attention"
            score_s = max(10, int(avg_sleep * 8))
        cards.append(
            WellnessDimensionCard(
                dimension="sleep",
                label=_DIM_LABELS_VI["sleep"],
                status=st2,
                score=max(0, min(100, score_s)),
                explanation=(
                    f"Dựa trên {n_sleep} lần bạn ghi nhận giấc ngủ trong check-in gần đây "
                    f"(trung bình khoảng {avg_sleep:.1f} giờ). Đây chỉ là ghi nhận tự báo cáo."
                ),
                evidence_count=n_sleep,
                suggested_action="Thử cố định một thói quen nghỉ nhẹ 30 phút trước khi ngủ.",
            )
        )
    else:
        cards.append(
            WellnessDimensionCard(
                dimension="sleep",
                label=_DIM_LABELS_VI["sleep"],
                status="limited_data",
                score=None,
                explanation="Serene chưa có đủ ghi nhận ngủ trong check-in để nói thêm.",
                evidence_count=0,
                suggested_action="Nếu muốn, ghi thêm số giờ ngủ trong check-in để Serene hiểu nhịp của bạn.",
            )
        )

    breath_sessions = int(stats.get("breathing_sessions") or 0)
    breath_from_coping = sum(
        1
        for c in coping_history
        if isinstance(c, dict) and "thở" in str(c.get("action") or "").lower() and int(c.get("tried_count") or 0) > 0
    )
    breath_ev = max(breath_sessions, breath_from_coping)
    if breath_ev > 0:
        score_m = min(100, 35 + breath_ev * 8)
        cards.append(
            WellnessDimensionCard(
                dimension="mindfulness",
                label=_DIM_LABELS_VI["mindfulness"],
                status="improving" if breath_ev >= 3 else "steady",
                score=score_m,
                explanation=f"Bạn có khoảng {breath_ev} ghi nhận liên quan đến thở nhẹ / tỉnh thức trong dữ liệu gần đây.",
                evidence_count=breath_ev,
                suggested_action="Một vòng thở ngắn 2 phút cũng là đủ cho hôm nay.",
            )
        )
    else:
        cards.append(
            WellnessDimensionCard(
                dimension="mindfulness",
                label=_DIM_LABELS_VI["mindfulness"],
                status="limited_data",
                score=None,
                explanation="Chưa có nhiều dấu hiệu về thói quen thở/tỉnh thức trong dữ liệu hiện tại.",
                evidence_count=0,
                suggested_action="Thử một bài thở ngắn trong mục Bài tập khi bạn muốn.",
            )
        )

    # Connection (sessions as gentle engagement proxy — non-clinical)
    if session_count <= 0:
        cards.append(
            WellnessDimensionCard(
                dimension="connection",
                label=_DIM_LABELS_VI["connection"],
                status="limited_data",
                score=None,
                explanation="Serene chưa có đủ phiên trò chuyện để nhận ra nhịp kết nối ấm trong app.",
                evidence_count=0,
                suggested_action="Một phiên ngắn cũng có giá trị — không cần phải “tâm sự dài”.",
            )
        )
    elif session_count < 5:
        cards.append(
            WellnessDimensionCard(
                dimension="connection",
                label=_DIM_LABELS_VI["connection"],
                status="improving",
                score=min(100, 25 + session_count * 14),
                explanation=f"Bạn đã có {session_count} phiên trò chuyện được ghi nhận — đây là dấu hiệu bạn đang chủ động kết nối.",
                evidence_count=session_count,
                suggested_action="Nếu muốn, hãy chia sẻ một điều nhỏ nhưng cụ thể về ngày của bạn.",
            )
        )
    else:
        cards.append(
            WellnessDimensionCard(
                dimension="connection",
                label=_DIM_LABELS_VI["connection"],
                status="steady",
                score=min(100, 40 + session_count * 6),
                explanation=f"Bạn duy trì khoảng {session_count} phiên trò chuyện — Serene thấy nhịp kết nối khá đều.",
                evidence_count=session_count,
                suggested_action="Giữ nhịp nhẹ: không cần nói nhiều, chỉ cần đều đặn.",
            )
        )

    tried, effective = _effective_coping_stats(coping_history)
    if tried <= 0:
        cards.append(
            WellnessDimensionCard(
                dimension="body",
                label=_DIM_LABELS_VI["body"],
                status="limited_data",
                score=None,
                explanation="Chưa có đủ ghi nhận coping trong app để Serene nói về ‘phản hồi thể chất/năng lượng’ một cách cụ thể.",
                evidence_count=0,
                suggested_action="Khi thử một việc nhỏ giúp đỡ đỡ hơn, bạn có thể đánh dấu trong check-in.",
            )
        )
    else:
        rate = effective / tried if tried else 0.0
        score_b = int(round(max(0.0, min(1.0, rate)) * 100))
        body_status: Literal["steady", "improving"] = "steady" if rate >= 0.55 else "improving"
        cards.append(
            WellnessDimensionCard(
                dimension="body",
                label=_DIM_LABELS_VI["body"],
                status=body_status,
                score=score_b,
                explanation=(
                    f"Dựa trên {tried} lần bạn thử coping được ghi nhận. "
                    "Serene chỉ xem đây là phản hồi chủ quan của bạn."
                ),
                evidence_count=tried,
                suggested_action="Chọn một hành động nhỏ, làm xong là thắng.",
            )
        )

    growth_evidence = streak_days + min(session_count, 10)
    if streak_days <= 0:
        cards.append(
            WellnessDimensionCard(
                dimension="growth",
                label=_DIM_LABELS_VI["growth"],
                status="limited_data",
                score=None,
                explanation="Mình mới chỉ có vài dấu hiệu về thói quen của bạn — chưa đủ để nói về ‘tiến triển’.",
                evidence_count=0,
                suggested_action="Một check-in hoặc một phiên ngắn hôm nay là đủ để mở đầu nhẹ.",
            )
        )
    elif 1 <= streak_days <= 6:
        cards.append(
            WellnessDimensionCard(
                dimension="growth",
                label=_DIM_LABELS_VI["growth"],
                status="improving",
                score=min(100, 20 + streak_days * 8 + session_count * 3),
                explanation=(
                    f"Dựa trên chuỗi khoảng {streak_days} ngày và {session_count} phiên — "
                    "Serene thấy bạn đang xây nhịp nhẹ."
                ),
                evidence_count=growth_evidence,
                suggested_action="Giữ một việc nhỏ lặp lại 3 ngày — không cần hoàn hảo.",
            )
        )
    else:
        cards.append(
            WellnessDimensionCard(
                dimension="growth",
                label=_DIM_LABELS_VI["growth"],
                status="steady",
                score=min(100, 25 + streak_days * 5 + session_count * 2),
                explanation=(
                    f"Dựa trên chuỗi khoảng {streak_days} ngày và {session_count} phiên — "
                    "có vẻ bạn đang duy trì đều đặn hơn."
                ),
                evidence_count=growth_evidence,
                suggested_action="Chọn một điều nhỏ để khen mình hôm nay — có thể chỉ là đã check-in.",
            )
        )

    return cards


def build_wellness_dimensions(
    profile_data: dict[str, Any],
    *,
    checkins: list[MoodCheckin],
    session_count: int,
    sufficiency: DashboardDataSufficiency,
    streak_days: int = 0,
) -> list[WellnessDimensionCard]:
    return _build_wellness_dimensions(
        profile_data,
        checkins=checkins,
        session_count=session_count,
        sufficiency=sufficiency,
        streak_days=streak_days,
    )


def _progress_snapshot(profile_data: dict[str, Any], *, session_count: int, streak_days: int, is_today_completed: bool, completed_days: list[int]) -> DashboardProgressSnapshot:
    stats = dict(profile_data.get("stats") or {})
    coping_history = list(profile_data.get("coping_history") or [])
    tried, effective = _effective_coping_stats(coping_history)
    rate = (effective / tried) if tried > 0 else None
    return DashboardProgressSnapshot(
        streak_days=streak_days,
        total_sessions=session_count,
        days_active_last_30=int(stats.get("days_active_last_30") or 0),
        breathing_sessions=int(stats.get("breathing_sessions") or 0),
        effective_rate=rate,
        is_today_completed=is_today_completed,
        completed_days=completed_days,
    )


def _radar_available(sufficiency: DashboardDataSufficiency, dimensions: list[WellnessDimensionCard]) -> bool:
    if sufficiency.readiness_level not in ("weekly_trend", "stable_pattern"):
        return False
    scored = sum(1 for d in dimensions if d.score is not None)
    return scored >= 4


def build_reflect_summary(db: Session, *, user_id: str) -> DashboardReflectSummary:
    sufficiency = compute_data_sufficiency(db, user_id=user_id)
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data: dict[str, Any] = dict(profile_row.profile if profile_row and profile_row.profile else {})

    streak_row = db.scalar(select(StreakState).where(StreakState.user_id == user_id))
    streak_days = streak_row.current_mood_checkin_streak if streak_row else 0

    is_today_completed = False
    if streak_row and streak_row.last_mood_checkin_date == local_date_utc7():
        is_today_completed = True

    checkins = db.scalars(
        select(MoodCheckin).where(MoodCheckin.user_id == user_id).order_by(MoodCheckin.logged_date.asc())
    ).all()
    convs = db.scalars(
        select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
    ).all()

    all_cards = build_safe_insight_cards(db, user_id=user_id, sufficiency=sufficiency)
    if sufficiency.readiness_level == "no_data":
        top = []
    elif sufficiency.readiness_level == "first_signals":
        top = all_cards[:1]
    else:
        top = all_cards[:_MAX_FRONTEND_INSIGHT_CARDS]

    dimensions = build_wellness_dimensions(
        profile_data,
        checkins=list(checkins),
        session_count=len(convs),
        sufficiency=sufficiency,
        streak_days=streak_days,
    )
    mood_series = build_mood_series(list(checkins), days=14)
    preview = build_checkin_history(list(checkins), days=7)
    radar = _radar_available(sufficiency, dimensions)
    
    # Calculate completed days of current week (Mon-Sun)
    today = local_date_utc7()
    current_weekday = today.weekday() # 0=Mon ... 6=Sun
    start_of_week = today - timedelta(days=current_weekday)
    end_of_week = start_of_week + timedelta(days=6)
    
    completed_days = []
    week_checkin_dates = {c.logged_date for c in checkins if start_of_week <= c.logged_date <= end_of_week}
    
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        if day_date in week_checkin_dates:
            completed_days.append(i)
            
    progress = _progress_snapshot(profile_data, session_count=len(convs), streak_days=streak_days, is_today_completed=is_today_completed, completed_days=completed_days)

    return DashboardReflectSummary(
        sufficiency=sufficiency,
        top_insights=top,
        wellness_dimensions=dimensions,
        mood_series=mood_series,
        checkin_history_preview=preview,
        radar_available=radar,
        progress=progress,
    )


def build_safe_insights_payload(db: Session, *, user_id: str) -> dict[str, Any]:
    sufficiency = compute_data_sufficiency(db, user_id=user_id)
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data: dict[str, Any] = dict(profile_row.profile if profile_row and profile_row.profile else {})
    cards = build_safe_insight_cards(db, user_id=user_id, sufficiency=sufficiency)
    return {
        "sufficiency": sufficiency.model_dump(mode="json"),
        "insights": [c.model_dump(mode="json") for c in cards],
    }
