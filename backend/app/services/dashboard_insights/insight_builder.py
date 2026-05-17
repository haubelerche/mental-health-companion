from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.dashboard.types import DashboardDataSufficiency, DashboardInsightCard, WellnessDimensionCard
from app.dashboard.sufficiency import compute_data_sufficiency
from app.services.db.models import (
    ClinicalProfile,
    Conversation,
    DashboardSafeInsight,
    MoodCheckin,
    NutritionMealCheckin,
    SleepCheckin,
    UserProfile,
)
from app.services.utils import get_now, local_date_utc7

SOURCE_VERSION = "dashboard_insight_builder_v1"
SAFE_CATEGORIES = (
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
)

MoodBand = Literal["low", "medium", "high"]

_MOOD_SCORE = {
    "terrible": 1,
    "stressful": 1,
    "bad": 2,
    "sad": 2,
    "fine": 5,
    "neutral": 5,
    "good": 8,
    "peaceful": 8,
    "awesome": 10,
    "delightful": 10,
}


def _window(days: int) -> tuple[date, date]:
    end = local_date_utc7()
    return end - timedelta(days=max(1, days) - 1), end


def _window_dt(days: int) -> tuple[datetime, datetime]:
    start, end = _window(days)
    return datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())


def _score(mood: str | None) -> int:
    if not mood:
        return 5
    return _MOOD_SCORE.get(str(mood).strip().lower(), 5)


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _confidence(count: int) -> MoodBand:
    if count >= 10:
        return "high"
    if count >= 4:
        return "medium"
    return "low"


def _top(values: list[str], limit: int = 3) -> list[tuple[str, int]]:
    return Counter(v for v in values if v).most_common(limit)


def _card(
    *,
    category: str,
    title: str,
    summary: str,
    interpretation: str,
    evidence_count: int,
    evidence_sources: list[str],
    evidence: list[dict[str, Any]],
    confidence: MoodBand | None = None,
    severity_band: Literal["neutral", "watch"] = "neutral",
    actions: list[str] | None = None,
    missing_data: list[str] | None = None,
    window_start: date | None = None,
    window_end: date | None = None,
) -> DashboardInsightCard:
    recommended = (actions or [])[:3]
    return DashboardInsightCard(
        insight_id=f"dsi_{category}_{uuid4().hex[:10]}",
        category=category,  # type: ignore[arg-type]
        title=title,
        user_safe_summary=summary,
        interpretation=interpretation,
        evidence=evidence,
        evidence_count=evidence_count,
        evidence_sources=evidence_sources,
        confidence=confidence or _confidence(evidence_count),
        severity_band=severity_band,
        suggested_action=recommended[0] if recommended else None,
        recommended_actions=recommended,
        missing_data=missing_data or [],
        source_version=SOURCE_VERSION,
        evidence_window_start=window_start,
        evidence_window_end=window_end,
        updated_at=get_now(),
    )


def _recent_checkins(checkins: list[MoodCheckin], days: int) -> list[MoodCheckin]:
    start, end = _window(days)
    return [row for row in checkins if start <= row.logged_date <= end]


