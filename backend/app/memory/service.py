"""Memory Cards service — Plan 06.

Handles persistence: create, list, user actions (keep/edit/delete/disable_personalization),
and retrieval of a single active card for response context injection.

All write paths emit audit events for keep/edit/delete.
Micro-memory rule: get_active_card_for_context() returns at most one card.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from app.services.utils import get_now

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.memory.extractor import ExtractionResult
from app.memory.guardrail import review_memory_candidate
from app.services.db.models import MemoryCard, MemoryCardAuditEvent

UserAction = Literal["keep", "edit", "delete", "disable_personalization"]

_ACTIVE_STATUSES = {"active", "edited_by_user", "pending_user_review"}
_EXCLUDED_FROM_CONTEXT = {"deleted_by_user", "rejected_by_guardrail"}


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def create_cards_from_candidates(
    db: Session,
    user_id: str,
    extraction: ExtractionResult,
    *,
    auto_approve_safe: bool = True,
) -> list[MemoryCard]:
    """Persist guardrail-reviewed candidates. Returns created cards."""
    created: list[MemoryCard] = []

    for candidate in extraction["candidate_cards"]:
        # Skip if a non-deleted, non-rejected card of this type already exists for the user.
        existing = db.scalars(
            select(MemoryCard)
            .where(MemoryCard.user_id == user_id)
            .where(MemoryCard.memory_type == candidate["memory_type"])
            .where(MemoryCard.status.notin_({"deleted_by_user", "rejected_by_guardrail"}))
        ).first()
        if existing:
            continue

        result = review_memory_candidate(
            memory_type=candidate["memory_type"],
            title=candidate["title"],
            content=candidate["content"],
            confidence=candidate.get("confidence"),
        )

        if result["approved"]:
            status = "pending_user_review"
            safety_status = "approved"
        else:
            status = "rejected_by_guardrail"
            safety_status = "rejected"

        card = MemoryCard(
            card_id=f"mc_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            source_session_id=candidate.get("source_session_id"),
            memory_type=candidate["memory_type"],
            title=candidate["title"],
            content=candidate["content"],
            confidence=candidate.get("confidence"),
            status=status,
            safety_review_status=safety_status,
            personalization_disabled=False,
            metadata_json=candidate.get("metadata", {}),
        )
        db.add(card)
        created.append(card)

    if created:
        db.flush()
        # Push real-time notification for new memories
        try:
            from app.services.notification_service import send_instant_notification
            # We notify that new memories are available for review
            send_instant_notification(
                db,
                user_id=user_id,
                event_type="memory.completed",
                payload={
                    "count": len(created),
                    "message": f"AI vừa ghi nhớ thêm {len(created)} điều mới về bạn!",
                    "card_ids": [c.card_id for c in created]
                }
            )
        except Exception:
            # Don't fail the whole memory creation if notification fails
            pass

    return created


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def get_user_cards(
    db: Session,
    user_id: str,
    *,
    include_deleted: bool = False,
    include_rejected: bool = False,
) -> list[MemoryCard]:
    """Return all cards for a user, excluding unwanted statuses by default."""
    stmt = select(MemoryCard).where(MemoryCard.user_id == user_id)

    excluded = set()
    if not include_deleted:
        excluded.add("deleted_by_user")
    if not include_rejected:
        excluded.add("rejected_by_guardrail")

    if excluded:
        stmt = stmt.where(MemoryCard.status.notin_(excluded))

    stmt = stmt.order_by(MemoryCard.created_at.desc())
    return list(db.scalars(stmt))


def get_active_card_for_context(
    db: Session,
    user_id: str,
    memory_type: str | None = None,
) -> MemoryCard | None:
    """Return at most one active card eligible for response injection.

    Micro-memory rule: only one card is injected per response.
    Personalization-disabled and deleted/rejected cards are excluded.
    """
    stmt = (
        select(MemoryCard)
        .where(MemoryCard.user_id == user_id)
        .where(MemoryCard.status.in_({"active", "edited_by_user"}))
        .where(MemoryCard.safety_review_status == "approved")
        .where(MemoryCard.personalization_disabled.is_(False))
    )

    if memory_type:
        stmt = stmt.where(MemoryCard.memory_type == memory_type)

    stmt = stmt.order_by(MemoryCard.updated_at.desc()).limit(1)
    return db.scalars(stmt).first()


def get_card(db: Session, user_id: str, card_id: str) -> MemoryCard | None:
    return db.scalars(
        select(MemoryCard)
        .where(MemoryCard.card_id == card_id)
        .where(MemoryCard.user_id == user_id)
    ).first()


# ---------------------------------------------------------------------------
# User actions
# ---------------------------------------------------------------------------

def apply_user_action(
    db: Session,
    user_id: str,
    card_id: str,
    action: UserAction,
    *,
    new_title: str | None = None,
    new_content: str | None = None,
) -> MemoryCard:
    """Apply a user action to a card. Raises ValueError on invalid state.

    Actions:
        keep                  -> status = active
        edit                  -> update title/content, status = edited_by_user
        delete                -> status = deleted_by_user
        disable_personalization -> personalization_disabled = True (card stays visible)
    """
    card = get_card(db, user_id, card_id)
    if card is None:
        raise ValueError(f"memory card not found: {card_id}")

    if card.status == "deleted_by_user":
        raise ValueError("cannot act on a deleted memory card")

    old_value: dict[str, Any] = {
        "status": card.status,
        "title": card.title,
        "content": card.content,
        "personalization_disabled": card.personalization_disabled,
    }
    new_value: dict[str, Any] = {}

    if action == "keep":
        card.status = "active"
        new_value = {"status": "active"}

    elif action == "edit":
        if new_content is None:
            raise ValueError("edit action requires new_content")
        # Re-run guardrail on edited content
        result = review_memory_candidate(
            memory_type=card.memory_type,
            title=new_title or card.title,
            content=new_content,
        )
        if not result["approved"]:
            raise ValueError(f"edited content rejected by guardrail: {result['rejection_reason']}")

        if new_title:
            card.title = new_title
        card.content = new_content
        card.status = "edited_by_user"
        card.safety_review_status = "approved"
        new_value = {
            "status": "edited_by_user",
            "title": card.title,
            "content": card.content,
        }

    elif action == "delete":
        card.status = "deleted_by_user"
        new_value = {"status": "deleted_by_user"}

    elif action == "disable_personalization":
        card.personalization_disabled = True
        new_value = {"personalization_disabled": True}

    else:
        raise ValueError(f"unknown action: {action}")

    card.updated_at = get_now().replace(tzinfo=None)

    if action in {"keep", "edit", "delete", "disable_personalization"}:
        audit = MemoryCardAuditEvent(
            event_id=f"mca_{uuid.uuid4().hex[:16]}",
            memory_card_id=card.card_id,
            user_id=user_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
        db.add(audit)

    db.flush()
    return card
