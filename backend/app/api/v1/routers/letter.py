from datetime import date, datetime, timezone
import random

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import Letter, LetterFlow, LetterReaction, LetterReply, Report, SyncOutbox, User
from app.db.session import get_db
from app.schemas.payloads import LetterReactRequest, LetterReplyRequest, LetterReportRequest, LetterSendRequest
from app.services.utils import make_anon_name, make_id

router = APIRouter(tags=["letters"])


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def can_send_letter(db: Session, user_id: str) -> bool:
    today = date.today()
    count = (
        db.query(func.count(Letter.letter_id))
        .filter(Letter.sender_id == user_id, func.date(Letter.created_at) == today)
        .scalar()
    ) or 0
    return count < 5


def can_receive(db: Session, user_id: str) -> bool:
    today = date.today()
    count = (
        db.query(func.count(LetterFlow.flow_id))
        .filter(LetterFlow.to_user_id == user_id, func.date(LetterFlow.created_at) == today)
        .scalar()
    ) or 0
    return count < 5


def _latest_flow(db: Session, letter_id: str) -> LetterFlow | None:
    return (
        db.query(LetterFlow)
        .filter(LetterFlow.letter_id == letter_id)
        .order_by(LetterFlow.created_at.desc(), LetterFlow.flow_id.desc())
        .first()
    )


def _received_flow(db: Session, letter_id: str, user_id: str) -> LetterFlow | None:
    return (
        db.query(LetterFlow)
        .filter(
            LetterFlow.letter_id == letter_id,
            LetterFlow.to_user_id == user_id,
            LetterFlow.action.in_(["sent", "forwarded"]),
        )
        .order_by(LetterFlow.created_at.desc(), LetterFlow.flow_id.desc())
        .first()
    )


def _reply_summary(db: Session, letter: Letter, *, replier_id: str | None = None) -> dict | None:
    query = db.query(LetterReply).filter(LetterReply.letter_id == letter.letter_id)
    if replier_id:
        query = query.filter(LetterReply.replier_id == replier_id)

    reply = query.first()
    if not reply:
        return None

    reaction = (
        db.query(LetterReaction)
        .filter(LetterReaction.reply_id == reply.reply_id, LetterReaction.user_id == letter.sender_id)
        .first()
    )

    return {
        "reply_id": reply.reply_id,
        "content": reply.content,
        "anonymous_name": reply.anonymous_name,
        "replier_id": reply.replier_id,
        "received_at": reply.created_at.isoformat() + "Z",
        "reaction_type": reaction.reaction_type if reaction else None,
        "has_reaction": reaction is not None,
    }