def build_daily_mood_insight(checkins: list[MoodCheckin]) -> DashboardInsightCard:
    today = local_date_utc7()
    rows = [row for row in checkins if row.logged_date == today]
    missing = []
    buckets = {str(row.time_bucket or "other"): row for row in rows}
    if "evening" not in buckets:
        missing.append("Thiếu check-in buổi tối để so sánh cảm xúc cuối ngày.")
    if not rows:
        return _card(
            category="daily_mood",
            title="Hôm nay cảm xúc của bạn chưa đủ rõ",
            summary="Hôm nay Serene chưa có check-in nào để nhận xét mood trong ngày.",
            interpretation="Không nên đoán tình hình hôm nay khi chưa có dữ liệu trong ngày. Một check-in ngắn sẽ giúp dashboard đọc đúng hơn.",
            evidence_count=0,
            evidence_sources=["mood_checkins"],
            evidence=[],
            confidence="low",
            missing_data=["Cần ít nhất một check-in hôm nay.", *missing],
            actions=["Check-in ngắn hôm nay.", "Nếu có thể, thêm check-in buổi tối."],
            window_start=today,
            window_end=today,
        )

    avg = round(sum(_score(row.mood) for row in rows) / len(rows), 1)
    emotions = _top([e for row in rows for e in _strings(row.emotions)], 2)
    triggers = _top([t for row in rows for t in _strings(row.triggers)], 2)
    emotion_text = ", ".join(label for label, _ in emotions) or "chưa rõ"
    trigger_text = ", ".join(label for label, _ in triggers) or "chưa rõ"
    severity = "watch" if avg < 5 else "neutral"
    trend_bits = []
    for key, label in (("morning", "sáng"), ("afternoon", "chiều"), ("evening", "tối")):
        row = buckets.get(key)
        if row:
            trend_bits.append(f"{label}: {_score(row.mood)}/10")
    return _card(
        category="daily_mood",
        title="Hôm nay cảm xúc của bạn ra sao",
        summary=f"Hôm nay có {len(rows)} check-in, mood trung bình khoảng {avg}/10. Cảm xúc nổi bật: {emotion_text}.",
        interpretation=f"Dữ liệu hôm nay gợi ý mood đang chịu ảnh hưởng từ: {trigger_text}. {'; '.join(trend_bits)}.",
        evidence_count=len(rows),
        evidence_sources=["mood_checkins"],
        evidence=[{"source": "mood_checkins", "count": len(rows), "summary": f"avg_mood={avg}, emotions={emotion_text}, triggers={trigger_text}"}],
        severity_band=severity,
        missing_data=missing,
        actions=["Ghi thêm check-in buổi tối để Serene thấy mood cuối ngày.", "Chọn một việc nhỏ làm giảm áp lực lớn nhất trong hôm nay."],
        window_start=today,
        window_end=today,
    )


