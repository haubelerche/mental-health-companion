"""Knowledge Unlocks API router — Plan 07.

Endpoints:
    GET  /api/v1/knowledge/packs                    List packs (with access status)
    GET  /api/v1/knowledge/packs/{pack_id}/cards    List cards (requires access)
    POST /api/v1/knowledge/cards/{card_id}/complete Mark card completed → +15 Tim
    GET  /api/v1/knowledge/progress                 User's completion history
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.responses import ok
from app.knowledge.catalog import get_all_packs, get_cards_for_pack, get_pack
from app.knowledge.progress_service import _get_card_db
from app.knowledge.content_review import review_knowledge_card
from app.knowledge.progress_service import (
    complete_card,
    get_user_progress,
    has_pack_access,
)
from app.services.db.models import User
from app.services.db.session import get_db

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/packs", summary="List all knowledge packs with user access status")
def list_packs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    """Return catalog packs annotated with locked/unlocked status for this user."""
    completed_set = {row["card_id"] for row in get_user_progress(db, current_user.user_id)}
    result = []
    for pack in get_all_packs():
        if not pack.get("is_active", True):
            continue
        accessible = has_pack_access(db, current_user.user_id, pack["pack_id"])
        cards = get_cards_for_pack(pack["pack_id"])
        completed_in_pack = sum(1 for c in cards if c["card_id"] in completed_set)
        result.append({
            **{k: v for k, v in pack.items()},
            "accessible": accessible,
            "card_count": len(cards),
            "completed_card_count": completed_in_pack,
        })
    return ok({"packs": result})


@router.get(
    "/packs/{pack_id}/cards",
    summary="List ordered cards in a pack (requires access)",
)
def list_cards(
    pack_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    pack = get_pack(pack_id)
    if pack is None or not pack.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack not found.")

    if not has_pack_access(db, current_user.user_id, pack_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pack is locked. Purchase or unlock it first.",
        )

    completed_set = {row["card_id"] for row in get_user_progress(db, current_user.user_id)}
    cards = [
        {**c, "completed": c["card_id"] in completed_set}
        for c in get_cards_for_pack(pack_id)
    ]
    return ok({"pack": pack, "cards": cards})


@router.post(
    "/cards/{card_id}/complete",
    summary="Mark a knowledge card as completed (idempotent, +15 Tim once)",
)
def mark_complete(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    card_def = _get_card_db(db, card_id)
    if card_def is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    try:
        result = complete_card(db, current_user.user_id, card_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

    return ok({
        "card_id": card_id,
        "already_completed": result["already_completed"],
        "reward": result["reward"],
    })


@router.get("/progress", summary="List completed knowledge cards for current user")
def user_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    rows = get_user_progress(db, current_user.user_id)
    return ok({"completed": rows, "total_completed": len(rows)})


@router.post("/admin/review-card", summary="Content safety review for a knowledge card (admin/internal)")
def admin_review_card(
    title: str,
    content_markdown: str,
    reflection_prompt: str | None = None,
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    """Deterministic content safety review. Returns approved=True/False + reason."""
    result = review_knowledge_card(title, content_markdown, reflection_prompt)
    return ok(result)
