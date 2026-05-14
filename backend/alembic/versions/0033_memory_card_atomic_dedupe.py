"""Add atomic dedupe fields for compact memory cards.

Revision ID: 0033_memory_card_atomic_dedupe
Revises: 0032_memory_card_display_copy, 0032_analyst_pipeline_schema
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op


revision = "0033_memory_card_atomic_dedupe"
down_revision = ("0032_memory_card_display_copy", "0032_analyst_pipeline_schema")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS canonical_key text")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS normalized_text text")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS mention_count integer NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS first_mentioned_at timestamptz")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS last_mentioned_at timestamptz")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS evidence_message_ids jsonb NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS display_category text")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS subject text")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS predicate text")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS is_temporary boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS expires_at timestamptz")
    # Clean up rows with legacy types that are not carried forward.
    # 'kindness_pattern' existed in an earlier schema iteration and is not
    # part of the new atomic-memory model. Mark them as system-deleted.
    op.execute(
        """
        UPDATE app.memory_cards
        SET status = 'deleted_by_system'
        WHERE memory_type NOT IN (
          'background', 'support_style', 'current_stressor', 'coping_history',
          'preference', 'persona_preference', 'nutrition_pattern', 'temporary_context',
          'event_memory', 'support_insight', 'relationship_context', 'goal_or_hope',
          'emotional_pattern'
        )
        """
    )
    op.execute("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_type")
    op.execute(
        """
        ALTER TABLE app.memory_cards
        ADD CONSTRAINT chk_memory_type CHECK (
          memory_type IN (
            'background', 'support_style', 'current_stressor', 'coping_history',
            'preference', 'persona_preference', 'nutrition_pattern', 'temporary_context',
            'event_memory', 'support_insight', 'relationship_context', 'goal_or_hope',
            'emotional_pattern'
          )
        )
        """
    )
    op.execute("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_status")
    op.execute(
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
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_cards_user_canonical_key_active
        ON app.memory_cards (user_id, canonical_key)
        WHERE canonical_key IS NOT NULL
          AND status IN ('pending_user_review', 'active', 'edited_by_user')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_memory_cards_user_canonical_key_active")
    op.execute("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_status")
    op.execute(
        """
        ALTER TABLE app.memory_cards
        ADD CONSTRAINT chk_memory_status CHECK (
          status IN (
            'pending_user_review', 'active', 'edited_by_user',
            'deleted_by_user', 'rejected_by_guardrail'
          )
        )
        """
    )
    op.execute("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_type")
    op.execute(
        """
        ALTER TABLE app.memory_cards
        ADD CONSTRAINT chk_memory_type CHECK (
          memory_type IN (
            'support_style', 'preference', 'emotional_pattern', 'coping_history',
            'current_stressor', 'nutrition_pattern', 'kindness_pattern',
            'persona_preference'
          )
        )
        """
    )
    for column in (
        "canonical_key",
        "normalized_text",
        "mention_count",
        "first_mentioned_at",
        "last_mentioned_at",
        "evidence_message_ids",
        "display_category",
        "subject",
        "predicate",
        "is_temporary",
    ):
        op.execute(f"ALTER TABLE app.memory_cards DROP COLUMN IF EXISTS {column}")