def build_weekly_life_state_insight(checkins: list[MoodCheckin], conversations: list[Conversation], sleeps: list[SleepCheckin], days: int) -> DashboardInsightCard:
    recent = _recent_checkins(checkins, days)
    start, end = _window(days)
    if not recent:
        return _card(
            category="weekly_life_state",
            title="Tổng quan tuần này",
            summary="Tuần này chưa có đủ check-in để Serene nhận định tình hình đời sống.",
            interpretation="Dữ liệu hiện tại còn thấp; dashboard cần mood, trigger, giấc ngủ hoặc bữa ăn để nói điều có ích.",
            evidence_count=0,
            evidence_sources=["mood_checkins"],
            evidence=[],
            confidence="low",
            missing_data=["Cần vài check-in trong tuần.", "Cần ít nhất một check-in buổi tối."],
            actions=["Check-in một lần hôm nay.", "Thêm giờ ngủ tối qua nếu nhớ."],
            window_start=start,
            window_end=end,
        )
    avg = round(sum(_score(row.mood) for row in recent) / len(recent), 1)
    trigger_counts = Counter(t for row in recent for t in _strings(row.triggers))
    top_trigger, top_count = trigger_counts.most_common(1)[0] if trigger_counts else ("chưa rõ", 0)
    low_days = len({row.logged_date for row in recent if _score(row.mood) < 5})
    short_sleep = sum(1 for row in sleeps if row.duration_hours is not None and row.duration_hours < 7)
    conv_count = len(conversations)

    if avg < 4.5 and top_count >= 2:
        state = "overloaded"
        phrase = "có vẻ đang nhiều sóng gió và phải gồng khá nhiều"
    elif top_count >= 2 and any(token in top_trigger.lower() for token in ("công", "học", "deadline", "study", "work")):
        state = "work_or_study_pressure"
        phrase = "có vẻ chịu áp lực rõ từ công việc hoặc học tập"
    elif conv_count >= 7:
        state = "lonely_or_withdrawn"
        phrase = "có thể đang dựa vào Serene khá nhiều trong lúc thiếu kết nối ngoài đời"
    elif low_days >= 2 or short_sleep >= 2:
        state = "mildly_fluctuating"
        phrase = "đang dao động, nhất là khi ngủ ít hoặc trigger lặp lại"
    else:
        state = "steady"
        phrase = "khá yên bình hoặc chỉ dao động nhẹ"

    return _card(
        category="weekly_life_state",
        title="Tổng quan tuần này",
        summary=f"Trong {days} ngày, mood trung bình khoảng {avg}/10 từ {len(recent)} check-in. Yếu tố nổi bật: {top_trigger}.",
        interpretation=f"Dữ liệu gợi ý tuần này bạn {phrase}. Nhận định này dựa trên check-in, trigger, giấc ngủ và nhịp dùng app; không phải kết luận cố định.",
        evidence_count=len(recent),
        evidence_sources=["mood_checkins", "sleep_checkins", "conversations"],
        evidence=[
            {"source": "mood_checkins", "count": len(recent), "summary": f"avg_mood={avg}, low_days={low_days}, state={state}"},
            {"source": "sleep_checkins", "count": len(sleeps), "summary": f"short_sleep_nights={short_sleep}"},
            {"source": "conversations", "count": conv_count, "summary": "Serene app usage in window"},
        ],
        severity_band="watch" if state in {"overloaded", "work_or_study_pressure", "lonely_or_withdrawn"} else "neutral",
        missing_data=[] if any(row.time_bucket == "evening" for row in recent) else ["Thiếu check-in buổi tối để đọc nhịp cuối ngày."],
        actions=[
            "Viết ra một việc nhỏ nhất cần xử lý trong ngày mai.",
            "Ghi check-in buổi tối để Serene thấy ngày kết thúc ra sao.",
            "Nếu tuần này nặng, nhắn một người thật ngoài đời một câu ngắn.",
        ],
        window_start=start,
        window_end=end,
    )


def build_trigger_impact_insight(checkins: list[MoodCheckin], days: int) -> DashboardInsightCard | None:
    recent = _recent_checkins(checkins, days)
    start, end = _window(days)
    trigger_counts: Counter[str] = Counter()
    trigger_emotions: dict[str, Counter[str]] = defaultdict(Counter)
    trigger_low_score: dict[str, list[int]] = defaultdict(list)
    for row in recent:
        for trigger in _strings(row.triggers):
            trigger_counts[trigger] += 1
            trigger_low_score[trigger].append(_score(row.mood))
            for emotion in _strings(row.emotions):
                trigger_emotions[trigger][emotion] += 1
    if not trigger_counts:
        return None
    frequent, freq_count = trigger_counts.most_common(1)[0]
    scored_triggers = {key: scores for key, scores in trigger_low_score.items() if scores}
    intense = (
        min(scored_triggers, key=lambda key: sum(scored_triggers[key]) / len(scored_triggers[key]))
        if scored_triggers
        else frequent
    )
    emotions = ", ".join(label for label, _ in trigger_emotions[frequent].most_common(2)) or "chưa rõ"
    return _card(
        category="trigger_impact",
        title=f"Yếu tố ảnh hưởng nhiều nhất: {frequent}",
        summary=f"{frequent} xuất hiện {freq_count} lần trong {days} ngày và thường đi cùng: {emotions}.",
        interpretation=f"Trigger xuất hiện nhiều nhất là {frequent}; trigger có mood đi xuống rõ nhất là {intense}. Hai điều này giúp phân biệt tần suất với mức ảnh hưởng cảm xúc.",
        evidence_count=sum(trigger_counts.values()),
        evidence_sources=["mood_checkins"],
        evidence=[{"source": "mood_checkins", "count": sum(trigger_counts.values()), "summary": f"frequent={frequent}, intense={intense}, emotions={emotions}"}],
        severity_band="watch" if freq_count >= 2 else "neutral",
        actions=[f"Trước lần tới khi {frequent} xuất hiện, chuẩn bị một bước nhỏ có thể làm ngay.", "Ghi thêm cảm xúc đi kèm trigger để Serene đọc mức ảnh hưởng rõ hơn."],
        window_start=start,
        window_end=end,
    )


