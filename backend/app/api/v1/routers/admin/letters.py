from fastapi import Depends, Request
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
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    
    where_conditions = []
    if status:
        where_conditions.append(TherapyLetter.status == status)
    else:
        # Default to reported letters for monitoring
        where_conditions.append(TherapyLetter.status == "reported")

    if query:
        where_conditions.append(TherapyLetter.content.ilike(f"%{query}%"))
        
    stmt = select(TherapyLetter)
    if where_conditions:
        stmt = stmt.where(*where_conditions)
        
    total = db.scalar(select(func.count(TherapyLetter.letter_id)).where(*where_conditions))
    
    letters = db.scalars(stmt.order_by(TherapyLetter.created_at.desc()).offset(offset).limit(limit)).all()
    
    letters_with_replies = []
    from app.services.letter_ai_worker import AI_SERENE_USER_ID

    for l in letters:
        # Check if AI has replied
        ai_reply = db.scalar(
            select(TherapyLetter)
            .where(
                TherapyLetter.reply_to_id == l.letter_id,
                TherapyLetter.user_id == AI_SERENE_USER_ID
            )
            .limit(1)
        )
        
        letters_with_replies.append({
            "letter_id": l.letter_id,
            "sender_id": l.user_id,
            "content": l.content,
            "status": l.status,
            "report_data": l.report_data,
            "created_at": l.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "ai_reply": {
                "content": ai_reply.content,
                "created_at": ai_reply.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            } if ai_reply else None
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
