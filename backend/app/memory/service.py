"""Memory-card persistence and user actions."""

from __future__ import annotations

from datetime import timedelta
from threading import RLock
from typing import Any, Iterable

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.memory.display_copy import display_copy_from_card, validate_user_facing_memory_copy
from app.memory.extractor import AtomicMemoryCandidate, ExtractionResult, MemoryCandidate
from app.memory.guardrail import review_memory_candidate
from app.memory.normalization import (
    build_memory_canonical_key,
    build_memory_display_text,
    merge_evidence_message_ids,
    normalize_memory_text,
)
from app.services.db.models import MemoryCard, MemoryCardAuditEvent
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.utils import get_now
from app.services.utils import make_id

_SCHEMA_ENSURED = False
_SCHEMA_LOCK = RLock()


def _is_sqlite(db: Session) -> bool:
    try:
        bind = db.get_bind()
    except Exception:
        bind = getattr(db, "bind", None)
    return str(getattr(getattr(bind, "dialect", None), "name", "")).lower() == "sqlite"


def ensure_memory_card_tables(db: Session) -> None:
    """Ensure canonical memory-card tables exist for local/dev runtimes.

    Alembic migration 0031 remains the production source of truth. This guard
    prevents `/chat/memory-cards` from 500ing when a developer has not migrated
    the database yet.
    """
    global _SCHEMA_ENSURED
    if _SCHEMA_ENSURED:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_ENSURED:
            return

        if _is_sqlite(db):
            MemoryCard.__table__.create(db.get_bind(), checkfirst=True)
            MemoryCardAuditEvent.__table__.create(db.get_bind(), checkfirst=True)
            db.commit()
            _SCHEMA_ENSURED = True
            return

        if not get_settings().auto_create_schema:
            _SCHEMA_ENSURED = True
            return

        db.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app.memory_cards (
                  card_id text PRIMARY KEY,
                  user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
                  source_session_id text REFERENCES app.conversations(session_id) ON DELETE SET NULL,
                  memory_type text NOT NULL,
                  title text NOT NULL,
                  content text NOT NULL,
                  confidence double precision,
                  canonical_key text,
                  normalized_text text,
                  mention_count integer NOT NULL DEFAULT 1,
                  first_mentioned_at timestamptz,
                  last_mentioned_at timestamptz,
                  evidence_message_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
                  display_category text,
                  subject text,
                  predicate text,
                  is_temporary boolean NOT NULL DEFAULT false,
                  status text NOT NULL DEFAULT 'pending_user_review',
                  safety_review_status text NOT NULL DEFAULT 'pending',
                  personalization_disabled boolean NOT NULL DEFAULT false,
                  expires_at timestamptz,
                  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz NOT NULL DEFAULT now(),
                  updated_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS expires_at timestamptz"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS canonical_key text"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS normalized_text text"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS mention_count integer NOT NULL DEFAULT 1"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS first_mentioned_at timestamptz"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS last_mentioned_at timestamptz"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS evidence_message_ids jsonb NOT NULL DEFAULT '[]'::jsonb"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS display_category text"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS subject text"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS predicate text"))
        db.execute(text("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS is_temporary boolean NOT NULL DEFAULT false"))
        db.execute(text("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_type"))
        db.execute(
            text(
                """
                ALTER TABLE app.memory_cards
                ADD CONSTRAINT chk_memory_type CHECK (
                  memory_type IN (
                    'background', 'support_style', 'current_stressor', 'coping_history',
                    'preference', 'persona_preference', 'nutrition_pattern', 'temporary_context',
                    'event_memory', 'support_insight', 'relationship_context',
                    'goal_or_hope', 'emotional_pattern'
                  )
                )
                """
            )
        )
        db.execute(text("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_status"))
        db.execute(
            text(
                """
                ALTER TABLE app.memory_cards
                ADD CONSTRAINT chk_memory_status CHECK (
                  status IN (
                    'pending_user_review', 'active', 'edited_by_user', 'deleted_by_user',
                    'rejected_by_guardrail', 'merged_duplicate', 'deleted_by_system'
                  )
                )
                """
            )
        )
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS app.memory_card_audit_events (
                  event_id text PRIMARY KEY,
                  memory_card_id text NOT NULL REFERENCES app.memory_cards(card_id) ON DELETE CASCADE,
                  user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
                  action text NOT NULL,
                  old_value jsonb,
                  new_value jsonb,
                  created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        db.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_cards_user_canonical_key_active
                ON app.memory_cards (user_id, canonical_key)
                WHERE canonical_key IS NOT NULL
                  AND status IN ('pending_user_review', 'active', 'edited_by_user')
                """
            )
        )
        db.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_cards_user_session_type_title
                ON app.memory_cards (user_id, source_session_id, memory_type, title)
                WHERE source_session_id IS NOT NULL
                """
            )
        )
        db.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_cards_user_status
                ON app.memory_cards (user_id, status, created_at DESC)
                """
            )
        )
        db.commit()
        _SCHEMA_ENSURED = True


def _candidate_items(extraction: ExtractionResult | dict[str, Any]) -> Iterable[MemoryCandidate | dict[str, Any]]:
    if isinstance(extraction, ExtractionResult):
        return extraction.candidate_cards
    return extraction.get("candidate_cards", []) or []


def _candidate_value(candidate: MemoryCandidate | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(candidate, MemoryCandidate):
        return getattr(candidate, key, default)
    return candidate.get(key, default)


def _candidate_to_atomic(candidate: AtomicMemoryCandidate | dict[str, Any]) -> AtomicMemoryCandidate | None:
    if isinstance(candidate, AtomicMemoryCandidate):
        return candidate

    memory_type = str(candidate.get("memory_type") or "").strip()
    display_text = str(candidate.get("display_text") or candidate.get("content") or "").strip()
    if not memory_type or not display_text:
        return None

    display_category = str(candidate.get("display_category") or candidate.get("title") or "Ký ức").strip()
    subject = str(candidate.get("subject") or display_text[:80]).strip()
    predicate = str(candidate.get("predicate") or display_text[:120]).strip()
    metadata = dict(candidate.get("metadata") or {})
    evidence = list(candidate.get("evidence_message_ids") or metadata.get("evidence_message_ids") or [])
    return AtomicMemoryCandidate(
        memory_type=memory_type,  # type: ignore[arg-type]
        display_category=display_category,
        subject=subject,
        predicate=predicate,
        display_text=display_text,
        confidence=float(candidate.get("confidence") or 0.7),
        is_temporary=bool(candidate.get("is_temporary") or memory_type in {"current_stressor", "temporary_context"}),
        ttl_days=candidate.get("ttl_days") or metadata.get("ttl_days"),
        evidence_message_ids=[str(item) for item in evidence if str(item or "").strip()],
        source_session_id=candidate.get("source_session_id"),
        sensitivity_level=str(candidate.get("sensitivity_level") or "low"),  # type: ignore[arg-type]
        metadata=metadata,
    )


def _active_status_filter(stmt):
    return stmt.where(MemoryCard.status.in_(["pending_user_review", "active", "edited_by_user"]))


def _find_duplicate_by_key(db: Session, user_id: str, canonical_key: str) -> MemoryCard | None:
    return db.scalar(
        _active_status_filter(
            select(MemoryCard).where(
                MemoryCard.user_id == user_id,
                MemoryCard.canonical_key == canonical_key,
            )
        ).limit(1)
    )


def _find_duplicate_by_text(
    db: Session,
    user_id: str,
    memory_type: str,
    normalized_text: str,
) -> MemoryCard | None:
    """Secondary dedup: same visible text for the same user + type = same memory.

    The canonical key is derived from LLM-generated subject/predicate which can
    vary between extraction calls for the same topic, producing different keys
    but identical display text. This check catches that case.
    """
    if not normalized_text:
        return None
    return db.scalar(
        _active_status_filter(
            select(MemoryCard).where(
                MemoryCard.user_id == user_id,
                MemoryCard.memory_type == memory_type,
                MemoryCard.normalized_text == normalized_text,
            )
        ).limit(1)
    )


def _deleted_recently(db: Session, user_id: str, canonical_key: str) -> bool:
    cutoff = get_now().replace(tzinfo=None) - timedelta(days=30)
    row = db.scalar(
        select(MemoryCard)
        .where(
            MemoryCard.user_id == user_id,
            MemoryCard.canonical_key == canonical_key,
            MemoryCard.status == "deleted_by_user",
            MemoryCard.updated_at >= cutoff,
        )
        .limit(1)
    )
    return row is not None


def _apply_atomic_fields(card: MemoryCard, candidate: AtomicMemoryCandidate, canonical_key: str, now) -> None:
    card.memory_type = candidate.memory_type
    card.display_category = candidate.display_category
    card.subject = candidate.subject
    card.predicate = candidate.predicate
    card.canonical_key = canonical_key
    card.normalized_text = normalize_memory_text(candidate.display_text)
    card.is_temporary = bool(candidate.is_temporary)
    card.evidence_message_ids = merge_evidence_message_ids(card.evidence_message_ids, candidate.evidence_message_ids)
    card.last_mentioned_at = now
    if card.first_mentioned_at is None:
        card.first_mentioned_at = now
    if candidate.ttl_days:
        card.expires_at = now + timedelta(days=int(candidate.ttl_days))


def upsert_memory_candidate(
    db: Session,
    *,
    user_id: str,
    candidate: AtomicMemoryCandidate,
) -> MemoryCard | None:
    ensure_memory_card_tables(db)
    canonical_key = build_memory_canonical_key(
        user_id=user_id,
        memory_type=candidate.memory_type,
        subject=candidate.subject,
        predicate=candidate.predicate,
    )

    if _deleted_recently(db, user_id, canonical_key):
        return None

    display_review = validate_user_facing_memory_copy(
        {"title": candidate.display_category, "body": candidate.display_text}
    )
    if not display_review["approved"]:
        return None

    review = review_memory_candidate(candidate.memory_type, candidate.display_category, candidate.display_text, candidate.confidence)
    if not review["approved"]:
        return None

    now = get_now().replace(tzinfo=None)
    existing = _find_duplicate_by_key(db, user_id, canonical_key)
    if existing is None:
        # Secondary dedup: LLM may produce different subject/predicate for the
        # same visible sentence → different canonical_key but identical display.
        norm = normalize_memory_text(candidate.display_text)
        existing = _find_duplicate_by_text(db, user_id, candidate.memory_type, norm)
        if existing is not None:
            # Adopt the new canonical_key so future lookups hit the faster path.
            existing.canonical_key = canonical_key
    metadata = dict(candidate.metadata or {})
    metadata.update(
        {
            "atomic_memory_version": "atomic_memory_v1",
            "sensitivity_level": candidate.sensitivity_level,
            "ttl_days": candidate.ttl_days,
        }
    )

    if existing is not None:
        existing.mention_count = int(existing.mention_count or 1) + 1
        existing.confidence = min(0.95, max(float(existing.confidence or 0.0), float(candidate.confidence or 0.0) + 0.03))
        if existing.status != "edited_by_user" and len(candidate.display_text) <= len(existing.content or "") + 20:
            existing.title = candidate.display_category
            existing.content = candidate.display_text
        _apply_atomic_fields(existing, candidate, canonical_key, now)
        existing.metadata_json = {**dict(existing.metadata_json or {}), **metadata}
        db.flush()
        return existing

    auto_active = bool(get_settings().memory_card_auto_active)
    card = MemoryCard(
        card_id=make_id("mc"),
        user_id=user_id,
        source_session_id=candidate.source_session_id,
        memory_type=candidate.memory_type,
        title=candidate.display_category,
        content=candidate.display_text,
        confidence=float(candidate.confidence),
        canonical_key=canonical_key,
        normalized_text=normalize_memory_text(candidate.display_text),
        mention_count=1,
        first_mentioned_at=now,
        last_mentioned_at=now,
        evidence_message_ids=list(candidate.evidence_message_ids or []),
        display_category=candidate.display_category,
        subject=candidate.subject,
        predicate=candidate.predicate,
        is_temporary=bool(candidate.is_temporary),
        status="active" if auto_active else "pending_user_review",
        safety_review_status="approved",
        personalization_disabled=False,
        expires_at=(now + timedelta(days=int(candidate.ttl_days))) if candidate.ttl_days else None,
        metadata_json=metadata,
    )
    savepoint = db.begin_nested()
    try:
        db.add(card)
        db.flush()
        savepoint.commit()
        return card
    except IntegrityError:
        savepoint.rollback()
        # Duplicate detected by either the canonical_key index or the
        # normalized_text index — find the existing card by either path.
        existing = _find_duplicate_by_key(db, user_id, canonical_key)
        if existing is None:
            norm = normalize_memory_text(candidate.display_text)
            existing = _find_duplicate_by_text(db, user_id, candidate.memory_type, norm)
        if existing is None:
            raise
        existing.canonical_key = canonical_key
        existing.mention_count = int(existing.mention_count or 1) + 1
        existing.evidence_message_ids = merge_evidence_message_ids(existing.evidence_message_ids, candidate.evidence_message_ids)
        existing.last_mentioned_at = now
        db.flush()
        return existing


def create_cards_from_candidates(
    db: Session,
    user_id: str,
    extraction: ExtractionResult | dict[str, Any],
) -> list[MemoryCard]:
    ensure_memory_card_tables(db)
    cards: list[MemoryCard] = []
    for candidate in _candidate_items(extraction):
        atomic = _candidate_to_atomic(candidate)
        if atomic is None:
            continue
        card = upsert_memory_candidate(db, user_id=user_id, candidate=atomic)
        if card is not None:
            cards.append(card)
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
    ensure_memory_card_tables(db)
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
        display_review = validate_user_facing_memory_copy({"title": card.title, "body": new_content.strip()})
        if not display_review["approved"]:
            raise ValueError(f"edit rejected by display guardrail: {display_review['rejection_reason']}")
        review = review_memory_candidate(card.memory_type, card.title, new_content, card.confidence)
        if not review["approved"]:
            raise ValueError(f"edit rejected by guardrail: {review['rejection_reason']}")
        card.content = new_content.strip()
        card.normalized_text = normalize_memory_text(card.content)
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
    cache_delete(profile_cache_key(user_id))
    return card


_VALID_MEMORY_TYPES = frozenset({
    "background", "support_style", "current_stressor", "coping_history",
    "preference", "persona_preference", "nutrition_pattern", "temporary_context",
    "event_memory", "support_insight", "relationship_context", "goal_or_hope",
    "emotional_pattern",
})


def get_user_cards(db: Session, user_id: str, *, include_deleted: bool = False) -> list[MemoryCard]:
    ensure_memory_card_tables(db)
    stmt = select(MemoryCard).where(MemoryCard.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(
            MemoryCard.status.notin_(
                ["deleted_by_user", "deleted_by_system", "rejected_by_guardrail", "merged_duplicate"]
            )
        )
    stmt = stmt.order_by(MemoryCard.created_at.desc(), MemoryCard.card_id.desc())
    cards = list(db.scalars(stmt).all())
    if include_deleted:
        return cards
    visible: list[MemoryCard] = []
    changed = False
    for card in cards:
        # Legacy rows with unknown memory_type (e.g. emotional_pattern) violate the
        # chk_memory_type constraint added later — never attempt to UPDATE them.
        if card.memory_type not in _VALID_MEMORY_TYPES:
            continue
        # Only permanently reject cards with truly empty content — display_copy
        # now truncates to fit MAX_TITLE_CHARS/MAX_BODY_CHARS, so a card that
        # previously failed because its legacy title was too long will now pass.
        if not str(card.content or "").strip():
            card.status = "rejected_by_guardrail"
            card.safety_review_status = "rejected"
            metadata = dict(card.metadata_json or {})
            metadata["guardrail_rejection_reason"] = "empty_content"
            card.metadata_json = metadata
            changed = True
            continue
        if display_copy_from_card(card) is None:
            # Validation still fails even after truncation — skip for this request
            # but do NOT permanently mark rejected (could be a transient rule change).
            continue
        visible.append(card)
    if changed:
        db.flush()
        db.commit()
    return visible


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
