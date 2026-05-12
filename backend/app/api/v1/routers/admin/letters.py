from fastapi import Depends, Request, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import enforce_admin_ip, get_admin_claims
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.session import get_db
from app.services.db.models import TherapyLetter
from app.services.letter_ai_worker import run_ai_reply_worker
from .shared import router, _audit

@router.get("/letters")
def admin_list_letters(
    request: Request,
    status: str | None = None,
    query: str | None = None,
    replied_by: str | None = None, # 'none', 'ai', 'human'
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    from app.services.letter_ai_worker import AI_SERENE_USER_ID
    
    where_conditions = [TherapyLetter.letter_type != "reply"]
    if status:
        where_conditions.append(TherapyLetter.status == status)
    else:
        # Default to active letters if no status specified
        where_conditions.append(TherapyLetter.status == "active")

    if query:
        where_conditions.append(TherapyLetter.content.ilike(f"%{query}%"))
        
    from sqlalchemy.orm import aliased
    Reply = aliased(TherapyLetter)
    
    if replied_by == 'none':
        # Letters with no replies
        where_conditions.append(
            ~select(Reply.letter_id)
            .where(Reply.reply_to_id == TherapyLetter.letter_id)
            .exists()
        )
    elif replied_by == 'ai':
        # Letters with AI replies
        where_conditions.append(
            select(Reply.letter_id)
            .where(
                Reply.reply_to_id == TherapyLetter.letter_id,
                Reply.user_id == AI_SERENE_USER_ID
            )
            .exists()
        )
    elif replied_by == 'human':
        # Letters with Human/User replies (Not AI)
        where_conditions.append(
            select(Reply.letter_id)
            .where(
                Reply.reply_to_id == TherapyLetter.letter_id,
                Reply.user_id != AI_SERENE_USER_ID
            )
            .exists()
        )
        
    stmt = select(TherapyLetter)
    if where_conditions:
        stmt = stmt.where(*where_conditions)
        
    total = db.scalar(select(func.count(TherapyLetter.letter_id)).where(*where_conditions))
    
    letters = db.scalars(stmt.order_by(TherapyLetter.created_at.desc()).offset(offset).limit(limit)).all()
    
    letters_with_replies = []

    for l in letters:
        # Get all replies for this letter
        replies_data = db.scalars(
            select(TherapyLetter)
            .where(TherapyLetter.reply_to_id == l.letter_id)
            .order_by(TherapyLetter.created_at.asc())
        ).all()
        
        all_replies = []
        for r in replies_data:
            all_replies.append({
                "content": r.content,
                "created_at": r.created_at.isoformat(),
                "author": r.anonymous_name or "Người dùng",
                "is_ai": r.user_id == AI_SERENE_USER_ID
            })
        
        letters_with_replies.append({
            "letter_id": l.letter_id,
            "sender_id": l.user_id,
            "content": l.content,
            "status": l.status,
            "report_data": l.report_data,
            "created_at": l.created_at.isoformat(),
            "replies": all_replies,
            # For backward compatibility and quick access
            "ai_reply": next((r for r in all_replies if r["is_ai"]), None),
            "human_reply": next((r for r in all_replies if not r["is_ai"]), None)
        })
    
    _audit(db, claims["sub"], "LIST_LETTERS", request)
    
    return ok({
        "letters": letters_with_replies,
        "total": total or 0
    })

@router.patch("/letters/{letter_id}/review")
def admin_review_letter(
    letter_id: str,
    action: str, # "keep" or "delete"
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    letter = db.get(TherapyLetter, letter_id)
    if not letter:
        raise AppError("NOT_FOUND", "Thư không tồn tại", 404)
        
    if action == "keep":
        letter.status = "active"
        if letter.report_data:
            letter.report_data["reviewed"] = True
            letter.report_data["reviewed_by"] = claims["sub"]
    elif action == "delete":
        letter.status = "deleted"
    else:
        raise AppError("INVALID_PARAMETER", "Hành động không hợp lệ", 400)
        
    db.commit()
    
    _audit(db, claims["sub"], f"REVIEW_LETTER_{letter_id}_{action}", request)
    
    return ok({"letter_id": letter_id, "action": action})

@router.post("/letters/{letter_id}/ai-analyze")
async def admin_ai_analyze_letter(
    letter_id: str,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    letter = db.get(TherapyLetter, letter_id)
    if not letter:
        raise AppError("NOT_FOUND", "Thư không tồn tại", 404)

    # Determine if it's a normal or reported analysis
    if letter.status == "reported":
        reason = letter.report_data.get("reason") if letter.report_data else None
        from app.services.letter_ai_worker import analyze_reported_letter
        result = await analyze_reported_letter(letter.content, reason)
    else:
        # Generic summary for normal letters
        result = {"category": "general", "reason": "Thư bình thường, sẵn sàng phản hồi.", "action": "keep"}

    _audit(db, claims["sub"], f"AI_ANALYZE_LETTER_{letter_id}", request)
    
    return ok(result)

@router.post("/run-ai-responder")
async def admin_run_ai_responder(
    request: Request,
    hours: int = 6,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    count = await run_ai_reply_worker(db, hours_threshold=hours)
    
    _audit(db, claims["sub"], f"RUN_AI_RESPONDER_{hours}H", request)
    
    return ok({"processed_count": count})

@router.get("/letters/{letter_id}/ai-suggest")
async def admin_letter_ai_suggest(
    letter_id: str,
    request: Request,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    letter = db.get(TherapyLetter, letter_id)
    if not letter:
        raise AppError("NOT_FOUND", "Thư không tồn tại", 404)
        
    from app.services.letter_ai_worker import generate_multi_reply_suggestions, MoodCheckin, ClinicalProfile
    
    # Get context
    sender_id = letter.user_id
    latest_mood = db.scalar(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == sender_id)
        .order_by(MoodCheckin.logged_at.desc())
        .limit(1)
    )
    clinical = db.scalar(
        select(ClinicalProfile).where(ClinicalProfile.user_id == sender_id)
    )
    
    mood_str = f"{latest_mood.mood} ({latest_mood.emoji})" if latest_mood else "Chưa ghi nhận"
    clin_str = f"PHQ-9: {clinical.phq9_score}, GAD-7: {clinical.gad7_score}" if clinical else "N/A"
    
    suggestions = await generate_multi_reply_suggestions(letter.content, mood_str, clin_str)
    
    _audit(db, claims["sub"], f"AI_SUGGEST_REPLY_{letter_id}", request)
    return ok({"suggestions": suggestions})

from pydantic import BaseModel
class AdminReplyPayload(BaseModel):
    content: str
    anonymous_name: str | None = None

@router.post("/letters/{letter_id}/reply")
async def admin_letter_reply(
    letter_id: str,
    payload: AdminReplyPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    letter = db.get(TherapyLetter, letter_id)
    if not letter:
        raise AppError("NOT_FOUND", "Thư không tồn tại", 404)
        
    from app.services.utils import make_id, make_anon_name, get_now
    from app.services.letter_ai_worker import AI_SERENE_USER_ID
    from app.services.db.models import User

    # Ensure system user exists
    ai_user = db.get(User, AI_SERENE_USER_ID)
    if not ai_user:
        ai_user = User(
            user_id=AI_SERENE_USER_ID,
            email="healer.friend@serene.app",
            display_name="Người bạn chữa lành",
            is_active=True
        )
        db.add(ai_user)
        db.flush()
    
    # Create reply
    reply = TherapyLetter(
        letter_id=make_id("lrep_adm"),
        user_id=AI_SERENE_USER_ID, # Use the system user ID that exists in 'users' table
        receiver_id=letter.user_id, # Set receiver so user sees it in inbox
        reply_to_id=letter.letter_id,
        anonymous_name=payload.anonymous_name or "Một người lắng nghe",
        content=payload.content,
        letter_type="reply",
        status="active",
        created_at=get_now().replace(tzinfo=None)
    )
    
    # Remove from pending (by setting receiver_id to None if it was waiting for someone)
    letter.receiver_id = None
    
    db.add(reply)
    db.add(letter)
    
    # Send notification to the user
    from app.services.notification_service import send_instant_notification
    send_instant_notification(
        db, 
        user_id=letter.user_id, 
        event_type="letter.replied", 
        payload={
            "letter_id": letter.letter_id,
            "reply_id": reply.letter_id,
            "message": f"Ai đó vừa phản hồi lá thư tâm sự của bạn."
        },
        background_tasks=background_tasks
    )
    
    db.commit()
    
    _audit(db, claims["sub"], f"ADMIN_REPLY_LETTER_{letter_id}", request)
    return ok({"message": "Đã gửi phản hồi thành công", "reply_id": reply.letter_id})
