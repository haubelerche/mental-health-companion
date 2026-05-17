import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.hearts.service import grant_hearts, get_balance
from app.hearts.streaks import update_mood_streak
from app.services.db.models import MoodCheckin, SleepCheckin, User
from app.services.db.session import get_db
from app.services.schemas.payloads import CheckinQuickRequest
from app.services.utils import local_date_utc7, make_id, get_now, VN_TZ

router = APIRouter(prefix="/checkin", tags=["checkin"])

_MOOD_CHECKIN_HEARTS = 10


def _compute_time_bucket() -> str:
    hour = get_now().hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "other"


def _time_on_date(base_date, value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        hour_s, minute_s = value.split(":", 1)
        hour = int(hour_s)
        minute = int(minute_s)
    except (TypeError, ValueError):
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)


def _upsert_sleep_checkin(
    db: Session,
    *,
    user_id: str,
    logged_date,
    sleep_start: str | None,
    wake_time: str | None,
    duration_hours: float | None,
    sleep_quality: int | None,
    note: str | None,
) -> None:
    if not sleep_start and not wake_time and duration_hours is None and sleep_quality is None:
        return
    sleep_date = logged_date
    bedtime_at = _time_on_date(logged_date, sleep_start)
    wake_time_at = _time_on_date(logged_date, wake_time)
    if bedtime_at and wake_time_at and bedtime_at > wake_time_at:
        bedtime_at = bedtime_at - timedelta(days=1)
        sleep_date = bedtime_at.date()
    if duration_hours is None and bedtime_at and wake_time_at:
        duration_hours = round((wake_time_at - bedtime_at).total_seconds() / 3600, 2)
    if duration_hours is not None and not (0 < float(duration_hours) <= 16):
        duration_hours = None

    existing = db.scalar(
        select(SleepCheckin).where(
            SleepCheckin.user_id == user_id,
            SleepCheckin.sleep_date == sleep_date,
        )
    )
    now = get_now().replace(tzinfo=None)
    if existing is None:
        existing = SleepCheckin(
            sleep_id=make_id("slp"),
            user_id=user_id,
            sleep_date=sleep_date,
            source="self_report",
        )
        db.add(existing)
    existing.bedtime_at = bedtime_at
    existing.wake_time_at = wake_time_at
    existing.duration_hours = duration_hours
    existing.sleep_quality = sleep_quality
    existing.note = note
    existing.updated_at = now


@router.post("/quick")
def checkin_quick(
    payload: CheckinQuickRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    logged_date = local_date_utc7()
    user_id = current_user.user_id
    time_bucket = payload.time_bucket or _compute_time_bucket()
    existing = db.scalar(
        select(MoodCheckin).where(
            MoodCheckin.user_id == user_id,
            MoodCheckin.logged_date == logged_date,
            MoodCheckin.time_bucket == time_bucket,
        )
    )
    prior_same_day = (
        db.scalar(
            select(func.count())
            .select_from(MoodCheckin)
            .where(MoodCheckin.user_id == user_id, MoodCheckin.logged_date == logged_date)
        )
        or 0
    )
    extra = {
        "stress_level": payload.stress_level,
        "sleep_hours": payload.sleep_hours,
        "sleep_start": payload.sleep_start,
        "wake_time": payload.wake_time,
        "sleep_quality": payload.sleep_quality,
        "study_hours": payload.study_hours,
        "emotions": payload.emotions,
        "triggers": payload.triggers,
    }
    note_blob = json.dumps({"extra": extra, "note": payload.note}, ensure_ascii=False)

    if existing:
        existing.mood = payload.mood
        existing.emotions = payload.emotions
        existing.triggers = payload.triggers
        existing.note = note_blob[:10000]
        existing.updated_at = get_now().replace(tzinfo=None)
        _upsert_sleep_checkin(
            db,
            user_id=user_id,
            logged_date=logged_date,
            sleep_start=payload.sleep_start,
            wake_time=payload.wake_time,
            duration_hours=payload.sleep_hours,
            sleep_quality=payload.sleep_quality,
            note=payload.note,
        )
        streak_result = update_mood_streak(db, user_id=current_user.user_id, checkin_date=logged_date)
        db.commit()
        return ok({
            "checkin_id": existing.checkin_id,
            "updated": True,
            "reward": {
                "granted": False,
                "amount": 0,
                "reason": "already_claimed_today",
                "new_balance": get_balance(db, current_user.user_id)
            },
            "streak": streak_result,
        })

    row = MoodCheckin(
        checkin_id=make_id("mc"),
        user_id=user_id,
        mood=payload.mood,
        emoji=None,
        emotions=payload.emotions,
        triggers=payload.triggers,
        note=note_blob[:10000],
        logged_date=logged_date,
        logged_at=get_now().replace(tzinfo=None),
        time_bucket=time_bucket,
    )
    db.add(row)
    db.flush()
    _upsert_sleep_checkin(
        db,
        user_id=user_id,
        logged_date=logged_date,
        sleep_start=payload.sleep_start,
        wake_time=payload.wake_time,
        duration_hours=payload.sleep_hours,
        sleep_quality=payload.sleep_quality,
        note=payload.note,
    )

    idem_key = f"mood_checkin:{user_id}:{logged_date.isoformat()}"
    first_checkin_today = prior_same_day == 0
    reward_result = (
        grant_hearts(
            db,
            user_id=user_id,
            amount=_MOOD_CHECKIN_HEARTS,
            event_type="daily_mood_checkin_completed",
            source_tab="checkin",
            idempotency_key=idem_key,
            metadata={"mood": payload.mood, "logged_date": logged_date.isoformat()},
        )
        if first_checkin_today
        else {
            "granted": False,
            "amount": 0,
            "new_balance": get_balance(db, user_id),
        }
    )
    streak_result = update_mood_streak(db, user_id=user_id, checkin_date=logged_date)
    db.commit()
    return ok(
        {
            "checkin_id": row.checkin_id,
            "logged_at": row.logged_at.isoformat() + "Z",
            "summary": "Đã ghi nhận check-in nhanh.",
            "reward": {
                "granted": reward_result["granted"],
                "amount": reward_result.get("amount", 0),
                "reason": "daily_mood_checkin_completed",
                "balance": reward_result.get("new_balance", 0),
            },
            "streak": {
                "current": streak_result["current"],
                "bonus_granted": streak_result["bonus_granted"],
                "bonus_amount": streak_result["bonus_amount"],
            },
        },
        status_code=201,
    )