def build_sleep_insight(sleeps: list[SleepCheckin], days: int) -> DashboardInsightCard:
    start, end = _window(days)
    values = [float(row.duration_hours) for row in sleeps if row.duration_hours is not None]
    if not values:
        return _card(
            category="sleep",
            title="Giấc ngủ cần dữ liệu rõ hơn",
            summary="Serene chưa có giờ ngủ và giờ dậy đủ rõ để phân tích nhịp ngủ.",
            interpretation="Dashboard không nên đoán về giấc ngủ. Cần biết tối qua bạn ngủ từ mấy giờ đến mấy giờ để so với mốc 7-8 giờ.",
            evidence_count=0,
            evidence_sources=["sleep_checkins"],
            evidence=[],
            confidence="low",
            missing_data=["Cần giờ ngủ.", "Cần giờ thức dậy."],
            actions=["Ghi giờ ngủ tối qua.", "Ghi giờ thức dậy sáng nay."],
            window_start=start,
            window_end=end,
        )
    avg = round(sum(values) / len(values), 1)
    short = sum(1 for value in values if value < 7)
    irregular = max(values) - min(values) >= 2.5 if len(values) >= 2 else False
    if avg < 7:
        trend = "ngủ ít hơn mốc 7-8 giờ"
    elif irregular:
        trend = "ngủ khá thất thường so với mốc 7-8 giờ"
    else:
        trend = "ngủ tương đối đủ so với mốc 7-8 giờ"
    return _card(
        category="sleep",
        title="Giấc ngủ và năng lượng",
        summary=f"{len(values)} ghi nhận gần đây cho thấy trung bình khoảng {avg} giờ/đêm, {trend}.",
        interpretation=f"Có {short}/{len(values)} đêm dưới 7 giờ. Nếu mood cũng thấp trong cùng giai đoạn, giấc ngủ là điểm nên chăm trước.",
        evidence_count=len(values),
        evidence_sources=["sleep_checkins"],
        evidence=[{"source": "sleep_checkins", "count": len(values), "summary": f"avg={avg}, short_nights={short}, irregular={irregular}"}],
        severity_band="watch" if avg < 7 or irregular else "neutral",
        actions=["Tối nay chọn một giờ tắt màn hình sớm hơn 20 phút.", "Ghi lại giờ ngủ và giờ dậy sau khi thức."],
        window_start=start,
        window_end=end,
    )


def _nutrition_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    if any(key in lowered for key in ("thịt", "cá", "trứng", "gà", "bò", "đậu", "tofu", "sữa", "yogurt", "protein")):
        tags.append("có đạm")
    if any(key in lowered for key in ("rau", "salad", "quả", "trái cây", "chuối", "cam", "táo", "yến mạch", "gạo lứt", "khoai")):
        tags.append("có chất xơ")
    if any(key in lowered for key in ("rau", "salad", "cải", "bông cải", "dưa leo", "cà chua")):
        tags.append("có rau")
    if any(key in lowered for key in ("trà sữa", "nước ngọt", "bánh ngọt", "kẹo", "đường", "soda")):
        tags.append("nhiều đường")
    if any(key in lowered for key in ("cà phê", "coffee", "trà đặc", "caffeine", "matcha")):
        tags.append("có caffeine")
    if any(key in lowered for key in ("chiên", "rán", "gà rán", "khoai tây chiên", "đồ chiên")):
        tags.append("đồ chiên/nặng bụng")
    return tags or ["cần mô tả rõ hơn"]


