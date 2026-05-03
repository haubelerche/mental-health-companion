from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import ClinicalProfile, JournalEntry, JournalPrompt, MoodCheckin, User, UserProfile
from app.services.db.session import get_db
from app.services.schemas.payloads import JournalCreateRequest
from app.services.utils import local_date_utc7, make_id, utc_now

router = APIRouter(prefix="/reflect", tags=["reflect"])

MOOD_TO_SCORE = {
    "stressful": (1, "khó khăn"),
    "sad": (2, "buồn"),
    "neutral": (3, "ổn"),
    "peaceful": (4, "tốt"),
    "delightful": (5, "rất tốt"),
}
WEEKLY_NOTE_CACHE_DAYS = 7
WEEKLY_NOTE_REFRESH_COOLDOWN_HOURS = 6


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_iso_z(dt: datetime | None) -> str | None:
    point = _as_utc(dt)
    if point is None:
        return None
    return point.isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return _as_utc(parsed)


def _build_mood_trend_data(*, db: Session, user_id: str, days: int) -> dict[str, Any]:
    today = local_date_utc7()
    start = today - timedelta(days=days - 1)
    rows = db.scalars(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == user_id,
            MoodCheckin.logged_date >= start,
            MoodCheckin.logged_date <= today,
        )
        .order_by(MoodCheckin.logged_date.asc())
    ).all()

    point_map = {row.logged_date: row for row in rows}
    points: list[dict[str, Any]] = []
    missing: list[str] = []
    for idx in range(days):
        day = start + timedelta(days=idx)
        if day not in point_map:
            missing.append(day.isoformat())
            continue
        item = point_map[day]
        score, label = MOOD_TO_SCORE.get(item.mood, (3, "ổn"))
        points.append(
            {
                "date": day.isoformat(),
                "mood_score": score,
                "label": label,
                "emoji": item.emoji,
            }
        )

    return {
        "period": {"from": start.isoformat(), "to": today.isoformat()},
        "points": points,
        "days_missing": missing,
        "summary": "Tuần này bạn có xu hướng ổn định hơn." if points else "Chưa có đủ dữ liệu mood.",
    }


def _normalize_trigger_payload(profile_data: dict[str, Any]) -> list[dict[str, Any]]:
    trigger_tags = dict(profile_data.get("trigger_tags") or {})
    ordered = sorted(
        trigger_tags.items(),
        key=lambda item: int((item[1] or {}).get("count") or 0),
        reverse=True,
    )[:5]
    return [
        {
            "tag": tag,
            "count": int((meta or {}).get("count") or 0),
            "last_seen": _to_iso_z(_parse_datetime((meta or {}).get("last_seen"))),
        }
        for tag, meta in ordered
    ]


def _build_wellness_score(
    *,
    mood_points: list[dict[str, Any]],
    clinical: ClinicalProfile | None,
    profile_data: dict[str, Any],
) -> tuple[int, str]:
    weighted_values: list[tuple[float, float]] = []

    if mood_points:
        mood_avg = sum(float(item.get("mood_score") or 0.0) for item in mood_points) / max(len(mood_points), 1)
        mood_norm = max(0.0, min(100.0, (mood_avg / 5.0) * 100.0))
        weighted_values.append((mood_norm, 45.0))

    phq = clinical.phq9_score if clinical else None
    gad = clinical.gad7_score if clinical else None
    if phq is None or gad is None:
        clinical_snapshot = dict(profile_data.get("clinical_snapshot") or {})
        phq = clinical_snapshot.get("phq9_score") if phq is None else phq
        gad = clinical_snapshot.get("gad7_score") if gad is None else gad

    if isinstance(phq, int) and isinstance(gad, int):
        clinical_inv = (1.0 - ((phq / 27.0) * 0.5 + (gad / 21.0) * 0.5)) * 100.0
        weighted_values.append((max(0.0, min(100.0, clinical_inv)), 30.0))

    stats = dict(profile_data.get("stats") or {})
    days_active = int(stats.get("days_active_last_30") or 0)
    engagement = min(days_active / 20.0, 1.0) * 100.0
    weighted_values.append((max(0.0, min(100.0, engagement)), 25.0))

    if not weighted_values:
        return 50, "Đang cập nhật"

    denominator = sum(weight for _, weight in weighted_values)
    score = int(round(sum(value * weight for value, weight in weighted_values) / denominator))
    if score >= 80:
        label = "Khởi sắc"
    elif score >= 60:
        label = "Ổn định"
    elif score >= 40:
        label = "Cần quan tâm"
    else:
        label = "Cần hỗ trợ"
    return score, label


