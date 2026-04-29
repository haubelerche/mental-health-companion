from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.core.errors import AppError
from app.services.utils import make_id, utc_now
from app.api.deps import ensure_policy_acknowledged, get_admin_claims, enforce_admin_ip
from app.schemas.payloads import BambooSendRequest, BambooReplyRequest, BambooPassRequest
from app.db.models import User, BambooMessage
from app.db.session import get_db
import random
from datetime import datetime

router = APIRouter(prefix="/bamboo", tags=["bamboo"])


@router.post("/send")
def send_letter(payload: BambooSendRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    msg_id = make_id("bam")
    anon_name = "Một người vô danh"
    record = BambooMessage(
        message_id=msg_id,
        user_id=current_user.user_id,
        anonymous_name=anon_name,
        content=payload.content,
        topic=payload.topic,
        tone=payload.tone,
        direction="sent",
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ok(
        {
            "message_id": msg_id,
            "status": record.status,
            "sent_at": record.created_at.isoformat() + "Z",
            "moderation_mode": "hybrid",
            "anonymous_name": record.anonymous_name,
        },
        status_code=201,
    )


@router.get("/inbox")
def get_inbox(db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    rows = (
        db.query(BambooMessage)
        .filter(BambooMessage.status == "approved", BambooMessage.recipient_id == current_user.user_id)
        .order_by(BambooMessage.created_at.desc())
        .all()
    )
    items = [
        {
            "message_id": r.message_id,
            "anonymous_name": r.anonymous_name,
            "content": r.content,
            "topic": r.topic,
            "tone": r.tone,
            "received_at": r.created_at.isoformat() + "Z",
            "pass_count": r.pass_count,
            "reply_count": r.reply_count,
        }
        for r in rows
    ]
    return ok({"messages": items, "total": len(items), "has_more": False})


@router.get("/storage")
def get_storage(db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    rows = db.query(BambooMessage).filter((BambooMessage.user_id == current_user.user_id) | (BambooMessage.status == "approved")).order_by(BambooMessage.created_at.desc()).all()
    letters = [
        {
            "message_id": r.message_id,
            "direction": "sent" if r.user_id == current_user.user_id else "received",
            "status": r.status,
            "content": r.content,
            "topic": r.topic,
            "tone": r.tone,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]
    return ok({"letters": letters})


@router.get("/letters/{message_id}")
def get_letter(message_id: str, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    row = db.get(BambooMessage, message_id)
    if not row:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    if row.status != "approved" and row.user_id != current_user.user_id:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    # mark opened if recipient is the current user and not opened yet
    if row.recipient_id == current_user.user_id and row.opened_at is None:
        row.opened_at = datetime.utcnow()
        db.add(row)
        db.commit()

    return ok(
        {
            "message_id": row.message_id,
            "anonymous_name": row.anonymous_name,
            "content": row.content,
            "topic": row.topic,
            "tone": row.tone,
            "direction": "received" if row.user_id != current_user.user_id else "sent",
            "status": row.status,
            "received_at": row.created_at.isoformat() + "Z",
            "reply_count": row.reply_count,
            "pass_count": row.pass_count,
        }
    )


@router.post("/reply")
def reply_letter(payload: BambooReplyRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    target = db.get(BambooMessage, payload.message_id)
    if not target or target.status != "approved":
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    rid = make_id("bam_r")
    reply = BambooMessage(
        message_id=rid,
        user_id=current_user.user_id,
        anonymous_name="Một người vô danh",
        content=payload.content,
        topic=payload.topic or target.topic,
        tone=None,
        direction="reply",
        status="pending",
    )
    db.add(reply)
    # increment reply_count for target
    target.reply_count = (target.reply_count or 0) + 1
    db.add(target)
    db.commit()
    return ok({"reply_id": rid, "message_id": payload.message_id, "status": "pending"}, status_code=201)


@router.post("/pass")
def pass_letter(payload: BambooPassRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    target = db.get(BambooMessage, payload.message_id)
    if not target or target.status != "approved":
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    target.pass_count = (target.pass_count or 0) + 1
    # find a new recipient (exclude sender and current recipient)
    candidates = (
        db.query(User)
        .filter(User.user_id != target.user_id, User.user_id != target.recipient_id, User.is_active.is_(True), User.policy_acknowledged_at.is_not(None))
        .all()
    )
    new_recipient = None
    elig = []
    for u in candidates:
        cnt = db.query(BambooMessage).filter(BambooMessage.recipient_id == u.user_id, BambooMessage.status == "approved", BambooMessage.opened_at.is_(None)).count()
        if cnt < 5:
            elig.append(u)
    if elig:
        new_recipient = random.choice(elig).user_id
    target.recipient_id = new_recipient
    db.add(target)
    db.commit()
    return ok({"message_id": payload.message_id, "pass_count": target.pass_count, "new_recipient": new_recipient, "passed_at": utc_now().isoformat() + "Z"})


# Moderation endpoints (admin only)
@router.get("/moderation/queue")
def moderation_queue(admin: dict = Depends(get_admin_claims), request=Depends(enforce_admin_ip), db: Session = Depends(get_db)):
    items = db.query(BambooMessage).filter(BambooMessage.status == "pending").order_by(BambooMessage.created_at.desc()).all()
    simplified = [
        {
            "message_id": r.message_id,
            "status": r.status,
            "submitted_at": r.created_at.isoformat() + "Z",
            "topic": r.topic,
            "tone": r.tone,
            "flag_count": 0,
        }
        for r in items
    ]
    return ok({"items": simplified, "total": len(simplified), "has_more": False})


@router.patch("/moderation/{message_id}")
def moderation_action(message_id: str, payload: dict, admin: dict = Depends(get_admin_claims), request=Depends(enforce_admin_ip), db: Session = Depends(get_db)):
    row = db.get(BambooMessage, message_id)
    if not row:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    status = payload.get("status")
    if status not in {"approved", "rejected", "archived"}:
        raise AppError("INVALID_PARAMETER", "status không hợp lệ", 400)
    row.status = status
    row.reviewed_at = utc_now()
    # on approval, assign to a random recipient who has <5 unread messages
    if status == "approved":
        candidates = (
            db.query(User)
            .filter(User.user_id != row.user_id, User.is_active.is_(True), User.policy_acknowledged_at.is_not(None))
            .all()
        )
        elig = []
        for u in candidates:
            cnt = db.query(BambooMessage).filter(BambooMessage.recipient_id == u.user_id, BambooMessage.status == "approved", BambooMessage.opened_at.is_(None)).count()
            if cnt < 5:
                elig.append(u)
        new_recipient = None
        if elig:
            new_recipient = random.choice(elig).user_id
        row.recipient_id = new_recipient
    db.add(row)
    db.commit()
    return ok({"message_id": message_id, "status": status, "recipient_id": row.recipient_id, "reviewed_at": row.reviewed_at.isoformat() + "Z"})
