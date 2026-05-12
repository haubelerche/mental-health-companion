"""Create onboarding tour state table.

Revision ID: 0025_onboarding_tour_states
Revises: 0024_retire_legacy_dupes
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "0025_onboarding_tour_states"
down_revision = "0024_retire_legacy_dupes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, extensions")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.onboarding_tour_states (
          user_id text PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
          status text NOT NULL DEFAULT 'not_started',
          variant text NOT NULL DEFAULT 'first_run',
          current_step_id text,
          completed_step_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          skipped_step_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          dismissed_at timestamptz,
          completed_at timestamptz,
          last_seen_at timestamptz,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_onboarding_tour_status CHECK (
            status IN (
              'not_started', 'available', 'in_progress', 'paused_for_safety',
              'completed', 'skipped', 'dismissed'
            )
          )
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app.onboarding_tour_states")
