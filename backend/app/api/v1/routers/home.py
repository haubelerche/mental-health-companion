from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import Conversation, MoodCheckin, User
from app.services.db.session import get_db
from app.services.schemas.payloads import MoodCheckinPatchRequest, MoodCheckinRequest
from app.services.utils import local_date_utc7, make_id, utc_now

router = APIRouter(tags=["home"])


@router.post("/mood/checkin")
def create_checkin(payload: MoodCheckinRequest, current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    logged_date = local_date_utc7()
    existing = db.scalar(
        select(MoodCheckin).where(
            MoodCheckin.user_id == current_user.user_id,
            MoodCheckin.logged_date == logged_date,
        )
    )
    if existing:
        raise AppError("MOOD_ALREADY_LOGGED", "Bạn đã checkin hôm nay", 409)

    row = MoodCheckin(
        checkin_id=make_id("mc"),
        user_id=current_user.user_id,
        mood=payload.mood,
        emoji=payload.emoji,
        note=payload.note,
        logged_date=logged_date,
        logged_at=utc_now().replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    return ok({"checkin_id": row.checkin_id, "logged_at": row.logged_at.isoformat() + "Z"}, status_code=201)


@router.patch("/mood/checkin/{checkin_id}")
def patch_checkin(
    checkin_id: str,
    payload: MoodCheckinPatchRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(MoodCheckin).where(MoodCheckin.checkin_id == checkin_id, MoodCheckin.user_id == current_user.user_id)
    )
    if not row:
        raise AppError("CHECKIN_NOT_FOUND", "Checkin không tồn tại", 404)

    if row.logged_date != local_date_utc7():
        raise AppError("CHECKIN_NOT_EDITABLE", "Chỉ sửa được checkin hôm nay", 409)

    if payload.mood is not None:
        row.mood = payload.mood
    if payload.emoji is not None:
        row.emoji = payload.emoji
    row.note = payload.note
    row.updated_at = utc_now().replace(tzinfo=None)
    db.commit()
    return ok({"updated_at": row.updated_at.isoformat() + "Z"})


@router.get("/home/feed")
def home_feed(current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    today = local_date_utc7()
    mood = db.scalar(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == current_user.user_id, MoodCheckin.logged_date == today)
        .order_by(MoodCheckin.logged_at.desc())
    )
    last_session = db.scalar(
        select(Conversation)
        .where(Conversation.user_id == current_user.user_id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.last_message_at.desc())
    )

    session_data = None
    if last_session:
        session_data = {
            "session_id": last_session.session_id,
            "preview": "Tiếp tục cuộc trò chuyện gần nhất",
            "last_message_at": last_session.last_message_at.isoformat() + "Z",
        }

    return ok(
        {
            "quote_of_day": {
                "text": "Bạn không cần phải hoàn hảo để xứng đáng được yêu thương.",
                "author": "Brene Brown",
            },
            "suggested_meditation": {
                "id": "med_01",
                "title": "Bắt đầu tập trung",
                "duration_sec": 300,
                "thumbnail": "https://cdn.example.com/thumb/med_01.jpg",
            },
            "last_session": session_data,
            "dynamic_suggestion": {
                "type": "sleep",
                "reason": "late_night",
                "message": "Đã khuya rồi, thử bài thở ngủ ngon nhé?",
            },
            "mood_today": {
                "checked_in": mood is not None,
                "mood": mood.mood if mood else None,
                "emoji": mood.emoji if mood else None,
            },
        }
    )