def build_nutrition_insight(meals: list[NutritionMealCheckin], days: int) -> DashboardInsightCard | None:
    if not meals:
        return None
    start, end = _window(days)
    latest = max(meals, key=lambda meal: meal.created_at or datetime.min)
    tags = _nutrition_tags(latest.items_text)
    all_tags = Counter(tag for meal in meals for tag in _nutrition_tags(meal.items_text))
    missing_slots = {"breakfast", "lunch", "dinner"} - {meal.meal_slot for meal in meals if meal.meal_date == latest.meal_date}
    action = "Bữa tới thêm một nguồn đạm hoặc rau nếu bữa gần nhất còn thiếu."
    if "nhiều đường" in tags:
        action = "Sau bữa nhiều đường, thử thêm nước lọc hoặc một món có đạm/chất xơ để năng lượng ổn hơn."
    return _card(
        category="nutrition",
        title="Ăn uống và năng lượng",
        summary=f"Bữa {latest.meal_slot} gần nhất: {latest.items_text}. Điểm Serene thấy: {', '.join(tags)}.",
        interpretation=f"Trong {days} ngày có {len(meals)} bữa được ghi. Các dấu hiệu lặp lại: {', '.join(tag for tag, _ in all_tags.most_common(3))}. Đây là quan sát dinh dưỡng cơ bản, không phán xét và không phải lời khuyên y khoa.",
        evidence_count=len(meals),
        evidence_sources=["nutrition_meal_checkins"],
        evidence=[{"source": "nutrition_meal_checkins", "count": len(meals), "summary": f"latest_tags={tags}, top_tags={all_tags.most_common(3)}"}],
        severity_band="watch" if any(tag in tags for tag in ("nhiều đường", "đồ chiên/nặng bụng")) else "neutral",
        missing_data=[f"Thiếu log bữa: {', '.join(sorted(missing_slots))}."] if missing_slots else [],
        actions=[action],
        window_start=start,
        window_end=end,
    )


def build_connection_insight(conversations: list[Conversation], profile_data: dict[str, Any], days: int) -> DashboardInsightCard | None:
    if not conversations:
        return None
    start, end = _window(days)
    session_count = len(conversations)
    msg_count = sum(int(row.message_count or 0) for row in conversations)
    summaries = list(profile_data.get("session_summaries") or [])[-10:]
    text = " ".join(str(item.get("summary") or "") + " " + str(item.get("dominant_emotion") or "") for item in summaries if isinstance(item, dict)).lower()
    loneliness = any(token in text for token in ("cô đơn", "co don", "một mình", "thu mình", "lonely"))
    high_use = session_count >= 7 or msg_count >= 50
    if high_use or loneliness:
        interpretation = "Serene có thể hỗ trợ bạn sắp xếp cảm xúc, nhưng nếu tuần này bạn dựa vào app rất nhiều, đây là lúc nên kéo thêm một kết nối thật ngoài đời vào vòng hỗ trợ."
        severity = "watch"
        actions = ["Hôm nay thử nhắn một người bạn tin tưởng một câu ngắn.", "Ra ngoài 10-15 phút nếu cơ thể cho phép."]
    else:
        interpretation = "Bạn đang dùng Serene như một điểm phản tư nhẹ; vẫn nên giữ nhịp kết nối ngoài đời khi có thể."
        severity = "neutral"
        actions = ["Chọn một tương tác thật nhỏ ngoài app: chào hỏi, nhắn tin, hoặc đi ra ngoài 10 phút."]
    return _card(
        category="real_world_connection",
        title="Kết nối ngoài đời",
        summary=f"{days} ngày gần đây có {session_count} phiên với Serene, khoảng {msg_count} lượt tin nhắn được ghi nhận.",
        interpretation=interpretation,
        evidence_count=session_count,
        evidence_sources=["conversations"],
        evidence=[{"source": "conversations", "count": session_count, "summary": f"message_count={msg_count}, high_ai_use={high_use}, loneliness_signal={loneliness}"}],
        severity_band=severity,  # type: ignore[arg-type]
        missing_data=["Chưa có dữ liệu trực tiếp về kết nối thật ngoài ứng dụng."],
        actions=actions,
        window_start=start,
        window_end=end,
    )


