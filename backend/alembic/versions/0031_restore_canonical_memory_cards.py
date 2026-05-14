"""Restore canonical user-facing memory cards.

Revision ID: 0031_restore_memory_cards
Revises: 0030_advisor_runtime_alignment
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op


revision = "0031_restore_memory_cards"
down_revision = "0030_advisor_runtime_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.memory_cards (
          card_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          source_session_id text REFERENCES app.conversations(session_id) ON DELETE SET NULL,
          memory_type text NOT NULL,
          title text NOT NULL,
          content text NOT NULL,
          confidence double precision,
          status text NOT NULL DEFAULT 'pending_user_review',
          safety_review_status text NOT NULL DEFAULT 'pending',
          personalization_disabled boolean NOT NULL DEFAULT false,
          expires_at timestamptz,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_memory_type CHECK (
            memory_type IN (
              'support_style', 'preference', 'emotional_pattern', 'coping_history',
              'current_stressor', 'nutrition_pattern', 'kindness_pattern',
              'persona_preference'
            )
          ),
          CONSTRAINT chk_memory_status CHECK (
            status IN (
              'pending_user_review', 'active', 'edited_by_user',
              'deleted_by_user', 'rejected_by_guardrail'
            )
          ),
          CONSTRAINT chk_safety_review_status CHECK (
            safety_review_status IN ('pending', 'approved', 'rejected')
          )
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_cards_user_session_type_title
        ON app.memory_cards (user_id, source_session_id, memory_type, title)
        WHERE source_session_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_cards_user_status
        ON app.memory_cards (user_id, status, created_at DESC)
        """
    )
    op.execute(
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
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_card_audit_events_card
        ON app.memory_card_audit_events (memory_card_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_memory_card_audit_events_card")
    op.execute("DROP TABLE IF EXISTS app.memory_card_audit_events")
    op.execute("DROP INDEX IF EXISTS app.idx_memory_cards_user_status")
    op.execute("DROP INDEX IF EXISTS app.uq_memory_cards_user_session_type_title")
    op.execute("DROP TABLE IF EXISTS app.memory_cards")
