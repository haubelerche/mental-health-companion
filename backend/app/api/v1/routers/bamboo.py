from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.core.errors import AppError
from app.services.utils import make_id, utc_now, make_anon_name
from app.api.deps import ensure_policy_acknowledged, get_admin_claims, enforce_admin_ip
from app.schemas.payloads import BambooSendRequest, BambooReplyRequest, BambooPassRequest
from app.db.models import User, BambooMessage, Inbox
from app.db.session import get_db
import random
from datetime import datetime
import hashlib

router = APIRouter(prefix="/bamboo", tags=["bamboo"])


def _to_iso_z(dt: datetime) -> str:
    return dt.isoformat() + "Z"


def _inbox_id_for_pair(user_a_id: str, user_b_id: str) -> str:
    pair_key = "::".join(sorted([user_a_id, user_b_id]))
    digest = hashlib.sha256(pair_key.encode("utf-8")).hexdigest()[:24]
    return f"inb_{digest}"


def _resolve_partner_id(row: BambooMessage, *, current_user_id: str) -> str | None:
    if row.user_id == current_user_id:
        return row.recipient_id
    if row.recipient_id == current_user_id:
        return row.user_id
    return None


def _pick_recipient(
    db: Session,
    *,
    sender_user_id: str,
    excluded_user_ids: set[str] | None = None,
) -> str | None:
    excluded = {sender_user_id}
    if excluded_user_ids:
        excluded.update(uid for uid in excluded_user_ids if uid)

    candidates = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            User.policy_acknowledged_at.is_not(None),
            ~User.user_id.in_(list(excluded)),
        )
        .all()
    )
    eligible = []
    for user in candidates:
        unread_count = (
            db.query(BambooMessage)
            .filter(
                BambooMessage.recipient_id == user.user_id,
                BambooMessage.status == "approved",
                BambooMessage.opened_at.is_(None),
            )
            .count()
        )
        if unread_count < 5:
            eligible.append(user.user_id)
    # deterministic selection based on sender id to avoid flakiness in tests
    if not eligible:
        return None
    h = int(hashlib.sha256(sender_user_id.encode("utf-8")).hexdigest(), 16)
    return eligible[h % len(eligible)]


@router.post("/send")
def send_letter(payload: BambooSendRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    msg_id = make_id("bam")
    anon_name = make_anon_name(payload.topic, payload.tone)
    recipient_id = _pick_recipient(db, sender_user_id=current_user.user_id)
    record = BambooMessage(
        message_id=msg_id,
        user_id=current_user.user_id,
        anonymous_name=anon_name,
        content=payload.content,
        topic=payload.topic,
        tone=payload.tone,
        direction="sent",
        status="pending",
        recipient_id=recipient_id,
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
        .filter(
            BambooMessage.recipient_id == current_user.user_id,
            BambooMessage.status.in_(["approved", "pending"]),
        )
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
            "status": r.status,
            "reply_to_message_id": r.reply_to_message_id,
            "pass_count": r.pass_count,
            "reply_count": r.reply_count,
        }
        for r in rows
    ]
    return ok({"messages": items, "total": len(items), "has_more": False})