def build_self_care_insight(profile_data: dict[str, Any]) -> DashboardInsightCard:
    coping = [item for item in list(profile_data.get("coping_history") or []) if isinstance(item, dict)]
    useful = [
        item
        for item in coping
        if int(item.get("tried_count") or 0) > 0 and int(item.get("self_reported_effective") or 0) > 0
    ]
    if not useful:
        return _card(
            category="self_care_action",
            title="Hành động tự chăm sóc",
            summary="Serene chưa đủ bằng chứng để nói hành động nào thật sự giúp bạn nhẹ hơn.",
            interpretation="Phần này chỉ nên kết luận khi có hành động được thử lại và có phản hồi tích cực hoặc mood cải thiện sau đó.",
            evidence_count=0,
            evidence_sources=["user_profiles"],
            evidence=[],
            confidence="low",
            missing_data=["Cần ghi hành động đã thử.", "Cần phản hồi hành động đó có giúp nhẹ hơn không."],
            actions=["Sau khi thử một việc nhỏ, đánh dấu nó có giúp bạn nhẹ hơn không."],
            window_start=None,
            window_end=None,
        )
    best = max(useful, key=lambda item: (int(item.get("self_reported_effective") or 0), int(item.get("tried_count") or 0)))
    action = str(best.get("action") or "một hành động nhỏ").strip()
    effective = int(best.get("self_reported_effective") or 0)
    tried = int(best.get("tried_count") or 0)
    return _card(
        category="self_care_action",
        title="Hành động tự chăm sóc từng giúp bạn",
        summary=f"{action} đã được ghi nhận {tried} lần, trong đó có {effective} lần bạn phản hồi là có ích.",
        interpretation="Đây là phản hồi chủ quan của bạn, nhưng có giá trị thực tế vì nó chỉ ra một hành động nhỏ có thể thử lại khi mood đi xuống.",
        evidence_count=tried,
        evidence_sources=["user_profiles"],
        evidence=[{"source": "user_profiles", "count": tried, "summary": f"action={action}, effective={effective}"}],
        actions=[f"Khi thấy căng, thử lại: {action}."],
        window_start=None,
        window_end=None,
    )


def _screening_band(instrument: str, score: int) -> str:
    if instrument == "phq9":
        return "rất cao" if score >= 20 else "cao" if score >= 15 else "trung bình" if score >= 10 else "nhẹ" if score >= 5 else "thấp"
    if instrument == "gad7":
        return "cao" if score >= 15 else "trung bình" if score >= 10 else "nhẹ" if score >= 5 else "thấp"
    if instrument == "pcl5":
        return "cần theo dõi" if score >= 31 else "thấp"
    if instrument == "mdq":
        return "cần theo dõi" if score >= 7 else "thấp"
    return "cần theo dõi" if score >= 10 else "thấp"


def build_screening_insight(profile: ClinicalProfile | None) -> DashboardInsightCard | None:
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
    label, instrument, score = max(available, key=lambda item: item[2])
    band = _screening_band(instrument, score)
    last_date = profile.last_scored_at.date() if profile.last_scored_at else None
    return _card(
        category="screening",
        title="Bài test sàng lọc",
        summary=f"Kết quả sàng lọc gần đây có {label} ở mức {band}. Đây không phải chẩn đoán.",
        interpretation="Serene chỉ dùng kết quả test như tín hiệu tham chiếu để đọc cùng mood, ngủ, ăn uống và trigger; không kết luận bạn có bất kỳ tình trạng cụ thể nào.",
        evidence_count=len(available),
        evidence_sources=["screening_results"],
        evidence=[{"source": "clinical_profiles", "count": len(available), "summary": f"highest_screening={label}, band={band}"}],
        confidence="medium",
        severity_band="watch" if band not in {"thấp", "nhẹ"} else "neutral",
        actions=["Nếu dấu hiệu kéo dài hoặc làm bạn khó sinh hoạt, cân nhắc trao đổi với chuyên gia phù hợp.", "Tiếp tục check-in mood và giấc ngủ trong tuần tới."],
        window_start=last_date,
        window_end=last_date,
    )


