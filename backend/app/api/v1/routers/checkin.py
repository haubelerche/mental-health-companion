import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.hearts.service import grant_hearts, get_balance
from app.hearts.streaks import update_mood_streak
from app.services.db.models import MoodCheckin, User
from app.services.db.session import get_db
from app.services.schemas.payloads import CheckinQuickRequest
from app.services.utils import local_date_utc7, make_id, utc_now

router = APIRouter(prefix="/checkin", tags=["checkin"])

_MOOD_CHECKIN_HEARTS = 10


@router.post("/quick")
def checkin_quick(
    payload: CheckinQuickRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    logged_date = local_date_utc7()
    user_id = current_user.user_id
    existing = db.scalar(
        select(MoodCheckin).where(
            MoodCheckin.user_id == user_id,
            MoodCheckin.logged_date == logged_date,
        )
    )
    extra = {
        "stress_level": payload.stress_level,
        "sleep_hours": payload.sleep_hours,
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
        existing.updated_at = utc_now().replace(tzinfo=None)
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
        logged_at=utc_now().replace(tzinfo=None),
    )
    db.add(row)
    db.flush()

    idem_key = f"mood_checkin:{user_id}:{logged_date.isoformat()}"
    reward_result = grant_hearts(
        db,
        user_id=user_id,
        amount=_MOOD_CHECKIN_HEARTS,
        event_type="daily_mood_checkin_completed",
        source_tab="checkin",
        idempotency_key=idem_key,
        metadata={"mood": payload.mood, "logged_date": logged_date.isoformat()},
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