@router.get("/inboxes")
def get_inboxes(db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    rows = (
        db.query(BambooMessage)
        .filter(
            (BambooMessage.user_id == current_user.user_id)
            | (BambooMessage.recipient_id == current_user.user_id)
        )
        .order_by(BambooMessage.created_at.desc())
        .all()
    )

    grouped: dict[str, list[BambooMessage]] = {}
    for row in rows:
        partner_id = _resolve_partner_id(row, current_user_id=current_user.user_id)
        if not partner_id:
            continue
        grouped.setdefault(partner_id, []).append(row)

    if not grouped:
        return ok({"inboxes": [], "total": 0, "has_more": False})

    # fetch inbox rows to get per-conversation anonymous names
    inbox_ids = [_inbox_id_for_pair(current_user.user_id, pid) for pid in grouped.keys()]
    inbox_map = {i.inbox_id: i for i in db.query(Inbox).filter(Inbox.inbox_id.in_(inbox_ids)).all()}

    items = []
    for partner_id, partner_rows in grouped.items():
        latest = max(partner_rows, key=lambda r: r.created_at)
        unread_count = sum(
            1
            for r in partner_rows
            if r.recipient_id == current_user.user_id
            and r.opened_at is None
            and r.status == "approved"
        )

        inbox_id = _inbox_id_for_pair(current_user.user_id, partner_id)
        inbox = inbox_map.get(inbox_id)
        if inbox:
            if inbox.user_a_id == current_user.user_id:
                partner_anon = inbox.anon_name_b
            else:
                partner_anon = inbox.anon_name_a
        else:
            partner_anon = "Người dùng ẩn danh"

        items.append(
            {
                "inbox_id": inbox_id,
                "display_name": partner_anon,
                "last_message_preview": latest.content,
                "last_message_at": _to_iso_z(latest.created_at),
                "last_direction": "sent" if latest.user_id == current_user.user_id else "received",
                "unread_count": unread_count,
                "message_count": len(partner_rows),
            }
        )

    items.sort(key=lambda i: i["last_message_at"], reverse=True)
    return ok({"inboxes": items, "total": len(items), "has_more": False})


@router.get("/inboxes/{inbox_id}/messages")
def get_inbox_messages(inbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    rows = (
        db.query(BambooMessage)
        .filter(
            (BambooMessage.user_id == current_user.user_id)
            | (BambooMessage.recipient_id == current_user.user_id)
        )
        .order_by(BambooMessage.created_at.asc())
        .all()
    )

    inbox_rows: list[BambooMessage] = []
    partner_id: str | None = None
    for row in rows:
        candidate_partner_id = _resolve_partner_id(row, current_user_id=current_user.user_id)
        if not candidate_partner_id:
            continue
        candidate_inbox_id = _inbox_id_for_pair(current_user.user_id, candidate_partner_id)
        if candidate_inbox_id == inbox_id:
            inbox_rows.append(row)
            partner_id = candidate_partner_id

    if not inbox_rows or not partner_id:
        raise AppError("BAMBOO_INBOX_NOT_FOUND", "Không tìm thấy hộp thư", 404)

    partner = db.get(User, partner_id)
    inbox = db.get(Inbox, inbox_id)

    pending_open_updates = []
    messages = []
    for row in inbox_rows:
        is_received = row.recipient_id == current_user.user_id
        if is_received and row.opened_at is None and row.status == "approved":
            row.opened_at = datetime.utcnow()
            pending_open_updates.append(row)
        # determine anonymous name per-inbox if available
        anon_name = row.anonymous_name
        if inbox and row.inbox_id == inbox.inbox_id:
            if row.user_id == inbox.user_a_id:
                anon_name = inbox.anon_name_a
            else:
                anon_name = inbox.anon_name_b

        messages.append(
            {
                "message_id": row.message_id,
                "anonymous_name": anon_name,
                "content": row.content,
                "topic": row.topic,
                "tone": row.tone,
                "sent_at": _to_iso_z(row.created_at),
                "status": row.status,
                "direction": "sent" if row.user_id == current_user.user_id else "received",
                "reply_to_message_id": row.reply_to_message_id,
                "reply_count": row.reply_count,
                "pass_count": row.pass_count,
            }
        )

    if pending_open_updates:
        db.add_all(pending_open_updates)
        db.commit()

    return ok(
        {
            "inbox": {
                "inbox_id": inbox_id,
                "display_name": partner.display_name if partner else "Người dùng ẩn danh",
            },
            "messages": messages,
            "total": len(messages),
            "has_more": False,
        }
    )


@router.get("/storage")
def get_storage(db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    rows = (
        db.query(BambooMessage)
        .filter(
            (BambooMessage.user_id == current_user.user_id)
            | (
                (BambooMessage.recipient_id == current_user.user_id)
            )
        )
        .order_by(BambooMessage.created_at.desc())
        .all()
    )
    letters = [
        {
            "message_id": r.message_id,
            "direction": "sent" if r.user_id == current_user.user_id else "received",
            "status": r.status,
            "content": r.content,
            "topic": r.topic,
            "tone": r.tone,
            "reply_to_message_id": r.reply_to_message_id,
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
    if row.status != "approved" and row.user_id != current_user.user_id and row.recipient_id != current_user.user_id:
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
            "reply_to_message_id": row.reply_to_message_id,
            "received_at": row.created_at.isoformat() + "Z",
            "reply_count": row.reply_count,
            "pass_count": row.pass_count,
        }
    )


@router.post("/reply")
def reply_letter(payload: BambooReplyRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    target = db.get(BambooMessage, payload.message_id)
    if not target:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    if target.recipient_id != current_user.user_id:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    rid = make_id("bam_r")
    # ensure an Inbox exists for this pair and generate per-inbox anonymous names
    inbox_id = _inbox_id_for_pair(current_user.user_id, target.user_id)
    inbox = db.get(Inbox, inbox_id)
    # create inbox if not exists
    if not inbox:
        # determine ordered users for storage
        a, b = sorted([current_user.user_id, target.user_id])
        # generate two distinct anonymous names
        anon_a = make_anon_name(payload.topic or target.topic, None)
        anon_b = make_anon_name(payload.topic or target.topic, None)
        if anon_a == anon_b:
            anon_b = make_anon_name((payload.topic or target.topic) or "", None)
        inbox = Inbox(inbox_id=inbox_id, user_a_id=a, user_b_id=b, anon_name_a=anon_a, anon_name_b=anon_b)
        db.add(inbox)

    # choose sender anon name from inbox
    if inbox.user_a_id == current_user.user_id:
        sender_anon = inbox.anon_name_a
    else:
        sender_anon = inbox.anon_name_b

    reply = BambooMessage(
        message_id=rid,
        user_id=current_user.user_id,
        anonymous_name=sender_anon,
        content=payload.content,
        topic=payload.topic or target.topic,
        tone=None,
        direction="reply",
        status="pending",
        recipient_id=target.user_id,
        reply_to_message_id=target.message_id,
        inbox_id=inbox.inbox_id,
    )
    db.add(reply)
    # increment reply_count for target
    target.reply_count = (target.reply_count or 0) + 1
    db.add(target)
    db.commit()
    return ok(
        {
            "reply_id": rid,
            "message_id": payload.message_id,
            "reply_to_message_id": target.message_id,
            "status": "pending",
        },
        status_code=201,
    )


@router.post("/inboxes/{inbox_id}/messages")
def send_inbox_message(inbox_id: str, payload: BambooSendRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    inbox = db.get(Inbox, inbox_id)
    if not inbox:
        raise AppError("BAMBOO_INBOX_NOT_FOUND", "Không tìm thấy hộp thư", 404)

    if current_user.user_id not in {inbox.user_a_id, inbox.user_b_id}:
        raise AppError("BAMBOO_INBOX_NOT_FOUND", "Không tìm thấy hộp thư", 404)

    # determine recipient and sender anon name
    if current_user.user_id == inbox.user_a_id:
        recipient = inbox.user_b_id
        anon_name = inbox.anon_name_a
    else:
        recipient = inbox.user_a_id
        anon_name = inbox.anon_name_b

    mid = make_id("bam_m")
    msg = BambooMessage(
        message_id=mid,
        user_id=current_user.user_id,
        anonymous_name=anon_name,
        content=payload.content,
        topic=payload.topic,
        tone=payload.tone,
        direction="sent",
        status="pending",
        recipient_id=recipient,
        inbox_id=inbox.inbox_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return ok({"message_id": mid, "status": msg.status, "sent_at": msg.created_at.isoformat() + "Z"}, status_code=201)


@router.post("/pass")
def pass_letter(payload: BambooPassRequest, db: Session = Depends(get_db), current_user: User = Depends(ensure_policy_acknowledged)):
    target = db.get(BambooMessage, payload.message_id)
    if not target:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    if target.recipient_id != current_user.user_id:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    target.pass_count = (target.pass_count or 0) + 1
    # rotate recipient (exclude sender and previous recipient)
    new_recipient = _pick_recipient(
        db,
        sender_user_id=target.user_id,
        excluded_user_ids={target.recipient_id} if target.recipient_id else None,
    )
    target.recipient_id = new_recipient
    db.add(target)
    db.commit()
    return ok({"message_id": payload.message_id, "pass_count": target.pass_count, "reassigned": bool(new_recipient), "passed_at": utc_now().isoformat() + "Z"})


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
    # on approval, keep pre-assigned recipient if present; otherwise assign one
    if status == "approved":
        if row.recipient_id is None:
            row.recipient_id = _pick_recipient(db, sender_user_id=row.user_id)
    db.add(row)
    db.commit()
    return ok({"message_id": message_id, "status": status, "recipient_id": row.recipient_id, "reviewed_at": row.reviewed_at.isoformat() + "Z"})