def _load_data(db: Session, user_id: str, days: int) -> tuple[dict[str, Any], list[MoodCheckin], list[SleepCheckin], list[NutritionMealCheckin], list[Conversation], ClinicalProfile | None]:
    start_d, end_d = _window(days)
    start_dt, end_dt = _window_dt(days)
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data = dict(profile_row.profile if profile_row and profile_row.profile else {})
    checkins = list(db.scalars(select(MoodCheckin).where(MoodCheckin.user_id == user_id, MoodCheckin.logged_date >= start_d, MoodCheckin.logged_date <= end_d).order_by(MoodCheckin.logged_date.asc(), MoodCheckin.logged_at.asc())).all())
    sleeps = list(db.scalars(select(SleepCheckin).where(SleepCheckin.user_id == user_id, SleepCheckin.sleep_date >= start_d, SleepCheckin.sleep_date <= end_d).order_by(SleepCheckin.sleep_date.asc())).all())
    if not sleeps:
        for row in checkins:
            try:
                blob = json.loads(row.note or "{}")
            except (TypeError, ValueError):
                continue
            extra = blob.get("extra") if isinstance(blob, dict) else None
            if not isinstance(extra, dict):
                continue
            raw_hours = extra.get("sleep_hours")
            try:
                hours = float(raw_hours)
            except (TypeError, ValueError):
                continue
            if 0 < hours <= 16:
                sleeps.append(
                    SleepCheckin(
                        sleep_id=f"legacy_sleep_{row.checkin_id}",
                        user_id=user_id,
                        sleep_date=row.logged_date,
                        duration_hours=hours,
                        source="self_report",
                    )
                )
    meals = list(db.scalars(select(NutritionMealCheckin).where(NutritionMealCheckin.user_id == user_id, NutritionMealCheckin.meal_date >= start_d, NutritionMealCheckin.meal_date <= end_d).order_by(NutritionMealCheckin.meal_date.asc(), NutritionMealCheckin.created_at.asc())).all())
    conversations = list(db.scalars(select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None), Conversation.last_message_at >= start_dt, Conversation.last_message_at < end_dt)).all())
    clinical = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    return profile_data, checkins, sleeps, meals, conversations, clinical


def build_dashboard_insight_cards(db: Session, *, user_id: str, days: int = 7) -> list[DashboardInsightCard]:
    profile_data, checkins, sleeps, meals, conversations, clinical = _load_data(db, user_id, days)
    cards: list[DashboardInsightCard | None] = [
        build_daily_mood_insight(checkins),
        build_weekly_life_state_insight(checkins, conversations, sleeps, days),
        build_trigger_impact_insight(checkins, days),
        build_sleep_insight(sleeps, days),
        build_nutrition_insight(meals, days),
        build_connection_insight(conversations, profile_data, days),
        build_self_care_insight(profile_data),
        build_screening_insight(clinical),
    ]
    out = [card for card in cards if card is not None]
    actions: list[str] = []
    for card in out:
        for action in card.recommended_actions:
            if action and action not in actions:
                actions.append(action)
    if actions:
        start, end = _window(days)
        evidence_count = sum(card.evidence_count for card in out)
        out.append(
            _card(
                category="next_step",
                title="Bước tiếp theo",
                summary="Serene chọn các bước nhỏ dựa trên những ghi nhận gần đây, ưu tiên hành động có thể làm ngay.",
                interpretation="Các gợi ý này không phải chỉ dẫn y khoa; chúng chỉ giúp giảm ma sát để bạn tự chăm sóc trong ngày.",
                evidence_count=evidence_count,
                evidence_sources=["dashboard_safe_insights"],
                evidence=[{"source": "dashboard_safe_insights", "count": evidence_count, "summary": "Derived from current safe dashboard cards."}],
                severity_band="neutral",
                actions=actions[:3],
                window_start=start,
                window_end=end,
            )
        )
    return out


