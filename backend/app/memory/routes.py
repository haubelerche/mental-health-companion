"""Memory Cards API router — Plan 06.

Endpoints:
    GET  /api/v1/chat/memory-cards          List user's memory cards (Ký ức tab)
    POST /api/v1/chat/memory-cards/extract  Extract candidates from session text (internal)
    PATCH /api/v1/chat/memory-cards/{card_id}  Apply user action
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.responses import ok
from app.memory.extractor import extract_memory_candidates
from app.memory.service import (
    apply_user_action,
    create_cards_from_candidates,
    get_user_cards,
    get_active_card_for_context,
)
from app.services.db.models import MemoryCard, User
from app.services.db.session import get_db

router = APIRouter(prefix="/chat/memory-cards", tags=["memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryCardOut(BaseModel):
    card_id: str
    memory_type: str
    title: str
    content: str
    confidence: float | None
    status: str
    safety_review_status: str
    personalization_disabled: bool
    source_session_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, card: MemoryCard) -> "MemoryCardOut":
        return cls(
            card_id=card.card_id,
            memory_type=card.memory_type,
            title=card.title,
            content=card.content,
            confidence=card.confidence,
            status=card.status,
            safety_review_status=card.safety_review_status,
            personalization_disabled=card.personalization_disabled,
            source_session_id=card.source_session_id,
            created_at=card.created_at.isoformat(),
            updated_at=card.updated_at.isoformat(),
        )


class MemoryCardActionRequest(BaseModel):
    action: str = Field(
        ...,
        description="One of: keep, edit, delete, disable_personalization",
    )
    new_title: str | None = Field(None, description="Required when action=edit (optional).")
    new_content: str | None = Field(None, description="Required when action=edit.")


class ExtractRequest(BaseModel):
    session_text: str = Field(..., min_length=1)
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", summary="List memory cards (Ký ức tab)")
def list_memory_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    """Return all visible memory cards for the current user."""
    cards = get_user_cards(db, current_user.user_id)
    return ok({"cards": [MemoryCardOut.from_orm(c) for c in cards]})


@router.patch("/{card_id}", summary="Apply user action to a memory card")
def update_memory_card(
    card_id: str,
    body: MemoryCardActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    """Apply keep / edit / delete / disable_personalization to a memory card."""
    valid_actions = {"keep", "edit", "delete", "disable_personalization"}
    if body.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{body.action}'. Must be one of: {sorted(valid_actions)}",
        )

    try:
        card = apply_user_action(
            db,
            current_user.user_id,
            card_id,
            body.action,  # type: ignore[arg-type]
            new_title=body.new_title,
            new_content=body.new_content,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ok({"card": MemoryCardOut.from_orm(card)})


@router.post("/extract", summary="Extract and save memory candidates from session text")
def extract_and_save(
    body: ExtractRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    """Run extraction + guardrail and persist approved candidates.

    Intended to be called server-side at session close, but exposed as an
    endpoint for internal tooling and integration tests.
    """
    extraction = extract_memory_candidates(
        body.session_text, session_id=body.session_id
    )
    cards = create_cards_from_candidates(db, current_user.user_id, extraction)
    db.commit()

    return ok({
        "extracted": len(extraction["candidate_cards"]),
        "saved": len(cards),
        "cards": [MemoryCardOut.from_orm(c) for c in cards],
    })


@router.get("/context-card", summary="Get one active card eligible for response injection")
def context_card(
    memory_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: None = Depends(ensure_policy_acknowledged),
) -> Any:
    """Return at most one active memory card for LLM context injection (micro-memory rule)."""
    card = get_active_card_for_context(db, current_user.user_id, memory_type=memory_type)
    return ok({"card": MemoryCardOut.from_orm(card) if card else None})
