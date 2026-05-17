from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import exists, func, select
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
from app.services.dashboard_insights.insight_builder import (
    build_and_persist_dashboard_insights,
    wellness_dimensions_from_insights,
)
from app.services.db.models import (
    ClinicalProfile,
    Conversation,
    DashboardSafeInsight,
    InsightEvidence,
    InsightHypothesis,
    MoodCheckin,
    NutritionMealCheckin,
    SleepCheckin,
    UserProfile,
    StreakState,
)
from app.services.utils import VN_TZ, local_date_utc7, get_now

_MOOD_TO_SCORE: dict[str, tuple[int, str]] = {
    "terrible": (1, "rất khó"),
    "stressful": (1, "khó khăn"),
    "bad": (1, "khó khăn"),
    "sad": (2, "buồn"),
    "fine": (3, "ổn"),
    "neutral": (3, "ổn"),
    "good": (4, "tốt"),
    "peaceful": (4, "tốt"),
    "awesome": (5, "rất tốt"),
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
_MAX_FRONTEND_INSIGHT_CARDS = 10


def _mood_score_label(mood: str | None) -> tuple[int, str]:
    if not mood:
        return 3, "ổn"
    return _MOOD_TO_SCORE.get(str(mood).strip().lower(), (3, "ổn"))


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


def _first_action(actions: list[str]) -> str | None:
    return actions[0] if actions else None


def _date_window(days: int) -> tuple[date, date]:
    end = local_date_utc7()
    return end - timedelta(days=max(1, days) - 1), end


def _window_dt(days: int) -> tuple[datetime, datetime]:
    start_d, end_d = _date_window(days)
    start = datetime.combine(start_d, datetime.min.time())
    end = datetime.combine(end_d + timedelta(days=1), datetime.min.time())
    return start, end


def _recent_checkins(checkins: list[MoodCheckin], *, days: int = 7) -> list[MoodCheckin]:
    start, end = _date_window(days)
    return [row for row in checkins if start <= row.logged_date <= end]


def _top_counter(labels: list[str], *, limit: int = 3) -> list[tuple[str, int]]:
    counter = Counter(label.strip() for label in labels if label and label.strip())
    return counter.most_common(limit)


def _avg_score(rows: list[MoodCheckin]) -> float | None:
    scores = [_mood_score_label(row.mood)[0] * 2 for row in rows]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _bucket_counts(rows: list[MoodCheckin]) -> dict[str, int]:
    out = {"morning": 0, "afternoon": 0, "evening": 0, "other": 0}
    for row in rows:
        out[_normalize_bucket(getattr(row, "time_bucket", None))] += 1
    return out


def _placeholder_like(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    bad_fragments = (
        "tín hiệu gần đây",
        "tÃ­n hiá»‡u gáº§n",
        "có vài dấu hiệu",
        "cÃ³ vÃ i dáº¥u hiá»‡u",
        "serene ghi nhận một tín hiệu nhẹ",
        "serene ghi nháº­n má»™t tÃ­n hiá»‡u nháº¹",
        "đây chỉ là quan sát nhẹ",
        "Ä‘Ã¢y chá»‰ lÃ  quan sÃ¡t nháº¹",
    )
    return any(fragment in text for fragment in bad_fragments)


def _confidence_from_evidence(count: int) -> Literal["low", "medium", "high"]:
    if count >= 10:
        return "high"
    if count >= 4:
        return "medium"
    return "low"


def _sleep_values(rows: list[MoodCheckin]) -> list[float]:
    vals: list[float] = []
    for row in rows:
        _, extra = _parse_note_blob(row.note)
        raw = extra.get("sleep_hours") or extra.get("duration_hours")
        try:
            if raw is not None:
                hours = float(raw)
                if 0 < hours <= 16:
                    vals.append(hours)
        except (TypeError, ValueError):
            continue
    return vals


def _sleep_checkin_values(rows: list[SleepCheckin]) -> list[float]:
    vals: list[float] = []
    for row in rows:
        try:
            hours = float(row.duration_hours) if row.duration_hours is not None else None
        except (TypeError, ValueError):
            hours = None
        if hours is None and row.bedtime_at and row.wake_time_at:
            delta = row.wake_time_at - row.bedtime_at
            hours = round(delta.total_seconds() / 3600, 2)
        if hours is not None and 0 < hours <= 16:
            vals.append(hours)
    return vals


def _nutrition_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    if any(k in lowered for k in ("thịt", "cá", "trứng", "gà", "bò", "đậu", "tofu", "sữa", "yogurt", "protein")):
        tags.append("có đạm")
    if any(k in lowered for k in ("rau", "salad", "quả", "trái cây", "chuối", "cam", "táo", "yến mạch", "gạo lứt", "khoai")):
        tags.append("có chất xơ")
    if any(k in lowered for k in ("rau", "salad", "cải", "bông cải", "dưa leo", "cà chua")):
        tags.append("có rau")
    if any(k in lowered for k in ("trà sữa", "nước ngọt", "bánh ngọt", "kẹo", "đường", "soda")):
        tags.append("nhiều đường")
    if any(k in lowered for k in ("cà phê", "coffee", "trà đặc", "caffeine", "matcha")):
        tags.append("có caffeine")
    if any(k in lowered for k in ("chiên", "rán", "khoai tây chiên", "gà rán", "đồ chiên")):
        tags.append("đồ chiên/nặng bụng")
    return tags or ["cần mô tả rõ hơn"]


def _screening_band(instrument: str, score: int) -> str:
    if instrument == "phq9":
        if score >= 20:
            return "rất cao"
        if score >= 15:
            return "cao"
        if score >= 10:
            return "trung bình"
        if score >= 5:
            return "nhẹ"
        return "thấp"
    if instrument == "gad7":
        if score >= 15:
            return "cao"
        if score >= 10:
            return "trung bình"
        if score >= 5:
            return "nhẹ"
        return "thấp"
    if instrument == "pcl5":
        return "cần theo dõi" if score >= 31 else "thấp"
    if instrument == "mdq":
        return "cần theo dõi" if score >= 7 else "thấp"
    return "cần theo dõi" if score >= 10 else "thấp"


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
                InsightHypothesis.run_id.isnot(None),
                exists(
                    select(InsightEvidence.evidence_id).where(
                        InsightEvidence.insight_id == InsightHypothesis.insight_id,
                        InsightEvidence.display_allowed.is_(True),
                    )
                ),
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
        title_text = str(row.get("title") or "Nhận định từ dữ liệu gần đây").strip()
        if _placeholder_like(title_text, summary_text):
            continue
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
                category="safe_dashboard_insight",
                title=title_text,
                user_safe_summary=summary_text,
                interpretation=summary_text,
                evidence_count=int(row.get("evidence_count") or 0),
                evidence_sources=[src],
                confidence=conf,
                severity_band=_map_db_severity(row.get("severity_band")),
                suggested_action=suggested,
                recommended_actions=[suggested] if suggested else [],
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
                        f"({cnt} lần ghi nhận). Serene xem đây là dữ liệu tham khảo để gợi ý bước nhỏ tiếp theo."
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
                category="self_care_action",
                title="Điều có vẻ giúp bạn dễ chịu hơn",
                user_safe_summary=(
                    "Serene nhận thấy bạn có vài lần phản hồi tích cực với hoạt động liên quan đến thở nhẹ. "
                    "Có thể các bước nhỏ, cụ thể hợp với bạn hơn là gợi ý dài."
                ),
                interpretation="Chá»‰ xem Ä‘Ã¢y lÃ  hÃ nh Ä‘á»™ng tá»± chÄƒm sÃ³c há»¯u Ã­ch khi cÃ³ láº·p láº¡i hoáº·c pháº£n há»“i hiá»‡u quáº£ tá»« báº¡n.",
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


def _mood_life_state_card(checkins: list[MoodCheckin], *, days: int = 7) -> DashboardInsightCard | None:
    recent = _recent_checkins(checkins, days=days)
    if not recent:
        return None
    now = get_now()
    avg = _avg_score(recent)
    bucket_counts = _bucket_counts(recent)
    triggers = _top_counter([t for row in recent for t in _string_list(row.triggers)], limit=2)
    emotions = _top_counter([e for row in recent for e in _string_list(row.emotions)], limit=2)
    missing: list[str] = []
    if bucket_counts["evening"] == 0:
        missing.append("Thiếu check-in buổi tối để so sánh mood cuối ngày.")
    if not triggers:
        missing.append("Thiếu trigger để biết yếu tố nào ảnh hưởng mạnh nhất.")

    top_trigger = triggers[0][0] if triggers else None
    top_emotion = emotions[0][0] if emotions else None
    low_days = sum(1 for row in recent if _mood_score_label(row.mood)[0] <= 2)
    if avg is None:
        state = "chưa rõ"
    elif avg < 5:
        state = "có vẻ đang chịu nhiều sóng gió"
    elif low_days >= 2 or (top_trigger and triggers[0][1] >= 2):
        state = "dao động và có áp lực lặp lại"
    elif avg >= 7:
        state = "khá yên bình"
    else:
        state = "tương đối ổn nhưng vẫn cần quan sát"

    summary = f"Trong {days} ngày gần đây, mood trung bình khoảng {avg}/10 từ {len(recent)} check-in."
    if top_trigger and top_emotion:
        summary += f" Yếu tố nổi bật là {top_trigger}, thường đi cùng cảm giác {top_emotion}."
    elif top_trigger:
        summary += f" Yếu tố được nhắc nhiều nhất là {top_trigger}."

    interpretation = (
        f"Dữ liệu gợi ý tuần này bạn {state}. Đây là nhận định từ check-in tự ghi, không phải kết luận y khoa; "
        "giá trị chính là giúp bạn nhìn thấy nhịp sống và điểm cần chăm nhẹ."
    )
    actions = [
        "Tối nay ghi thêm một check-in ngắn để xem cuối ngày mood đổi ra sao.",
        "Chọn một việc nhỏ liên quan đến yếu tố gây áp lực nhất và xử lý trong 10 phút.",
    ]
    if top_trigger:
        actions.insert(1, f"Viết một dòng: “Khi {top_trigger} xuất hiện, mình thường cần điều gì nhất?”")

    return DashboardInsightCard(
        insight_id=f"context_life_{uuid.uuid4().hex[:10]}",
        category="weekly_life_state",
        title="Tổng quan tuần này",
        user_safe_summary=summary,
        interpretation=interpretation,
        evidence_count=len(recent),
        evidence_sources=["mood_checkins"],
        confidence=_confidence_from_evidence(len(recent)),
        severity_band="watch" if avg is not None and avg < 6 else "neutral",
        suggested_action=_first_action(actions),
        recommended_actions=actions[:3],
        missing_data=missing,
        evidence_window_start=min(row.logged_date for row in recent),
        evidence_window_end=max(row.logged_date for row in recent),
        updated_at=now,
    )


def _daily_mood_card(checkins: list[MoodCheckin]) -> DashboardInsightCard | None:
    today_rows = [row for row in checkins if row.logged_date == local_date_utc7()]
    if not today_rows:
        return None
    avg = _avg_score(today_rows)
    bucket_counts = _bucket_counts(today_rows)
    emotions = _top_counter([e for row in today_rows for e in _string_list(row.emotions)], limit=3)
    triggers = _top_counter([t for row in today_rows for t in _string_list(row.triggers)], limit=1)
    missing = []
    if bucket_counts["evening"] == 0:
        missing.append("Thiáº¿u check-in buá»•i tá»‘i Ä‘á»ƒ xem cuá»‘i ngÃ y mood cÃ³ Ä‘á»•i khÃ´ng.")
    emotion_text = ", ".join(label for label, _ in emotions) if emotions else "chÆ°a rÃµ"
    trigger_text = triggers[0][0] if triggers else None
    summary = f"HÃ´m nay cÃ³ {len(today_rows)} check-in, mood trung bÃ¬nh khoáº£ng {avg}/10, cáº£m xÃºc ná»•i báº­t: {emotion_text}."
    if trigger_text:
        summary += f" Trigger ná»•i báº­t lÃ  {trigger_text}."
    actions = ["Ghi thÃªm check-in buá»•i tá»‘i náº¿u hÃ´m nay chÆ°a cÃ³.", "Chá»n má»™t viá»‡c nhá» trong 10 phÃºt Ä‘á»ƒ káº¿t ngÃ y nháº¹ hÆ¡n."]
    return DashboardInsightCard(
        insight_id=f"context_daily_{uuid.uuid4().hex[:10]}",
        category="daily_mood",
        title="Mood hÃ´m nay",
        user_safe_summary=summary,
        interpretation="Dá»¯ liá»‡u trong ngÃ y chá»‰ gá»£i Ã½ nhá»‹p hiá»‡n táº¡i, khÃ´ng pháº£i káº¿t luáº­n vá» báº¡n.",
        evidence_count=len(today_rows),
        evidence_sources=["mood_checkins"],
        confidence=_confidence_from_evidence(len(today_rows)),
        severity_band="watch" if avg is not None and avg < 5 else "neutral",
        suggested_action=actions[0],
        recommended_actions=actions,
        missing_data=missing,
        evidence_window_start=min(row.logged_date for row in today_rows),
        evidence_window_end=max(row.logged_date for row in today_rows),
        updated_at=get_now(),
    )


def _trigger_impact_card(checkins: list[MoodCheckin], *, days: int = 7) -> DashboardInsightCard | None:
    recent = _recent_checkins(checkins, days=days)
    pairs: dict[str, Counter[str]] = defaultdict(Counter)
    trigger_counts: Counter[str] = Counter()
    for row in recent:
        triggers = _string_list(row.triggers)
        emotions = _string_list(row.emotions)
        for trigger in triggers:
            trigger_counts[trigger] += 1
            for emotion in emotions:
                pairs[trigger][emotion] += 1
    if not trigger_counts:
        return None
    trigger, count = trigger_counts.most_common(1)[0]
    linked = pairs.get(trigger, Counter()).most_common(2)
    emotion_text = ", ".join(label for label, _ in linked) if linked else "chưa đủ rõ"
    actions = [
        f"Trước lần tới khi {trigger} xuất hiện, chuẩn bị một bước nhỏ có thể làm ngay.",
        "Ghi thêm cảm xúc đi kèm trigger để Serene phân biệt tần suất với mức ảnh hưởng.",
    ]
    return DashboardInsightCard(
        insight_id=f"context_trigger_{uuid.uuid4().hex[:10]}",
        category="trigger_impact",
        title=f"Yếu tố ảnh hưởng mạnh nhất: {trigger}",
        user_safe_summary=f"{trigger} xuất hiện {count} lần trong {days} ngày và thường đi cùng: {emotion_text}.",
        interpretation=(
            "Một trigger lặp lại không có nghĩa bạn làm sai điều gì; nó chỉ cho thấy có một bối cảnh đang lấy nhiều năng lượng hơn bình thường."
        ),
        evidence_count=sum(trigger_counts.values()),
        evidence_sources=["mood_checkins"],
        confidence=_confidence_from_evidence(sum(trigger_counts.values())),
        severity_band="watch" if count >= 2 else "neutral",
        suggested_action=actions[0],
        recommended_actions=actions,
        evidence_window_start=min(row.logged_date for row in recent),
        evidence_window_end=max(row.logged_date for row in recent),
        updated_at=get_now(),
    )


def _sleep_insight_card(
    checkins: list[MoodCheckin],
    sleep_checkins: list[SleepCheckin] | None = None,
    *,
    days: int = 7,
) -> DashboardInsightCard:
    recent = _recent_checkins(checkins, days=days)
    sleep_rows = list(sleep_checkins or [])
    values = _sleep_checkin_values(sleep_rows) or _sleep_values(recent)
    missing = []
    if not values:
        missing.append("Cần giờ ngủ hoặc số giờ ngủ trong check-in.")
        return DashboardInsightCard(
            insight_id=f"context_sleep_{uuid.uuid4().hex[:10]}",
            category="sleep",
            title="Giấc ngủ cần dữ liệu rõ hơn",
            user_safe_summary="Serene chưa thấy giờ ngủ hoặc số giờ ngủ đủ rõ để phân tích nhịp ngủ.",
            interpretation="Không nên đoán về giấc ngủ khi thiếu dữ liệu; bước đúng là hỏi người dùng ngủ từ mấy giờ đến mấy giờ.",
            evidence_count=0,
            evidence_sources=["sleep_checkins"],
            confidence="low",
            severity_band="neutral",
            suggested_action="Tối nay ghi: ngủ từ mấy giờ đến mấy giờ, và thức dậy lúc mấy giờ.",
            recommended_actions=["Ghi giờ ngủ tối qua.", "Ghi giờ thức dậy sáng nay."],
            missing_data=missing,
            updated_at=get_now(),
        )
    avg = round(sum(values) / len(values), 1)
    short_nights = sum(1 for h in values if h < 7)
    status = "đủ gần mục tiêu 7-8 giờ" if 7 <= avg <= 8.5 else "thấp hơn mục tiêu 7-8 giờ" if avg < 7 else "dài hơn mức thường gặp"
    window_dates = [row.sleep_date for row in sleep_rows] or [row.logged_date for row in recent]
    return DashboardInsightCard(
        insight_id=f"context_sleep_{uuid.uuid4().hex[:10]}",
        category="sleep",
        title="Giấc ngủ và năng lượng tuần này",
        user_safe_summary=f"{len(values)} ghi nhận ngủ gần đây cho thấy trung bình khoảng {avg} giờ/đêm, {status}.",
        interpretation=(
            f"Có {short_nights}/{len(values)} đêm dưới 7 giờ. Nếu mood cũng thấp hơn trong cùng giai đoạn, giấc ngủ có thể là một điểm cần chăm trước."
        ),
        evidence_count=len(values),
        evidence_sources=["sleep_checkins" if sleep_rows else "mood_checkins"],
        confidence=_confidence_from_evidence(len(values)),
        severity_band="watch" if avg < 7 else "neutral",
        suggested_action="Tối nay chọn một giờ tắt màn hình sớm hơn 20 phút.",
        recommended_actions=["Ghi giờ ngủ và giờ dậy.", "Thử giảm màn hình 20 phút trước khi ngủ."],
        evidence_window_start=min(window_dates),
        evidence_window_end=max(window_dates),
        updated_at=get_now(),
    )


def _nutrition_insight_card(meals: list[NutritionMealCheckin], *, days: int = 7) -> DashboardInsightCard | None:
    if not meals:
        return None
    latest = max(meals, key=lambda row: row.created_at or datetime.min)
    tags = _nutrition_tags(latest.items_text)
    all_tags = Counter(tag for meal in meals for tag in _nutrition_tags(meal.items_text))
    missing_slots = {"breakfast", "lunch", "dinner"} - {meal.meal_slot for meal in meals if meal.meal_date == latest.meal_date}
    actions = ["Bữa tới thêm một nguồn đạm hoặc rau nếu bữa gần nhất còn thiếu."]
    if "nhiều đường" in tags:
        actions.insert(0, "Sau bữa nhiều đường, thử thêm nước lọc hoặc một món có đạm/chất xơ để năng lượng ổn hơn.")
    return DashboardInsightCard(
        insight_id=f"context_nutrition_{uuid.uuid4().hex[:10]}",
        category="nutrition",
        title="Ăn uống và năng lượng",
        user_safe_summary=f"Bữa {latest.meal_slot} gần nhất: {latest.items_text}. Serene thấy các điểm: {', '.join(tags)}.",
        interpretation=(
            f"Trong {days} ngày, bạn có {len(meals)} bữa được ghi. Các dấu hiệu lặp lại nhiều nhất: "
            f"{', '.join(tag for tag, _ in all_tags.most_common(3))}. Đây là quan sát dinh dưỡng cơ bản, không phải lời khuyên y khoa."
        ),
        evidence_count=len(meals),
        evidence_sources=["nutrition_meal_checkins"],
        confidence=_confidence_from_evidence(len(meals)),
        severity_band="watch" if any(tag in tags for tag in ("nhiều đường", "đồ chiên/nặng bụng")) else "neutral",
        suggested_action=actions[0],
        recommended_actions=actions[:3],
        missing_data=[f"Thiếu log bữa: {', '.join(sorted(missing_slots))}."] if missing_slots else [],
        evidence_window_start=min(meal.meal_date for meal in meals),
        evidence_window_end=max(meal.meal_date for meal in meals),
        updated_at=get_now(),
    )


def _connection_insight_card(conversations: list[Conversation], profile_data: dict[str, Any], *, days: int = 7) -> DashboardInsightCard | None:
    start_dt, end_dt = _window_dt(days)
    recent = [c for c in conversations if c.last_message_at and start_dt <= c.last_message_at < end_dt]
    if not recent:
        return None
    session_count = len(recent)
    msg_count = sum(int(c.message_count or 0) for c in recent)
    summaries = list(profile_data.get("session_summaries") or [])[-10:]
    text = " ".join(str(s.get("summary") or "") + " " + str(s.get("dominant_emotion") or "") for s in summaries if isinstance(s, dict)).lower()
    loneliness_signal = any(k in text for k in ("cô đơn", "co don", "một mình", "thu mình", "lonely"))
    high_ai_use = session_count >= 7 or msg_count >= 50
    if high_ai_use or loneliness_signal:
        status = "watch"
        interpretation = (
            "Serene có thể hỗ trợ bạn sắp xếp cảm xúc, nhưng nếu tuần này bạn dựa vào app rất nhiều, "
            "đây là lúc nên kéo thêm một kết nối thật ngoài đời vào vòng hỗ trợ."
        )
        action = "Hôm nay thử nhắn một người bạn tin tưởng một câu ngắn."
    else:
        status = "neutral"
        interpretation = "Bạn đang dùng Serene như một điểm phản tư nhẹ; vẫn nên giữ nhịp kết nối ngoài đời khi có thể."
        action = "Chọn một tương tác thật nhỏ ngoài app: chào hỏi, nhắn tin, hoặc đi ra ngoài 10 phút."
    return DashboardInsightCard(
        insight_id=f"context_connection_{uuid.uuid4().hex[:10]}",
        category="real_world_connection",
        title="Kết nối ngoài đời",
        user_safe_summary=f"{days} ngày gần đây có {session_count} phiên với Serene, khoảng {msg_count} lượt tin nhắn được ghi nhận.",
        interpretation=interpretation,
        evidence_count=session_count,
        evidence_sources=["conversations"],
        confidence=_confidence_from_evidence(session_count),
        severity_band=status,  # type: ignore[arg-type]
        suggested_action=action,
        recommended_actions=[action, "Ra ngoài 10-15 phút nếu cơ thể cho phép."],
        missing_data=["Chưa có dữ liệu về kết nối thật ngoài ứng dụng."],
        evidence_window_start=start_dt.date(),
        evidence_window_end=(end_dt - timedelta(days=1)).date(),
        updated_at=get_now(),
    )


def _screening_insight_card(profile: ClinicalProfile | None) -> DashboardInsightCard | None:
    if profile is None:
        return None
    scores = {
        "PHQ-9": ("phq9", profile.phq9_score),
        "GAD-7": ("gad7", profile.gad7_score),
        "DASS-21 stress": ("dass21", profile.dass21_stress_score),
        "DASS-21 anxiety": ("dass21", profile.dass21_anxiety_score),
        "DASS-21 mood": ("dass21", profile.dass21_depression_score),
        "MDQ": ("mdq", profile.mdq_score),
        "PCL-5": ("pcl5", profile.pcl5_score),
    }
    available = [(label, inst, int(score)) for label, (inst, score) in scores.items() if score is not None]
    if not available:
        return None
    label, inst, score = max(available, key=lambda item: item[2])
    band = _screening_band(inst, score)
    action = "Nếu dấu hiệu kéo dài hoặc làm bạn khó sinh hoạt, cân nhắc trao đổi với chuyên gia phù hợp."
    return DashboardInsightCard(
        insight_id=f"context_screening_{uuid.uuid4().hex[:10]}",
        category="screening",
        title="Bài test sàng lọc",
        user_safe_summary=f"Kết quả sàng lọc gần đây có {label} ở mức {band}. Đây không phải chẩn đoán.",
        interpretation=(
            "Serene chỉ dùng kết quả test như một tín hiệu tham chiếu để đọc cùng mood, ngủ, ăn uống và trigger; "
            "không kết luận bạn có bất kỳ tình trạng cụ thể nào."
        ),
        evidence_count=len(available),
        evidence_sources=["screening_results"],
        confidence="medium",
        severity_band="watch" if band not in {"thấp", "nhẹ"} else "neutral",
        suggested_action=action,
        recommended_actions=[action, "Tiếp tục check-in mood và giấc ngủ trong tuần tới."],
        evidence_window_start=_dt_to_date(profile.last_scored_at),
        evidence_window_end=_dt_to_date(profile.last_scored_at),
        updated_at=get_now(),
    )


def _contextual_cards(
    db: Session,
    *,
    user_id: str,
    checkins: list[MoodCheckin],
    conversations: list[Conversation],
    profile_data: dict[str, Any],
    days: int = 7,
) -> list[DashboardInsightCard]:
    start_d, end_d = _date_window(days)
    meal_rows = db.scalars(
        select(NutritionMealCheckin)
        .where(
            NutritionMealCheckin.user_id == user_id,
            NutritionMealCheckin.meal_date >= start_d,
            NutritionMealCheckin.meal_date <= end_d,
        )
        .order_by(NutritionMealCheckin.meal_date.asc(), NutritionMealCheckin.created_at.asc())
    ).all()
    sleep_rows = db.scalars(
        select(SleepCheckin)
        .where(
            SleepCheckin.user_id == user_id,
            SleepCheckin.sleep_date >= start_d,
            SleepCheckin.sleep_date <= end_d,
        )
        .order_by(SleepCheckin.sleep_date.asc())
    ).all()
    clinical = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    candidates = [
        _daily_mood_card(checkins),
        _mood_life_state_card(checkins, days=days),
        _trigger_impact_card(checkins, days=days),
        _sleep_insight_card(checkins, list(sleep_rows), days=days) if (checkins or sleep_rows) else None,
        _nutrition_insight_card(list(meal_rows), days=days),
        _connection_insight_card(conversations, profile_data, days=days),
        _screening_insight_card(clinical),
    ]
    cards = [card for card in candidates if card is not None]
    actions: list[str] = []
    for card in cards:
        for action in card.recommended_actions:
            if action and action not in actions:
                actions.append(action)
    if actions:
        start_dates = [card.evidence_window_start for card in cards if card.evidence_window_start]
        end_dates = [card.evidence_window_end for card in cards if card.evidence_window_end]
        evidence_count = sum(card.evidence_count for card in cards)
        cards.append(
            DashboardInsightCard(
                insight_id=f"context_next_{uuid.uuid4().hex[:10]}",
                category="next_step",
                title="BÆ°á»›c tiáº¿p theo",
                user_safe_summary="Serene chá»n cÃ¡c bÆ°á»›c nhá» dá»±a trÃªn nhá»¯ng ghi nháº­n gáº§n Ä‘Ã¢y, Æ°u tiÃªn hÃ nh Ä‘á»™ng cÃ³ thá»ƒ lÃ m ngay.",
                interpretation="CÃ¡c gá»£i Ã½ nÃ y khÃ´ng pháº£i chá»‰ dáº«n y khoa; chá»‰ lÃ  cÃ¡ch giáº£m ma sÃ¡t Ä‘á»ƒ báº¡n tá»± chÄƒm sÃ³c trong ngÃ y.",
                evidence_count=evidence_count,
                evidence_sources=["dashboard_safe_insights"],
                confidence=_confidence_from_evidence(evidence_count),
                severity_band="neutral",
                suggested_action=actions[0],
                recommended_actions=actions[:3],
                evidence_window_start=min(start_dates) if start_dates else None,
                evidence_window_end=max(end_dates) if end_dates else None,
                updated_at=get_now(),
            )
        )
    return cards


def _evidence_for_card(card: DashboardInsightCard) -> list[dict[str, Any]]:
    if card.evidence:
        return card.evidence[:5]
    window = None
    if card.evidence_window_start and card.evidence_window_end:
        window = {
            "start": card.evidence_window_start.isoformat(),
            "end": card.evidence_window_end.isoformat(),
        }
    return [
        {
            "source": source,
            "count": card.evidence_count,
            "window": window,
        }
        for source in card.evidence_sources[:3]
    ]


def _persist_safe_cards(db: Session, *, user_id: str, cards: list[DashboardInsightCard]) -> None:
    safe_categories = {
        "daily_mood",
        "weekly_life_state",
        "trigger_impact",
        "sleep",
        "nutrition",
        "emotion",
        "real_world_connection",
        "self_care_action",
        "screening",
        "next_step",
    }
    now = get_now().replace(tzinfo=None)
    for card in cards:
        if card.category not in safe_categories:
            continue
        existing = db.scalar(
            select(DashboardSafeInsight).where(
                DashboardSafeInsight.user_id == user_id,
                DashboardSafeInsight.category == card.category,
            )
        )
        if existing is None:
            existing = DashboardSafeInsight(
                insight_id=f"dsi_{uuid.uuid4().hex[:16]}",
                user_id=user_id,
                category=card.category,
                title=card.title,
                user_safe_summary=card.user_safe_summary,
                interpretation=card.interpretation or card.user_safe_summary,
                confidence=card.confidence,
                severity_band=card.severity_band,
            )
            db.add(existing)
        existing.title = card.title[:200]
        existing.user_safe_summary = card.user_safe_summary
        existing.interpretation = card.interpretation or card.user_safe_summary
        existing.evidence = _evidence_for_card(card)
        existing.evidence_count = card.evidence_count
        existing.evidence_window_start = card.evidence_window_start
        existing.evidence_window_end = card.evidence_window_end
        existing.confidence = card.confidence
        existing.severity_band = card.severity_band
        existing.missing_data = list(card.missing_data or [])[:6]
        existing.recommended_actions = list(card.recommended_actions or [])[:3]
        existing.source_version = card.source_version
        existing.updated_at = now
    db.flush()


def build_safe_insight_cards(
    db: Session,
    *,
    user_id: str,
    sufficiency: DashboardDataSufficiency,
    days: int = 7,
) -> list[DashboardInsightCard]:
    try:
        cards = build_and_persist_dashboard_insights(db, user_id=user_id, days=days)
        db.commit()
        return cards[:_MAX_FRONTEND_INSIGHT_CARDS]
    except Exception:
        fallback_confidence = _confidence_for_cards(
            sufficiency.readiness_level,
            checkins=sufficiency.mood_checkin_count,
            sessions=sufficiency.total_session_count,
        )
        db_cards = _fetch_hypothesis_insights(db, user_id, fallback_confidence=fallback_confidence)
        return db_cards[:_MAX_FRONTEND_INSIGHT_CARDS]


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
                explanation="Serene chưa có đủ dữ liệu thói quen để nói về tiến triển một cách có ích.",
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

    dimensions = wellness_dimensions_from_insights(all_cards)
    if not dimensions:
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


def build_safe_insights_payload(db: Session, *, user_id: str, days: int = 7) -> dict[str, Any]:
    sufficiency = compute_data_sufficiency(db, user_id=user_id)
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data: dict[str, Any] = dict(profile_row.profile if profile_row and profile_row.profile else {})
    cards = build_safe_insight_cards(db, user_id=user_id, sufficiency=sufficiency, days=days)
    return {
        "window": f"{days}d",
        "sufficiency": sufficiency.model_dump(mode="json"),
        "insights": [c.model_dump(mode="json") for c in cards],
    }