def _build_mental_health_summary(*, db: Session, user_id: str) -> dict[str, Any]:
    mood_trend = _build_mood_trend_data(db=db, user_id=user_id, days=7)
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data = dict(profile_row.profile or {}) if profile_row else {}

    recent_summaries = list(profile_data.get("session_summaries") or [])[-10:]
    dominant_counter = Counter(
        str(item.get("dominant_emotion")).strip()
        for item in recent_summaries
        if str(item.get("dominant_emotion") or "").strip()
    )
    dominant_emotions = [
        {"emotion": emotion, "count": count}
        for emotion, count in dominant_counter.most_common(5)
    ]

    coping_history = list(profile_data.get("coping_history") or [])
    total_attempts = sum(int(item.get("tried_count") or 0) for item in coping_history)
    total_effective = sum(int(item.get("self_reported_effective") or 0) for item in coping_history)
    top_coping_items = sorted(
        (
            {
                "action": str(item.get("action") or "").strip(),
                "tried_count": int(item.get("tried_count") or 0),
            }
            for item in coping_history
            if str(item.get("action") or "").strip()
        ),
        key=lambda item: item["tried_count"],
        reverse=True,
    )[:3]

    clinical = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    score, label = _build_wellness_score(
        mood_points=list(mood_trend.get("points") or []),
        clinical=clinical,
        profile_data=profile_data,
    )
    clinical_snapshot = dict(profile_data.get("clinical_snapshot") or {})
    session_stats = dict(profile_data.get("stats") or {})
    goals = list(profile_data.get("goals") or [])[:5]

    return {
        "wellness_score": score,
        "wellness_label": label,
        "mood_trend": mood_trend,
        "dominant_emotions": dominant_emotions,
        "top_triggers": _normalize_trigger_payload(profile_data),
        "coping_stats": {
            "total_attempts": total_attempts,
            "effective_rate": round(total_effective / total_attempts, 2) if total_attempts > 0 else None,
            "top_coping": top_coping_items,
        },
        "session_stats": {
            "total_sessions": int(session_stats.get("total_sessions") or 0),
            "streak_days": int(session_stats.get("streak_days") or 0),
            "days_active_last_30": int(session_stats.get("days_active_last_30") or 0),
        },
        "clinical_snapshot": {
            "phq9_score": clinical.phq9_score if clinical else clinical_snapshot.get("phq9_score"),
            "gad7_score": clinical.gad7_score if clinical else clinical_snapshot.get("gad7_score"),
            "crisis_level": clinical.crisis_level if clinical else int(clinical_snapshot.get("crisis_level") or 0),
            "last_scored_at": _to_iso_z(clinical.last_scored_at if clinical else _parse_datetime(clinical_snapshot.get("last_scored_at"))),
        },
        "goals": goals,
        "has_enough_data": len(recent_summaries) >= 2,
    }


def _fallback_weekly_note(*, summary_payload: dict[str, Any]) -> str:
    dominant_emotions = list(summary_payload.get("dominant_emotions") or [])
    top_triggers = list(summary_payload.get("top_triggers") or [])
    emotion_hint = dominant_emotions[0]["emotion"] if dominant_emotions else "nhịp cảm xúc ổn định"
    trigger_hint = top_triggers[0]["tag"] if top_triggers else "những áp lực thường ngày"
    return (
        f"Tuần này bạn đã đi qua nhiều cung bậc cảm xúc, nổi bật là {emotion_hint}. "
        f"Serene ghi nhận {trigger_hint} là yếu tố đang tác động rõ rệt, nhưng bạn vẫn duy trì được nhịp tự chăm sóc. "
        "Hãy tiếp tục những bước nhỏ đều đặn - chúng đang tạo khác biệt tích cực."
    )


def _generate_weekly_note(*, summary_payload: dict[str, Any]) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return _fallback_weekly_note(summary_payload=summary_payload)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 4.0))
        resp = client.chat.completions.create(
            model=settings.openai_model_analyst,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là chuyên gia phân tích sức khỏe tinh thần của ứng dụng Serene. "
                        "Hãy viết một lời nhắn tuần bằng tiếng Việt, 2-3 câu, giọng ấm áp, không phán xét, "
                        "không chẩn đoán bệnh, không nêu thông tin định danh. "
                        "Nêu 1 điểm tích cực và 1 gợi ý nhẹ nhàng cho tuần tới."
                    ),
                },
                {"role": "user", "content": f"Dữ liệu người dùng tuần này: {summary_payload}"},
            ],
        )
        content = str(resp.choices[0].message.content or "").strip()
        if content:
            return content[:1000]
    except Exception:
        pass
    return _fallback_weekly_note(summary_payload=summary_payload)


def _upsert_weekly_note_meta(
    *,
    db: Session,
    user_id: str,
    content: str,
    generated_at: datetime,
) -> None:
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile_row is None:
        profile_row = UserProfile(user_id=user_id, profile={})
        db.add(profile_row)
        db.flush()

    profile_data = dict(profile_row.profile or {})
    meta = dict(profile_data.get("meta") or {})
    meta["pii_masked"] = bool(meta.get("pii_masked", True))
    meta["weekly_note_content"] = content
    meta["weekly_note_generated_at"] = _to_iso_z(generated_at)
    profile_data["meta"] = meta
    profile_row.profile = profile_data
    profile_row.updated_at = generated_at.replace(tzinfo=None)
    db.commit()


