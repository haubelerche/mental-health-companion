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
    
    _audit(db, claims["sub"], "LIST_LETTERS", request)
    
    return ok({
        "letters": [{
            "letter_id": l.letter_id,
            "sender_id": l.user_id,
            "content": l.content,
            "status": l.status,
            "report_data": l.report_data,
            "created_at": l.created_at.isoformat() + "Z"
        } for l in letters],
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
