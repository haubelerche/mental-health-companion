"""Extend chk_memory_type and add normalized_text dedup index.

Revision ID: 0034_memory_type_extended
Revises: 0033_memory_card_atomic_dedupe
Create Date: 2026-05-14

Changes:
  1. chk_memory_type constraint already included in 0033 (no-op here).
  2. Unique partial index on (user_id, memory_type, normalized_text) prevents
     duplicate rows when two background extraction threads race to insert the
     same visible memory sentence for the same user.
  3. Deduplicate any existing rows that already have identical normalized_text
     by keeping the earliest card and merging mention_count.
"""

from __future__ import annotations

from alembic import op


revision = "0034_memory_type_extended"
down_revision = "0033_memory_card_atomic_dedupe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge existing duplicate rows (same user_id + memory_type + normalized_text).
    # Keep the oldest card, add mention_counts together, then delete the duplicates.
    op.execute(
        """
        WITH ranked AS (
          SELECT
            card_id,
            user_id,
            memory_type,
            normalized_text,
            mention_count,
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
        ),
        updates AS (
          UPDATE app.memory_cards mc
          SET mention_count = r.total_mentions
          FROM ranked r
          WHERE mc.card_id = r.keeper_id
            AND r.rn = 1
            AND r.total_mentions > mc.mention_count
          RETURNING mc.card_id
        )
        UPDATE app.memory_cards
        SET status = 'merged_duplicate'
        WHERE card_id IN (
          SELECT card_id FROM ranked WHERE rn > 1
        )
        """
    )

    # Unique partial index: one active card per (user, type, normalized text).
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
