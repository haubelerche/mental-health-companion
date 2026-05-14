"""Canonical user-facing memory-card API plus mem0 compatibility aliases."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.errors import AppError
from app.core.responses import ok
from app.memory.normalization import build_memory_display_text
from app.memory.service import apply_user_action, get_user_cards
from app.services.db.models import MemoryCard, User
from app.services.db.session import get_db
from app.services.mem0_repository import delete_user_memory, list_user_memories

router = APIRouter(tags=["memory"])


class MemoryCardOut(BaseModel):
    id: str
    card_id: str
    memory_id: str
    memory_type: str
    display_category: str
    display_text: str
    mention_count: int = 1
    status: str
    is_selected: bool = True
    personalization_disabled: bool = False
    can_personalize: bool = True
    source: str = "memory_card"
    created_at: str | None = None
    last_mentioned_at: str | None = None
    expires_at: str | None = None
    # Compatibility fields for the previous frontend service shape.
    badge_label: str | None = None
    title: str | None = None
    body: str | None = None
    content: str | None = None

    @classmethod
    def from_card(cls, card: MemoryCard) -> "MemoryCardOut":
        display_category = str(getattr(card, "display_category", None) or card.title or "Ký ức")
        display_text = build_memory_display_text(card)
        return cls(
            id=card.card_id,
            card_id=card.card_id,
            memory_id=card.card_id,
            memory_type=card.memory_type,
            display_category=display_category,
            display_text=display_text,
            mention_count=int(getattr(card, "mention_count", 1) or 1),
            status=card.status,
            is_selected=card.status in {"pending_user_review", "active", "edited_by_user"},
            personalization_disabled=bool(card.personalization_disabled),
            can_personalize=not bool(card.personalization_disabled),
            created_at=card.created_at.isoformat() if card.created_at else None,
            last_mentioned_at=card.last_mentioned_at.isoformat() if getattr(card, "last_mentioned_at", None) else None,
            expires_at=card.expires_at.isoformat() if getattr(card, "expires_at", None) else None,
            badge_label=display_category,
            title=display_category,
            body=display_text,
            content=display_text,
        )


class MemoryCardActionIn(BaseModel):
    action: Literal["keep", "edit", "delete", "disable_personalization"]
    new_content: str | None = Field(default=None, max_length=300)


class UserMemoryOut(BaseModel):
    memory_id: str
    content: str
    source: str = "session_summary"
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/chat/memory-cards", summary="List canonical user memory cards")
def list_memory_cards(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: User = Depends(ensure_policy_acknowledged),
) -> Any:
    try:
        cards = get_user_cards(db, current_user.user_id, include_deleted=include_deleted)
    except SQLAlchemyError:
        db.rollback()
        return ok({"cards": [], "memory_cards": [], "memory_status": "temporarily_unavailable"})
    payload = [MemoryCardOut.from_card(card) for card in cards]
    return ok({"cards": payload, "memory_cards": payload})


@router.post("/chat/memory-cards/{card_id}/actions", summary="Apply a memory-card user action")
def memory_card_action(
    card_id: str,
    payload: MemoryCardActionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    try:
        card = apply_user_action(
            db,
            current_user.user_id,
            card_id,
            payload.action,
            new_content=payload.new_content,
        )
    except ValueError as exc:
        raise AppError("MEMORY_CARD_ACTION_INVALID", str(exc), 400) from exc
    db.commit()
    return ok({"memory_card": MemoryCardOut.from_card(card)})


@router.get("/chat/memories", summary="Compatibility alias for mem0-style user memories")
def list_memories_compat(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: User = Depends(ensure_policy_acknowledged),
) -> Any:
    rows = list_user_memories(db, user_id=current_user.user_id, limit=limit)
    memories = [
        UserMemoryOut(
            memory_id=row.id,
            content=row.content,
            source=row.source,
            created_at=row.created_at,
            metadata=dict(row.metadata or {}),
        ).model_dump()
        for row in rows
    ]
    return ok({"memories": memories})


@router.delete("/chat/memories/{memory_id}", summary="Compatibility delete for mem0-style user memories")
def delete_memory_compat(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    if not delete_user_memory(db, user_id=current_user.user_id, memory_id=memory_id):
        raise AppError("MEMORY_NOT_FOUND", "Không tìm thấy ký ức hoặc bạn không có quyền xoá.", 404)
    db.commit()
    return ok({"deleted": True, "memory_id": memory_id})
