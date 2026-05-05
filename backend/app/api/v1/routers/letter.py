from datetime import date, datetime, timezone
import random

from fastapi import APIRouter, Depends
from sqlalchemy import exists, func, select, or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import TherapyLetter, SyncOutbox, User
from app.services.db.session import get_db
from app.services.schemas.payloads import LetterReactRequest, LetterReplyRequest, LetterReportRequest, LetterSendRequest
from app.services.utils import make_anon_name, make_id

router = APIRouter(tags=["letters"])


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def can_send_letter(db: Session, user_id: str) -> bool:
    today = date.today()
    count = (
        db.query(func.count(TherapyLetter.letter_id))
        .filter(
            TherapyLetter.user_id == user_id, 
            TherapyLetter.letter_type == "public",
            func.date(TherapyLetter.created_at) == today
        )
        .scalar()
    ) or 0
    return count < 5


def can_receive(db: Session, user_id: str) -> bool:
    today = date.today()
    count = (
        db.query(func.count(TherapyLetter.letter_id))
        .filter(
            TherapyLetter.receiver_id == user_id, 
            func.date(TherapyLetter.created_at) == today
        )
        .scalar()
    ) or 0
    return count < 5


def _reply_summary(db: Session, letter: TherapyLetter, *, replier_id: str | None = None) -> dict | None:
    query = db.query(TherapyLetter).filter(
        TherapyLetter.reply_to_id == letter.letter_id,
        TherapyLetter.letter_type == "reply"
    )
    if replier_id:
        query = query.filter(TherapyLetter.user_id == replier_id)

    reply = query.first()
    if not reply:
        return None

    return {
        "reply_id": reply.letter_id,
        "content": reply.content,
        "anonymous_name": reply.anonymous_name,
        "replier_id": reply.user_id,
        "received_at": reply.created_at.isoformat() + "Z",
        "reaction_type": reply.reaction_type,
        "has_reaction": reply.reaction_type is not None,
    }


def _replied_archive_item(db: Session, reply: TherapyLetter) -> dict:
    letter = db.get(TherapyLetter, reply.reply_to_id) if reply.reply_to_id else None
    return {
        "reply_id": reply.letter_id,
        "letter_id": reply.reply_to_id,
        "content": reply.content,
        "anonymous_name": reply.anonymous_name,
        "original_content": letter.content if letter else None,
        "sent_at": reply.created_at.isoformat() + "Z",
        "reaction_type": reply.reaction_type,
        "has_reaction": reply.reaction_type is not None,
    }


def _pick_receiver(
    db: Session,
    *,
    sender_id: str,
    letter_id: str | None = None,
    excluded_user_ids: set[str] | None = None,
) -> str | None:
    excluded = {sender_id}
    if excluded_user_ids:
        excluded.update(uid for uid in excluded_user_ids if uid)

    # Find users who haven't interacted with this letter yet
    used_user_ids: set[str] = set()
    if letter_id:
        # Get anyone who was a sender or receiver of this letter or its replies
        senders = db.query(TherapyLetter.user_id).filter(
            or_(TherapyLetter.letter_id == letter_id, TherapyLetter.reply_to_id == letter_id)
        ).all()
        receivers = db.query(TherapyLetter.receiver_id).filter(TherapyLetter.letter_id == letter_id).all()
        used_user_ids.update(u[0] for u in senders if u[0])
        used_user_ids.update(u[0] for u in receivers if u[0])

    users = (
        db.query(User.user_id)
        .filter(
            User.is_active.is_(True),
            User.policy_acknowledged_at.is_not(None),
            ~User.user_id.in_(list(excluded | used_user_ids)),
        )
        .all()
    )

    candidates = sorted([u[0] for u in users if can_receive(db, u[0])])
    if not candidates:
        return None

    return random.choice(candidates)


def _notify_sender_reported(db: Session, sender_id: str, *, letter_id: str, message: str = "Lá thư của bạn đã bị báo cáo") -> None:
    from app.services.notification_service import enqueue_notification
    enqueue_notification(
        db,
        user_id=sender_id,
        event_type="letter.reported",
        payload={
            "letter_id": letter_id,
            "message": message,
        }
    )


def _notify_sender_replied(db: Session, sender_id: str, *, letter_id: str, reply_id: str, replier_id: str) -> None:
    from app.services.notification_service import enqueue_notification
    enqueue_notification(
        db,
        user_id=sender_id,
        event_type="letter.replied",
        payload={
            "letter_id": letter_id,
            "reply_id": reply_id,
            "replier_id": replier_id,
            "message": "Bạn có một phản hồi thư mới!",
        }
    )


def _notify_receiver_letter_received(db: Session, receiver_id: str, *, letter_id: str, sender_id: str) -> None:
    from app.services.notification_service import enqueue_notification
    enqueue_notification(
        db,
        user_id=receiver_id,
        event_type="letter.received",
        payload={
            "letter_id": letter_id,
            "sender_id": sender_id,
            "message": "Bạn vừa nhận được một lá thư ẩn danh mới",
        }
    )


