"""Memory-card persistence and user actions."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.memory.extractor import ExtractionResult, MemoryCandidate
from app.memory.guardrail import review_memory_candidate
from app.services.db.models import MemoryCard, MemoryCardAuditEvent
from app.services.utils import make_id


def _candidate_items(extraction: ExtractionResult | dict[str, Any]) -> Iterable[MemoryCandidate | dict[str, Any]]:
    if isinstance(extraction, ExtractionResult):
        return extraction.candidate_cards
    return extraction.get("candidate_cards", []) or []


def _candidate_value(candidate: MemoryCandidate | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(candidate, MemoryCandidate):
        return getattr(candidate, key, default)
    return candidate.get(key, default)


def create_cards_from_candidates(
    db: Session,
    user_id: str,
    extraction: ExtractionResult | dict[str, Any],
) -> list[MemoryCard]:
    cards: list[MemoryCard] = []
    for candidate in _candidate_items(extraction):
        memory_type = str(_candidate_value(candidate, "memory_type", "") or "")
        title = str(_candidate_value(candidate, "title", "") or "").strip()
        content = str(_candidate_value(candidate, "content", "") or "").strip()
        confidence = _candidate_value(candidate, "confidence", None)
        source_session_id = _candidate_value(candidate, "source_session_id", None)
        metadata = dict(_candidate_value(candidate, "metadata", {}) or {})

        review = review_memory_candidate(memory_type, title, content, confidence)
        approved = bool(review["approved"])
        metadata["guardrail_rejection_reason"] = review["rejection_reason"]
        card = MemoryCard(
            card_id=make_id("mc"),
            user_id=user_id,
            source_session_id=source_session_id,
            memory_type=memory_type,
            title=title,
            content=content,
            confidence=confidence,
            status="pending_user_review" if approved else "rejected_by_guardrail",
            safety_review_status="approved" if approved else "rejected",
            personalization_disabled=False,
            metadata_json=metadata,
        )
        db.add(card)
        cards.append(card)
    db.flush()
    return cards


def _get_card(db: Session, user_id: str, card_id: str) -> MemoryCard:
    card = db.scalar(select(MemoryCard).where(MemoryCard.user_id == user_id, MemoryCard.card_id == card_id))
    if card is None:
        raise ValueError("memory card not found")
    if card.status == "deleted_by_user":
        raise ValueError("memory card has been deleted")
    return card


def _audit(
    db: Session,
    *,
    card: MemoryCard,
    action: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    db.add(
        MemoryCardAuditEvent(
            event_id=make_id("mca"),
            memory_card_id=card.card_id,
            user_id=card.user_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
        )
    )


def apply_user_action(
    db: Session,
    user_id: str,
    card_id: str,
    action: str,
    *,
    new_content: str | None = None,
) -> MemoryCard:
    card = _get_card(db, user_id, card_id)
    old_value = {
        "status": card.status,
        "content": card.content,
        "personalization_disabled": card.personalization_disabled,
    }

    if action == "keep":
        card.status = "active"
    elif action == "edit":
        if not new_content or not new_content.strip():
            raise ValueError("new_content is required for edit")
        review = review_memory_candidate(card.memory_type, card.title, new_content, card.confidence)
        if not review["approved"]:
            raise ValueError(f"edit rejected by guardrail: {review['rejection_reason']}")
        card.content = new_content.strip()
        card.status = "edited_by_user"
        card.safety_review_status = "approved"
    elif action == "delete":
        card.status = "deleted_by_user"
    elif action == "disable_personalization":
        card.personalization_disabled = True
    else:
        raise ValueError(f"unsupported memory action: {action}")

    _audit(
        db,
        card=card,
        action=action,
        old_value=old_value,
        new_value={
            "status": card.status,
            "content": card.content,
            "personalization_disabled": card.personalization_disabled,
        },
    )
    db.flush()
    return card


def get_user_cards(db: Session, user_id: str, *, include_deleted: bool = False) -> list[MemoryCard]:
    stmt = select(MemoryCard).where(MemoryCard.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(MemoryCard.status != "deleted_by_user", MemoryCard.status != "rejected_by_guardrail")
    return list(db.scalars(stmt).all())


def get_active_card_for_context(db: Session, user_id: str) -> MemoryCard | None:
    stmt = (
        select(MemoryCard)
        .where(
            MemoryCard.user_id == user_id,
            MemoryCard.status.in_(["active", "edited_by_user"]),
            MemoryCard.personalization_disabled.is_(False),
        )
        .order_by(MemoryCard.updated_at.desc(), MemoryCard.created_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)
