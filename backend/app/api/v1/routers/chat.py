from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import Conversation, Message, User
from app.db.session import get_db
from app.schemas.payloads import ChatMessageRequest
from app.services.rate_limit import get_rate_limiter
from app.services.utils import make_id, utc_now

router = APIRouter(prefix="/chat", tags=["chat"])

SOS_KEYWORDS = ["khong muon tiep tuc", "muon chet", "tu tu", "khong muon song", "khong muốn tiếp tục"]


def _is_sos(message: str) -> bool:
    lowered = message.lower()
    return any(key in lowered for key in SOS_KEYWORDS)


@router.post("/message")
def send_message(payload: ChatMessageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    limiter = get_rate_limiter()
    limiter.enforce_per_minute(
        key=f"chat:{current_user.user_id}",
        limit=settings.chat_rate_limit_per_minute,
        code="RATE_LIMIT_EXCEEDED",
        message="Bạn đã vượt quá giới hạn chat mỗi phút",
    )

    now = utc_now().replace(tzinfo=None)
    session = None
    if payload.session_id:
        session = db.scalar(
            select(Conversation).where(
                Conversation.session_id == payload.session_id,
                Conversation.user_id == current_user.user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if not session:
            raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)
    else:
        session = Conversation(
            session_id=make_id("sess"),
            user_id=current_user.user_id,
            message_count=0,
            started_at=now,
            last_message_at=now,
        )
        db.add(session)
        db.flush()

    user_msg = Message(
        message_id=make_id("msg"),
        session_id=session.session_id,
        user_id=current_user.user_id,
        role="user",
        content=payload.message,
        created_at=now,
    )
    db.add(user_msg)

    sos = _is_sos(payload.message)
    if sos:
        assistant_content = "Mình thấy bạn đang rất khó khăn. Bạn không đơn độc, hãy gọi 1800-599-920 để được hỗ trợ ngay."
    else:
        assistant_content = "Mình nghe bạn rồi. Cảm ơn bạn đã chia sẻ, mình ở đây để đồng hành cùng bạn."

    assistant_msg = Message(
        message_id=make_id("msg"),
        session_id=session.session_id,
        user_id=current_user.user_id,
        role="assistant",
        content=assistant_content,
        tone_cam_xuc="xac_nhan" if not sos else None,
        sos_triggered=sos,
        created_at=now,
    )
    db.add(assistant_msg)

    session.message_count += 2
    session.last_message_at = now
    db.commit()

    if sos:
        return ok(
            {
                "session_id": session.session_id,
                "reply": None,
                "sos_triggered": True,
                "sos_card": {
                    "muc_do": "cao",
                    "message": "Mình thấy bạn đang trải qua điều rất nặng nề. Bạn không phải một mình.",
                    "hotline": {
                        "name": "Đường dây hỗ trợ sức khỏe tâm thần",
                        "number": "1800-599-920",
                        "available": "24/7",
                    },
                    "bai_tap_grounding": {
                        "id": "ground_54321",
                        "title": "Kỹ thuật 5-4-3-2-1",
                        "instruction": "Nhìn quanh và tìm 5 thứ bạn thấy, 4 thứ bạn chạm được...",
                    },
                    "suggest_clinic": True,
                },
            }
        )

    return ok(
        {
            "session_id": session.session_id,
            "reply": assistant_content,
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": ["Kể thêm đi", "Mình nên làm gì bây giờ?", "Chỉ cần lắng nghe thôi"],
            "the_dinh_kem": [
                {"type": "breathing_exercise", "id": "breath_478", "title": "Thở 4-7-8 - Giảm căng thẳng"}
            ],
            "sos_triggered": False,
        }
    )


@router.get("/sessions")
def get_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == current_user.user_id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.last_message_at.desc())
    ).all()

    sessions = []
    for row in rows:
        preview = db.scalar(
            select(Message.content)
            .where(Message.session_id == row.session_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        sessions.append(
            {
                "session_id": row.session_id,
                "last_message_at": row.last_message_at.isoformat() + "Z",
                "preview": preview,
            }
        )

    return ok({"sessions": sessions})


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not session:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)

    total = db.scalar(select(func.count(Message.message_id)).where(Message.session_id == session_id)) or 0
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    messages = [
        {
            "message_id": m.message_id,
            "role": m.role,
            "content": m.content,
            "tone_cam_xuc": m.tone_cam_xuc,
            "the_dinh_kem": [],
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in rows
    ]

    return ok(
        {
            "session_id": session_id,
            "messages": messages,
            "total": total,
            "has_more": offset + len(messages) < total,
        }
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    hard: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not session:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)

    now = utc_now().replace(tzinfo=None)
    session.deleted_at = now
    if hard:
        session.hard_deleted_at = now
        session.anonymous_summary = None
    else:
        session.hard_deleted_at = now + timedelta(days=90)
        session.anonymous_summary = {
            "turn_count": session.message_count,
            "dominant_tone": "xac_nhan",
            "had_sos": False,
        }

    db.commit()
    return ok(
        {
            "deleted_at": session.deleted_at.isoformat() + "Z",
            "hard_delete_at": session.hard_deleted_at.isoformat() + "Z",
        }
    )