def _notify_replier_reaction(db: Session, replier_id: str, *, reply_id: str, letter_id: str, reaction_type: str) -> None:
    from app.services.notification_service import enqueue_notification
    enqueue_notification(
        db,
        user_id=replier_id,
        event_type="letter.reacted",
        payload={
            "reply_id": reply_id,
            "letter_id": letter_id,
            "reaction_type": reaction_type,
            "message": "Ai đó vừa thả tim vào phản hồi của bạn!",
        }
    )


@router.post("/letters")
def send_letter(
    payload: LetterSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    if not can_send_letter(db, current_user.user_id):
        raise AppError("LETTER_SEND_DAILY_LIMIT",
                       "Bạn đã gửi tối đa 5 thư hôm nay", 400)

    receiver_id = _pick_receiver(db, sender_id=current_user.user_id)
    if receiver_id is None:
        raise AppError("LETTER_NO_RECEIVER",
                       "Hiện chưa có người nhận phù hợp", 400)

    letter = TherapyLetter(
        letter_id=make_id("let"),
        user_id=current_user.user_id,
        receiver_id=receiver_id,
        content=payload.content,
        letter_type="public",
        status="active",
        created_at=_utc_naive_now(),
    )
    db.add(letter)
    _notify_receiver_letter_received(db, receiver_id, letter_id=letter.letter_id, sender_id=current_user.user_id)
    db.commit()

    return ok(
        {
            "letter_id": letter.letter_id,
            "receiver_id": receiver_id,
            "forward_count": letter.forward_count,
            "has_reply": False,
            "is_reported": False,
        },
        status_code=201,
    )


@router.get("/letters/inbox")
def get_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    # Get letters where current user is the receiver and no reply exists yet.
    reply = aliased(TherapyLetter)
    letters = (
        db.query(TherapyLetter)
        .filter(
            TherapyLetter.receiver_id == current_user.user_id,
            TherapyLetter.letter_type == "public",
            TherapyLetter.status == "active",
            ~exists().where(
                reply.reply_to_id == TherapyLetter.letter_id,
            ),
        )
        .order_by(TherapyLetter.created_at.desc())
        .all()
    )

    items = []
    for letter in letters:
        items.append(
            {
                "letter_id": letter.letter_id,
                "content": letter.content,
                "sender_id": letter.user_id,
                "forward_count": letter.forward_count,
                "has_reply": False,
                "is_reported": False,
                "received_at": letter.created_at.isoformat() + "Z",
                "status": "received",
            }
        )

    return ok({"letters": items, "total": len(items), "has_more": False})


@router.get("/letters/sent")
def get_sent_letters(
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    # 1. Original letters sent by user
    rows = (
        db.query(TherapyLetter)
        .filter(
            TherapyLetter.user_id == current_user.user_id,
            TherapyLetter.letter_type == "public"
        )
        .order_by(TherapyLetter.created_at.desc())
        .all()
    )

    items = []
    for letter in rows:
        reply = _reply_summary(db, letter)
        items.append(
            {
                "letter_id": letter.letter_id,
                "content": letter.content,
                "sent_at": letter.created_at.isoformat() + "Z",
                "forward_count": letter.forward_count,
                "has_reply": reply is not None,
                "is_reported": letter.status == "reported",
                "reply": reply,
            }
        )

    # 2. Replies sent by user
    replied_rows = (
        db.query(TherapyLetter)
        .filter(
            TherapyLetter.user_id == current_user.user_id,
            TherapyLetter.letter_type == "reply"
        )
        .order_by(TherapyLetter.created_at.desc())
        .all()
    )
    replied_items = [_replied_archive_item(db, r) for r in replied_rows]

    return ok({"letters": items, "reply_letters": replied_items, "total": len(items) + len(replied_items), "has_more": False})


@router.post("/letters/{letter_id}/forward")
def forward_letter(
    letter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letter = db.get(TherapyLetter, letter_id)
    if not letter or letter.letter_type != "public":
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    if letter.forward_count >= 3:
        raise AppError("FORWARD_LIMIT_REACHED",
                       "Thư đã đạt giới hạn chuyển tiếp", 400)

    if letter.receiver_id != current_user.user_id:
        raise AppError("LETTER_FORWARD_NOT_ALLOWED",
                       "Bạn không được chuyển tiếp thư này", 403)

    new_receiver = _pick_receiver(
        db,
        sender_id=letter.user_id,
        letter_id=letter_id,
        excluded_user_ids={current_user.user_id},
    )
    if new_receiver is None:
        raise AppError("LETTER_NO_RECEIVER",
                       "Hiện chưa có người nhận phù hợp", 400)

    letter.forward_count += 1
    letter.receiver_id = new_receiver
    letter.updated_at = _utc_naive_now()
    
    db.add(letter)
    _notify_receiver_letter_received(db, new_receiver, letter_id=letter.letter_id, sender_id=letter.user_id)
    db.commit()

    return ok(
        {
            "letter_id": letter.letter_id,
            "forward_count": letter.forward_count,
            "to_user_id": new_receiver,
            "action": "forwarded",
        }
    )


@router.post("/letters/{letter_id}/reply")
def reply_letter(
    letter_id: str,
    payload: LetterReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letter = db.get(TherapyLetter, letter_id)
    if not letter or letter.letter_type != "public":
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    # Check if already replied to this specific letter
    existing_reply = db.query(TherapyLetter).filter(
        TherapyLetter.reply_to_id == letter_id,
        TherapyLetter.letter_type == "reply"
    ).first()
    
    if existing_reply:
        raise AppError("ALREADY_REPLIED", "Thư đã được phản hồi", 400)

    if letter.receiver_id != current_user.user_id:
        raise AppError("LETTER_REPLY_NOT_ALLOWED",
                       "Bạn không được phản hồi thư này", 403)

    reply = TherapyLetter(
        letter_id=make_id("lrep"),
        user_id=current_user.user_id,
        reply_to_id=letter.letter_id,
        anonymous_name=make_anon_name(),
        content=payload.content,
        letter_type="reply",
        status="active",
        created_at=_utc_naive_now(),
    )
    
    # Mark letter as handled (remove receiver so it's no longer in inbox)
    letter.receiver_id = None 
    
    db.add(reply)
    db.add(letter)
    
    _notify_sender_replied(db, letter.user_id, letter_id=letter.letter_id,
                           reply_id=reply.letter_id, replier_id=current_user.user_id)
    db.commit()

    return ok(
        {
            "reply_id": reply.letter_id,
            "letter_id": letter.letter_id,
            "replier_id": current_user.user_id,
            "action": "replied",
        },
        status_code=201,
    )


@router.post("/replies/{reply_id}/react")
def react_reply(
    reply_id: str,
    payload: LetterReactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    reply = db.get(TherapyLetter, reply_id)
    if not reply or reply.letter_type != "reply":
        raise AppError("REPLY_NOT_FOUND", "Không tìm thấy phản hồi", 404)

    original_letter = db.get(TherapyLetter, reply.reply_to_id)
    if not original_letter or original_letter.user_id != current_user.user_id:
        raise AppError("LETTER_REACT_NOT_ALLOWED",
                       "Chỉ người gửi thư mới được thả cảm xúc", 403)

    if reply.reaction_type:
        raise AppError("ALREADY_REACTED",
                       "Bạn đã thả cảm xúc cho phản hồi này", 400)

    reply.reaction_type = payload.reaction_type
    reply.updated_at = _utc_naive_now()
    
    db.add(reply)
    _notify_replier_reaction(db, reply.user_id, reply_id=reply_id, letter_id=original_letter.letter_id, reaction_type=payload.reaction_type)
    db.commit()

    return ok(
        {
            "reaction_id": f"react_{reply_id}",
            "reply_id": reply_id,
            "reaction_type": reply.reaction_type,
        },
        status_code=201,
    )


@router.post("/reports")
def report_letter(
    payload: LetterReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letter = db.get(TherapyLetter, payload.letter_id)
    if not letter:
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    report_category = payload.report_category.strip().lower()
    allowed_categories = {"spam", "abuse", "inappropriate", "self_harm", "other"}
    if report_category not in allowed_categories:
        raise AppError("INVALID_REPORT_CATEGORY", "Danh mục báo cáo không hợp lệ", 400)

    # Simple check: was it the sender or the current receiver?
    if current_user.user_id != letter.user_id and current_user.user_id != letter.receiver_id:
        raise AppError("LETTER_REPORT_NOT_ALLOWED", "Bạn không được báo cáo thư này", 403)

    if letter.report_data and current_user.user_id in letter.report_data.get("reporters", []):
        raise AppError("ALREADY_REPORTED", "Bạn đã báo cáo thư này trước đó", 400)

    # Update report data
    report_info = letter.report_data or {"reporters": [], "details": []}
    report_info["reporters"].append(current_user.user_id)
    report_info["details"].append({
        "reporter_id": current_user.user_id,
        "category": report_category,
        "reason": payload.reason or payload.description,
        "at": _utc_naive_now().isoformat()
    })
    
    letter.report_data = report_info
    letter.status = "reported"
    
    db.add(letter)
    _notify_sender_reported(db, letter.user_id, letter_id=letter.letter_id)
    db.commit()

    return ok(
        {
            "report_id": f"rep_{letter.letter_id}_{len(report_info['reporters'])}",
            "letter_id": letter.letter_id,
            "is_reported": True,
            "sender_notified": True,
        },
        status_code=201,
    )
