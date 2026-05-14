"""Add display-copy support fields for canonical memory cards.

Revision ID: 0032_memory_card_display_copy
Revises: 0031_restore_memory_cards
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op


revision = "0032_memory_card_display_copy"
down_revision = "0031_restore_memory_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE app.memory_cards ADD COLUMN IF NOT EXISTS expires_at timestamptz")
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


def downgrade() -> None:
    op.execute("ALTER TABLE app.memory_cards DROP CONSTRAINT IF EXISTS chk_memory_type")
    op.execute(
        """
        ALTER TABLE app.memory_cards
        ADD CONSTRAINT chk_memory_type CHECK (
          memory_type IN (
            'preference', 'emotional_pattern', 'coping_history',
            'current_stressor', 'nutrition_pattern', 'kindness_pattern',
            'persona_preference'
          )
        )
        """
    )
    op.execute("ALTER TABLE app.memory_cards DROP COLUMN IF EXISTS expires_at")
