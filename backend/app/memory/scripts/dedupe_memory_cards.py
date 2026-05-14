"""Dedupe canonical memory cards without printing sensitive memory text.

Usage:
  python -m app.memory.scripts.dedupe_memory_cards --dry-run
  python -m app.memory.scripts.dedupe_memory_cards --apply
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from sqlalchemy import select

from app.memory.normalization import (
    build_memory_canonical_key,
    merge_evidence_message_ids,
    normalize_memory_text,
)
from app.services.db.models import MemoryCard
from app.services.db.session import get_session_factory


ACTIVE_STATUSES = {"pending_user_review", "active", "edited_by_user"}


def _derived_key(card: MemoryCard) -> str:
    if card.canonical_key:
        return card.canonical_key
    subject = card.subject or card.normalized_text or card.content or ""
    predicate = card.predicate or card.normalized_text or card.content or ""
    return build_memory_canonical_key(
        user_id=card.user_id,
        memory_type=card.memory_type,
        subject=subject,
        predicate=predicate,
    )


def run(*, apply: bool = False) -> dict[str, int]:
    db = get_session_factory()()
    try:
        cards = list(
            db.scalars(
                select(MemoryCard)
                .where(MemoryCard.status.in_(sorted(ACTIVE_STATUSES)))
                .order_by(MemoryCard.user_id.asc(), MemoryCard.created_at.asc(), MemoryCard.card_id.asc())
            ).all()
        )
        groups: dict[tuple[str, str], list[MemoryCard]] = defaultdict(list)
        for card in cards:
            groups[(card.user_id, _derived_key(card))].append(card)

        duplicate_groups = 0
        duplicates_marked = 0
        for (_user_id, canonical_key), group in groups.items():
            if len(group) <= 1:
                continue
            duplicate_groups += 1
            canonical = next((card for card in group if card.status == "edited_by_user"), group[0])
            for card in group:
                if card.card_id == canonical.card_id:
                    continue
                duplicates_marked += 1
                if not apply:
                    continue
                canonical.canonical_key = canonical_key
                canonical.mention_count = int(canonical.mention_count or 1) + int(card.mention_count or 1)
                canonical.evidence_message_ids = merge_evidence_message_ids(
                    canonical.evidence_message_ids,
                    card.evidence_message_ids,
                )
                if canonical.last_mentioned_at is None or (
                    card.last_mentioned_at is not None and card.last_mentioned_at > canonical.last_mentioned_at
                ):
                    canonical.last_mentioned_at = card.last_mentioned_at
                if canonical.status != "edited_by_user" and card.status == "edited_by_user":
                    canonical.content = card.content
                    canonical.normalized_text = normalize_memory_text(card.content)
                card.status = "merged_duplicate"
        if apply:
            db.commit()
        return {
            "cards_scanned": len(cards),
            "duplicate_groups": duplicate_groups,
            "duplicates_marked": duplicates_marked,
            "applied": int(apply),
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Persist duplicate merges.")
    parser.add_argument("--dry-run", action="store_true", help="Report only. This is the default.")
    args = parser.parse_args()
    result = run(apply=bool(args.apply))
    print(result)


if __name__ == "__main__":
    main()
