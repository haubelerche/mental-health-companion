"""Normalize feature tables into the app schema.

Revision ID: 0015_feature_tables_app_schema
Revises: 0014_auth_auxiliary_tables
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


revision = "0015_feature_tables_app_schema"
down_revision = "0014_auth_auxiliary_tables"
branch_labels = None
depends_on = None


FEATURE_TABLES = (
    "heart_wallets",
    "heart_reward_events",
    "heart_spend_events",
    "streak_states",
    "nutrition_meal_checkins",
    "persona_unlock_states",
    "reward_store_items",
    "user_inventory_items",
    "memory_cards",
    "memory_card_audit_events",
    "knowledge_packs",
    "knowledge_cards",
    "user_knowledge_progress",
    "user_notifications",
    "user_notification_preferences",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, extensions")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_notification_preferences (
          user_id text PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
          letter_replied boolean NOT NULL DEFAULT true,
          letter_reported boolean NOT NULL DEFAULT true,
          memory_card_review boolean NOT NULL DEFAULT true,
          reward_earned boolean NOT NULL DEFAULT true,
          persona_unlocked boolean NOT NULL DEFAULT true,
          knowledge_completed boolean NOT NULL DEFAULT true,
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_notifications (
          notification_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          notification_type text NOT NULL,
          title text NOT NULL,
          body text NOT NULL,
          data jsonb NOT NULL DEFAULT '{}'::jsonb,
          is_read boolean NOT NULL DEFAULT false,
          read_at timestamptz,
          action_url text,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_notifications_user_created
          ON app.user_notifications (user_id, created_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_notifications_unread
          ON app.user_notifications (user_id, is_read)
          WHERE is_read = false;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_user_notifications_unread")
    op.execute("DROP INDEX IF EXISTS app.idx_user_notifications_user_created")
    op.execute("DROP TABLE IF EXISTS app.user_notifications")
    op.execute("DROP TABLE IF EXISTS app.user_notification_preferences")
