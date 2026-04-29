from fastapi import APIRouter, Depends
from typing import Dict, List
from app.core.responses import ok
from app.core.errors import AppError
from app.services.utils import make_id, utc_now
from app.api.deps import ensure_policy_acknowledged, get_admin_claims, enforce_admin_ip
from app.schemas.payloads import BambooSendRequest, BambooReplyRequest, BambooPassRequest
from app.db.models import User

router = APIRouter(prefix="/bamboo", tags=["bamboo"])

# In-memory store for MVP/demo purposes. Not persistent across processes.
_MESSAGES: Dict[str, Dict] = {}
_PUBLIC_FEED: List[str] = []


@router.post("/send")
def send_letter(payload: BambooSendRequest, current_user: User = Depends(ensure_policy_acknowledged)):
    # Basic validation already done by Pydantic
    msg_id = make_id("bam")
    record = {
        "message_id": msg_id,
        "user_id": current_user.user_id,
        "anonymous_name": "Một người vô danh",
        "content": payload.content,
        "topic": payload.topic,
        "tone": payload.tone,
        "direction": "sent",
        "status": "pending",
        "created_at": utc_now().isoformat() + "Z",
        "reviewed_at": None,
        "pass_count": 0,
        "reply_count": 0,
    }
    _MESSAGES[msg_id] = record
    # Add to moderation queue (implicit by status 'pending')
    return ok(
        {
            "message_id": msg_id,
            "status": "pending",
            "sent_at": record["created_at"],
            "moderation_mode": "hybrid",
            "anonymous_name": record["anonymous_name"],
        },
        status_code=201,
    )


@router.get("/inbox")
def get_inbox(current_user: User = Depends(ensure_policy_acknowledged)):
    items = []
    for mid in _PUBLIC_FEED:
        row = _MESSAGES.get(mid)
        if not row:
            continue
        items.append(
            {
                "message_id": row["message_id"],
                "anonymous_name": row["anonymous_name"],
                "content": row["content"],
                "topic": row.get("topic"),
                "tone": row.get("tone"),
                "received_at": row["created_at"],
                "pass_count": row.get("pass_count", 0),
                "reply_count": row.get("reply_count", 0),
            }
        )
    return ok({"messages": items, "total": len(items), "has_more": False})


@router.get("/storage")
def get_storage(current_user: User = Depends(ensure_policy_acknowledged)):
    letters = []
    for row in _MESSAGES.values():
        if row["user_id"] == current_user.user_id or row["status"] == "approved":
            letters.append(
                {
                    "message_id": row["message_id"],
                    "direction": "sent" if row["user_id"] == current_user.user_id else "received",
                    "status": row["status"],
                    "content": row["content"],
                    "topic": row.get("topic"),
                    "tone": row.get("tone"),
                    "created_at": row["created_at"],
                }
            )
    return ok({"letters": letters})


@router.get("/letters/{message_id}")
def get_letter(message_id: str, current_user: User = Depends(ensure_policy_acknowledged)):
    row = _MESSAGES.get(message_id)
    if not row:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    # Only return if approved or belongs to user
    if row["status"] != "approved" and row["user_id"] != current_user.user_id:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    return ok(
        {
            "message_id": row["message_id"],
            "anonymous_name": row["anonymous_name"],
            "content": row["content"],
            "topic": row.get("topic"),
            "tone": row.get("tone"),
            "direction": "received" if row["user_id"] != current_user.user_id else "sent",
            "status": row["status"],
            "received_at": row["created_at"],
            "reply_count": row.get("reply_count", 0),
            "pass_count": row.get("pass_count", 0),
        }
    )


@router.post("/reply")
def reply_letter(payload: BambooReplyRequest, current_user: User = Depends(ensure_policy_acknowledged)):
    target = _MESSAGES.get(payload.message_id)
    if not target or target.get("status") != "approved":
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    # create reply as new message tied to user
    rid = make_id("bam_r")
    reply = {
        "message_id": rid,
        "user_id": current_user.user_id,
        "anonymous_name": "Một người vô danh",
        "content": payload.content,
        "topic": payload.topic or target.get("topic"),
        "tone": None,
        "direction": "reply",
        "status": "pending",
        "created_at": utc_now().isoformat() + "Z",
        "reviewed_at": None,
        "pass_count": 0,
        "reply_count": 0,
    }
    _MESSAGES[rid] = reply
    # increment reply_count for target
    target["reply_count"] = target.get("reply_count", 0) + 1
    return ok({"reply_id": rid, "message_id": payload.message_id, "status": "pending"}, status_code=201)


@router.post("/pass")
def pass_letter(payload: BambooPassRequest, current_user: User = Depends(ensure_policy_acknowledged)):
    target = _MESSAGES.get(payload.message_id)
    if not target or target.get("status") != "approved":
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    target["pass_count"] = target.get("pass_count", 0) + 1
    return ok({"message_id": payload.message_id, "pass_count": target["pass_count"], "passed_at": utc_now().isoformat() + "Z"})


# Moderation endpoints (admin only)
@router.get("/moderation/queue")
def moderation_queue(admin: dict = Depends(get_admin_claims), request=Depends(enforce_admin_ip)):
    items = [v for v in _MESSAGES.values() if v.get("status") == "pending"]
    simplified = [
        {
            "message_id": r["message_id"],
            "status": r["status"],
            "submitted_at": r["created_at"],
            "topic": r.get("topic"),
            "tone": r.get("tone"),
            "flag_count": 0,
        }
        for r in items
    ]
    return ok({"items": simplified, "total": len(simplified), "has_more": False})


@router.patch("/moderation/{message_id}")
def moderation_action(message_id: str, payload: dict, admin: dict = Depends(get_admin_claims), request=Depends(enforce_admin_ip)):
    row = _MESSAGES.get(message_id)
    if not row:
        raise AppError("BAMBOO_MESSAGE_NOT_FOUND", "Không tìm thấy thư", 404)
    status = payload.get("status")
    if status not in {"approved", "rejected", "archived"}:
        raise AppError("INVALID_PARAMETER", "status không hợp lệ", 400)
    row["status"] = status
    row["reviewed_at"] = utc_now().isoformat() + "Z"
    if status == "approved":
        # add to public feed
        if message_id not in _PUBLIC_FEED:
            _PUBLIC_FEED.insert(0, message_id)
    else:
        # ensure not in public feed
        if message_id in _PUBLIC_FEED:
            _PUBLIC_FEED.remove(message_id)
    return ok({"message_id": message_id, "status": status, "reviewed_at": row["reviewed_at"]})
