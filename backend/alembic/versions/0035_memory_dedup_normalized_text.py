"""Add unique index on (user_id, memory_type, normalized_text) for dedup.

Revision ID: 0035_memory_dedup_normalized_text
Revises: 0034_memory_type_extended
Create Date: 2026-05-14

Root cause fixed: the LLM extraction produces different subject/predicate for
the same visible sentence on separate calls, yielding different canonical_keys
but identical display text, which creates duplicate cards.

This migration:
  1. Merges any existing duplicate rows that have identical normalized_text
     by keeping the earliest card and summing mention_count.
  2. Creates a unique partial index on (user_id, memory_type, normalized_text)
     so concurrent background threads cannot race-insert the same card.
"""

from __future__ import annotations

from alembic import op


revision = "0035_memory_text_dedup"
down_revision = "0034_memory_type_extended"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: mark duplicate rows as merged, update mention_count on the keeper.
    # Uses two CTEs: one to rank and sum, one to update the keeper, then the
    # outer UPDATE marks the losers as merged_duplicate.
    op.execute(
        """
        WITH ranked AS (
          SELECT
            card_id,
            created_at,
            mention_count,
            normalized_text,
            user_id,
            memory_type,
            ROW_NUMBER() OVER (
              PARTITION BY user_id, memory_type, normalized_text
              ORDER BY created_at ASC
            ) AS rn,
            FIRST_VALUE(card_id) OVER (
              PARTITION BY user_id, memory_type, normalized_text
              ORDER BY created_at ASC
            ) AS keeper_id,
            SUM(mention_count) OVER (
              PARTITION BY user_id, memory_type, normalized_text
            ) AS total_mentions
          FROM app.memory_cards
          WHERE normalized_text IS NOT NULL
            AND status IN ('pending_user_review', 'active', 'edited_by_user')
        )
        UPDATE app.memory_cards mc
        SET
          mention_count = r.total_mentions,
          status        = CASE WHEN r.rn = 1 THEN mc.status ELSE 'merged_duplicate' END
        FROM ranked r
        WHERE mc.card_id = r.card_id
          AND r.total_mentions > 1
        """
    )

    # Step 2: unique partial index — one active card per visible sentence.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_cards_user_type_norm_text
        ON app.memory_cards (user_id, memory_type, normalized_text)
        WHERE normalized_text IS NOT NULL
          AND status IN ('pending_user_review', 'active', 'edited_by_user')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_memory_cards_user_type_norm_text")
