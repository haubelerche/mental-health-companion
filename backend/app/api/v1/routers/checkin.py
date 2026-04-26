import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.db.models import MoodCheckin, User
from app.db.session import get_db
from app.schemas.payloads import CheckinQuickRequest
from app.services.utils import local_date_utc7, make_id, utc_now

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("/quick")
def checkin_quick(
    payload: CheckinQuickRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    logged_date = local_date_utc7()
    existing = db.scalar(
        select(MoodCheckin).where(
            MoodCheckin.user_id == current_user.user_id,
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
        db.commit()
        return ok({"checkin_id": existing.checkin_id, "updated": True})

    row = MoodCheckin(
        checkin_id=make_id("mc"),
        user_id=current_user.user_id,
        mood=payload.mood,
        emoji=None,
        emotions=payload.emotions,
        triggers=payload.triggers,
        note=note_blob[:10000],
        logged_date=logged_date,
        logged_at=utc_now().replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    return ok({"checkin_id": row.checkin_id, "logged_at": row.logged_at.isoformat() + "Z", "summary": "Đã ghi nhận check-in nhanh."}, status_code=201)
