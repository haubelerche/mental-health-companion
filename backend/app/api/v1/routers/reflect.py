from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import JournalEntry, JournalPrompt, MoodCheckin, User
from app.db.session import get_db
from app.schemas.payloads import JournalCreateRequest
from app.services.utils import local_date_utc7, make_id, utc_now

router = APIRouter(prefix="/reflect", tags=["reflect"])

MOOD_TO_SCORE = {
    "stressful": (1, "khó khăn"),
    "sad": (2, "buồn"),
    "neutral": (3, "ổn"),
    "peaceful": (4, "tốt"),
    "delightful": (5, "rất tốt"),
}


@router.get("/mood-trend")
def mood_trend(
    days: int = Query(default=7),
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    if days < 1 or days > 90:
        raise AppError("INVALID_PARAMETER", "days phải trong khoảng 1-90", 400)

    today = local_date_utc7()
    start = today - timedelta(days=days - 1)
    rows = db.scalars(
        select(MoodCheckin)
        .where(
            MoodCheckin.user_id == current_user.user_id,
            MoodCheckin.logged_date >= start,
            MoodCheckin.logged_date <= today,
        )
        .order_by(MoodCheckin.logged_date.asc())
    ).all()

    point_map = {row.logged_date: row for row in rows}
    points = []
    missing = []
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

    return ok(
        {
            "period": {"from": start.isoformat(), "to": today.isoformat()},
            "points": points,
            "days_missing": missing,
            "summary": "Tuần này bạn có xu hướng ổn định hơn." if points else "Chưa có đủ dữ liệu mood.",
        }
    )


@router.get("/weekly-note")
def weekly_note(current_user: User = Depends(ensure_policy_acknowledged)):
    _ = current_user
    return ok(
        {
            "week_of": local_date_utc7().isoformat(),
            "content": "Tuần này bạn đã nỗ lực rất nhiều. Hãy tiếp tục giữ nhịp nghỉ ngơi.",
            "generated_at": utc_now().isoformat().replace("+00:00", "Z"),
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