@router.get("/mood-trend")
def mood_trend(
    days: int = Query(default=7),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    if days < 1 or days > 90:
        raise AppError("INVALID_PARAMETER", "days phải trong khoảng 1-90", 400)

    return ok(_build_mood_trend_data(db=db, user_id=current_user.user_id, days=days))


@router.get("/mental-health-summary")
def mental_health_summary(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    return ok(_build_mental_health_summary(db=db, user_id=current_user.user_id))


@router.get("/weekly-note")
def weekly_note(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    now = utc_now()
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile_data = dict(profile_row.profile or {}) if profile_row else {}
    meta = dict(profile_data.get("meta") or {})
    cached_content = str(meta.get("weekly_note_content") or "").strip()
    cached_generated_at = _parse_datetime(meta.get("weekly_note_generated_at"))
    if cached_content and cached_generated_at and now - cached_generated_at < timedelta(days=WEEKLY_NOTE_CACHE_DAYS):
        return ok(
            {
                "week_of": local_date_utc7().isoformat(),
                "content": cached_content,
                "generated_at": _to_iso_z(cached_generated_at),
                "is_cached": True,
            }
        )

    summary_payload = _build_mental_health_summary(db=db, user_id=current_user.user_id)
    content = _generate_weekly_note(summary_payload=summary_payload)
    _upsert_weekly_note_meta(
        db=db,
        user_id=current_user.user_id,
        content=content,
        generated_at=now,
    )

    return ok(
        {
            "week_of": local_date_utc7().isoformat(),
            "content": content,
            "generated_at": _to_iso_z(now),
            "is_cached": False,
        }
    )


@router.post("/refresh-insight")
def refresh_insight(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    now = utc_now()
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile_data = dict(profile_row.profile or {}) if profile_row else {}
    meta = dict(profile_data.get("meta") or {})
    cached_generated_at = _parse_datetime(meta.get("weekly_note_generated_at"))
    if cached_generated_at and now - cached_generated_at < timedelta(hours=WEEKLY_NOTE_REFRESH_COOLDOWN_HOURS):
        remaining = timedelta(hours=WEEKLY_NOTE_REFRESH_COOLDOWN_HOURS) - (now - cached_generated_at)
        remaining_minutes = max(int(remaining.total_seconds() // 60), 1)
        raise AppError(
            "REFRESH_COOLDOWN",
            f"Bạn vừa làm mới insight gần đây. Vui lòng thử lại sau khoảng {remaining_minutes} phút.",
            429,
        )

    summary_payload = _build_mental_health_summary(db=db, user_id=current_user.user_id)
    content = _generate_weekly_note(summary_payload=summary_payload)
    _upsert_weekly_note_meta(
        db=db,
        user_id=current_user.user_id,
        content=content,
        generated_at=now,
    )
    return ok(
        {
            "week_of": local_date_utc7().isoformat(),
            "content": content,
            "generated_at": _to_iso_z(now),
            "is_cached": False,
        }
    )


@router.post("/journal")
def create_journal(payload: JournalCreateRequest, current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    if payload.prompt_id:
        prompt = db.scalar(
            select(JournalPrompt).where(
                JournalPrompt.prompt_id == payload.prompt_id,
                JournalPrompt.is_active.is_(True),
            )
        )
        if not prompt:
            raise AppError("INVALID_PARAMETER", "prompt_id không hợp lệ", 400)

    row = JournalEntry(
        journal_id=make_id("j"),
        user_id=current_user.user_id,
        prompt_id=payload.prompt_id,
        content=payload.content,
    )
    db.add(row)
    db.commit()
    return ok({"journal_id": row.journal_id, "created_at": row.created_at.isoformat() + "Z"}, status_code=201)


@router.get("/journals")
def list_journals(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    total = (
        db.scalar(
            select(func.count(JournalEntry.journal_id)).where(
                JournalEntry.user_id == current_user.user_id,
                JournalEntry.deleted_at.is_(None),
            )
        )
        or 0
    )

    rows = db.scalars(
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.user_id, JournalEntry.deleted_at.is_(None))
        .order_by(JournalEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    journals = [
        {
            "journal_id": row.journal_id,
            "content_preview": (row.content[:57] + "...") if len(row.content) > 60 else row.content,
            "prompt_id": row.prompt_id,
            "created_at": row.created_at.isoformat() + "Z",
        }
        for row in rows
    ]

    return ok({"journals": journals, "total": total, "has_more": offset + len(journals) < total})


@router.get("/journal-prompts")
def journal_prompts(db: Session = Depends(get_db)):
    prompts = db.scalars(
        select(JournalPrompt)
        .where(JournalPrompt.is_active.is_(True))
        .order_by(JournalPrompt.created_at.asc())
    ).all()

    return ok(
        {
            "prompts": [{"id": row.prompt_id, "text": row.text} for row in prompts]
            if prompts
            else [
                {"id": "prompt_01", "text": "Hôm nay điều gì khiến bạn cảm thấy tự hào về bản thân?"},
                {"id": "prompt_02", "text": "Điều gì đang chiếm nhiều năng lượng nhất của bạn tuần này?"},
                {"id": "prompt_03", "text": "Nếu nói chuyện với bản thân 1 năm trước, bạn sẽ nói gì?"},
            ]
        }
    )