def persist_dashboard_safe_insights(db: Session, *, user_id: str, cards: list[DashboardInsightCard]) -> None:
    db.execute(delete(DashboardSafeInsight).where(DashboardSafeInsight.user_id == user_id))
    for card in cards:
        db.add(
            DashboardSafeInsight(
                insight_id=card.insight_id,
                user_id=user_id,
                category=card.category,
                title=card.title,
                user_safe_summary=card.user_safe_summary,
                interpretation=card.interpretation or card.user_safe_summary,
                evidence=card.evidence,
                evidence_count=card.evidence_count,
                evidence_window_start=card.evidence_window_start,
                evidence_window_end=card.evidence_window_end,
                confidence=card.confidence,
                severity_band=card.severity_band,
                missing_data=card.missing_data,
                recommended_actions=card.recommended_actions,
                source_version=SOURCE_VERSION,
                updated_at=card.updated_at.replace(tzinfo=None) if card.updated_at.tzinfo else card.updated_at,
            )
        )
    db.flush()


def build_and_persist_dashboard_insights(db: Session, *, user_id: str, days: int = 7) -> list[DashboardInsightCard]:
    cards = build_dashboard_insight_cards(db, user_id=user_id, days=days)
    persist_dashboard_safe_insights(db, user_id=user_id, cards=cards)
    return cards


def build_safe_dashboard_payload(db: Session, *, user_id: str, window: str = "7d") -> dict[str, Any]:
    days = int(window.removesuffix("d")) if window in {"7d", "14d", "30d"} else 7
    sufficiency = compute_data_sufficiency(db, user_id=user_id)
    cards = build_and_persist_dashboard_insights(db, user_id=user_id, days=days)
    db.commit()
    return {
        "window": f"{days}d",
        "updated_at": get_now().isoformat(),
        "sufficiency": sufficiency.model_dump(mode="json"),
        "insights": [card.model_dump(mode="json") for card in cards],
    }


def wellness_dimensions_from_insights(cards: list[DashboardInsightCard]) -> list[WellnessDimensionCard]:
    mapping = {
        "daily_mood": ("emotion", "Cảm xúc"),
        "sleep": ("sleep", "Giấc ngủ"),
        "nutrition": ("nutrition", "Ăn uống và năng lượng"),
        "real_world_connection": ("connection", "Kết nối ngoài đời"),
        "self_care_action": ("body", "Hành động tự chăm sóc"),
        "screening": ("screening", "Bài test sàng lọc"),
    }
    out: list[WellnessDimensionCard] = []
    seen: set[str] = set()
    for card in cards:
        if card.category not in mapping:
            continue
        dimension, label = mapping[card.category]
        if dimension in seen:
            continue
        seen.add(dimension)
        status = "needs_attention" if card.severity_band == "watch" else "steady"
        if card.evidence_count == 0:
            status = "limited_data"
        score = None if card.evidence_count == 0 else 45 if status == "needs_attention" else 75
        out.append(
            WellnessDimensionCard(
                dimension=dimension,  # type: ignore[arg-type]
                label=label,
                status=status,  # type: ignore[arg-type]
                score=score,
                explanation=card.interpretation or card.user_safe_summary,
                evidence_count=card.evidence_count,
                suggested_action=card.recommended_actions[0] if card.recommended_actions else card.suggested_action,
            )
        )
    return out