def _replied_archive_item(db: Session, reply: LetterReply) -> dict:
    letter = db.get(Letter, reply.letter_id)
    reaction = (
        db.query(LetterReaction)
        .filter(LetterReaction.reply_id == reply.reply_id, LetterReaction.user_id == (letter.sender_id if letter else None))
        .first()
    )
    return {
        "reply_id": reply.reply_id,
        "letter_id": reply.letter_id,
        "content": reply.content,
        "anonymous_name": reply.anonymous_name,
        "original_content": letter.content if letter else None,
        "sent_at": reply.created_at.isoformat() + "Z",
        "reaction_type": reaction.reaction_type if reaction else None,
        "has_reaction": reaction is not None,
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

    used_user_ids: set[str] = set()
    if letter_id:
        used_user_ids = {
            uid[0]
            for uid in db.query(LetterFlow.to_user_id).filter(LetterFlow.letter_id == letter_id).all()
            if uid[0]
        }

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


def _notify_sender_reported(db: Session, sender_id: str, *, letter_id: str, report_id: str, reporter_id: str) -> None:
    next_outbox_id = (db.query(func.max(SyncOutbox.outbox_id)).scalar() or 0) + 1
    payload = {
        "letter_id": letter_id,
        "report_id": report_id,
        "reporter_id": reporter_id,
        "message": "Your letter was reported",
    }
    db.add(
        SyncOutbox(
            outbox_id=next_outbox_id,
            user_id=sender_id,
            event_type="letter.reported",
            payload=payload,
            status="pending",
        )
    )


def _notify_sender_replied(db: Session, sender_id: str, *, letter_id: str, reply_id: str, replier_id: str) -> None:
    next_outbox_id = (db.query(func.max(SyncOutbox.outbox_id)).scalar() or 0) + 1
    payload = {
        "letter_id": letter_id,
        "reply_id": reply_id,
        "replier_id": replier_id,
        "message": "Your letter received a reply",
    }
    db.add(
        SyncOutbox(
            outbox_id=next_outbox_id,
            user_id=sender_id,
            event_type="letter.replied",
            payload=payload,
            status="pending",
        )
    )


@router.post("/letters")
def send_letter(
    payload: LetterSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    if not can_send_letter(db, current_user.user_id):
        raise AppError("LETTER_SEND_DAILY_LIMIT", "Bạn đã gửi tối đa 5 thư hôm nay", 400)

    receiver_id = _pick_receiver(db, sender_id=current_user.user_id)
    if receiver_id is None:
        raise AppError("LETTER_NO_RECEIVER", "Hiện chưa có người nhận phù hợp", 400)

    letter = Letter(
        letter_id=make_id("let"),
        sender_id=current_user.user_id,
        content=payload.content,
    )
    flow = LetterFlow(
        flow_id=make_id("lf"),
        letter_id=letter.letter_id,
        from_user_id=current_user.user_id,
        to_user_id=receiver_id,
        action="sent",
        created_at=_utc_naive_now(),
    )
    db.add(letter)
    db.add(flow)
    db.commit()

    return ok(
        {
            "letter_id": letter.letter_id,
            "receiver_id": receiver_id,
            "forward_count": letter.forward_count,
            "has_reply": letter.has_reply,
            "is_reported": letter.is_reported,
        },
        status_code=201,
    )


@router.get("/letters/inbox")
def get_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letters = db.query(Letter).order_by(Letter.created_at.desc()).all()

    items = []
    for letter in letters:
        if letter.sender_id == current_user.user_id:
            continue
        if letter.is_reported:
            continue
        latest = _latest_flow(db, letter.letter_id)
        if not latest or latest.to_user_id != current_user.user_id or latest.action not in {"sent", "forwarded"}:
            continue
        if letter.has_reply:
            continue

        items.append(
            {
                "letter_id": letter.letter_id,
                "content": letter.content,
                "sender_id": letter.sender_id,
                "forward_count": letter.forward_count,
                "has_reply": letter.has_reply,
                "is_reported": letter.is_reported,
                "received_at": latest.created_at.isoformat() + "Z",
                "status": "received",
            }
        )

    return ok({"letters": items, "total": len(items), "has_more": False})


@router.get("/letters/sent")
def get_sent_letters(
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    rows = (
        db.query(Letter)
        .filter(Letter.sender_id == current_user.user_id)
        .order_by(Letter.created_at.desc())
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
                "has_reply": letter.has_reply,
                "is_reported": letter.is_reported,
                "reply": (
                    {
                        "reply_id": reply["reply_id"],
                        "content": reply["content"],
                        "anonymous_name": reply["anonymous_name"],
                        "replier_id": reply["replier_id"],
                        "received_at": reply["received_at"],
                        "reaction_type": reply["reaction_type"],
                        "has_reaction": reply["has_reaction"],
                    }
                    if reply
                    else None
                ),
            }
        )

    replied_rows = (
        db.query(LetterReply)
        .filter(LetterReply.replier_id == current_user.user_id)
        .order_by(LetterReply.created_at.desc())
        .all()
    )
    replied_items = [_replied_archive_item(db, reply) for reply in replied_rows]

    return ok({"letters": items, "reply_letters": replied_items, "total": len(items) + len(replied_items), "has_more": False})


@router.post("/letters/{letter_id}/forward")
def forward_letter(
    letter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letter = db.get(Letter, letter_id)
    if not letter:
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    if letter.forward_count >= 3:
        raise AppError("FORWARD_LIMIT_REACHED", "Thư đã đạt giới hạn chuyển tiếp", 400)

    latest = _latest_flow(db, letter_id)
    if not latest or latest.to_user_id != current_user.user_id or latest.action not in {"sent", "forwarded"}:
        raise AppError("LETTER_FORWARD_NOT_ALLOWED", "Bạn không được chuyển tiếp thư này", 403)

    new_receiver = _pick_receiver(
        db,
        sender_id=letter.sender_id,
        letter_id=letter_id,
        excluded_user_ids={current_user.user_id},
    )
    if new_receiver is None:
        raise AppError("LETTER_NO_RECEIVER", "Hiện chưa có người nhận phù hợp", 400)

    letter.forward_count += 1
    flow = LetterFlow(
        flow_id=make_id("lf"),
        letter_id=letter.letter_id,
        from_user_id=current_user.user_id,
        to_user_id=new_receiver,
        action="forwarded",
        created_at=_utc_naive_now(),
    )
    db.add(letter)
    db.add(flow)
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
    letter = db.get(Letter, letter_id)
    if not letter:
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    if letter.has_reply:
        raise AppError("ALREADY_REPLIED", "Thư đã được phản hồi", 400)

    latest = _latest_flow(db, letter_id)
    if not latest or latest.to_user_id != current_user.user_id or latest.action not in {"sent", "forwarded"}:
        raise AppError("LETTER_REPLY_NOT_ALLOWED", "Bạn không được phản hồi thư này", 403)

    reply = LetterReply(
        reply_id=make_id("lrep"),
        letter_id=letter.letter_id,
        replier_id=current_user.user_id,
        anonymous_name=make_anon_name(),
        content=payload.content,
    )
    flow = LetterFlow(
        flow_id=make_id("lf"),
        letter_id=letter.letter_id,
        from_user_id=current_user.user_id,
        to_user_id=letter.sender_id,
        action="replied",
        created_at=_utc_naive_now(),
    )

    letter.has_reply = True
    db.add(reply)
    db.add(flow)
    # notify the sender that their letter received a reply
    _notify_sender_replied(db, letter.sender_id, letter_id=letter.letter_id, reply_id=reply.reply_id, replier_id=current_user.user_id)
    db.add(letter)
    db.commit()

    return ok(
        {
            "reply_id": reply.reply_id,
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
    reply = db.get(LetterReply, reply_id)
    if not reply:
        raise AppError("REPLY_NOT_FOUND", "Không tìm thấy phản hồi", 404)

    letter = db.get(Letter, reply.letter_id)
    if not letter or letter.sender_id != current_user.user_id:
        raise AppError("LETTER_REACT_NOT_ALLOWED", "Chỉ người gửi thư mới được thả cảm xúc", 403)

    existing = (
        db.query(LetterReaction)
        .filter(LetterReaction.reply_id == reply_id, LetterReaction.user_id == current_user.user_id)
        .first()
    )
    if existing:
        raise AppError("ALREADY_REACTED", "Bạn đã thả cảm xúc cho phản hồi này", 400)

    reaction = LetterReaction(
        reaction_id=make_id("lrea"),
        reply_id=reply_id,
        user_id=current_user.user_id,
        reaction_type=payload.reaction_type,
    )
    db.add(reaction)
    db.commit()

    return ok(
        {
            "reaction_id": reaction.reaction_id,
            "reply_id": reply_id,
            "reaction_type": reaction.reaction_type,
        },
        status_code=201,
    )


@router.post("/reports")
def report_letter(
    payload: LetterReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
):
    letter = db.get(Letter, payload.letter_id)
    if not letter:
        raise AppError("LETTER_NOT_FOUND", "Không tìm thấy thư", 404)

    was_receiver = (
        db.query(LetterFlow.flow_id)
        .filter(LetterFlow.letter_id == letter.letter_id, LetterFlow.to_user_id == current_user.user_id)
        .first()
        is not None
    )
    if current_user.user_id != letter.sender_id and not was_receiver:
        raise AppError("LETTER_REPORT_NOT_ALLOWED", "Bạn không được báo cáo thư này", 403)

    report = Report(
        report_id=make_id("rep"),
        reporter_id=current_user.user_id,
        letter_id=letter.letter_id,
        reason=payload.reason,
    )
    letter.is_reported = True

    db.add(report)
    db.add(letter)
    _notify_sender_reported(
        db,
        letter.sender_id,
        letter_id=letter.letter_id,
        report_id=report.report_id,
        reporter_id=current_user.user_id,
    )
    db.commit()

    return ok(
        {
            "report_id": report.report_id,
            "letter_id": letter.letter_id,
            "is_reported": letter.is_reported,
            "sender_notified": True,
        },
        status_code=201,
    )
