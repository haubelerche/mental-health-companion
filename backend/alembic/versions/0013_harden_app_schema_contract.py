"""Harden app schema contract for Supabase runtime.

Revision ID: 0013_harden_app_schema_contract
Revises: 0012_sync_core_schema
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


revision = "0013_harden_app_schema_contract"
down_revision = "0012_sync_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, extensions")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS app.user_profiles
          ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1,
          ADD COLUMN IF NOT EXISTS schema_version text NOT NULL DEFAULT 'v1',
          ADD COLUMN IF NOT EXISTS profile jsonb NOT NULL DEFAULT '{}'::jsonb,
          ADD COLUMN IF NOT EXISTS last_active_session_id text,
          ADD COLUMN IF NOT EXISTS summary_count integer NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
          ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('app.user_profiles') IS NOT NULL
             AND NOT EXISTS (
               SELECT 1
               FROM pg_constraint
               WHERE conrelid = 'app.user_profiles'::regclass
                 AND conname = 'ck_user_profiles_summary_count_gte0'
             )
          THEN
            ALTER TABLE app.user_profiles
              ADD CONSTRAINT ck_user_profiles_summary_count_gte0
              CHECK (summary_count >= 0);
          END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('app.user_profiles') IS NOT NULL
             AND NOT EXISTS (
               SELECT 1
               FROM pg_trigger
               WHERE tgrelid = 'app.user_profiles'::regclass
                 AND tgname = 'trg_user_profiles_updated_at'
             )
          THEN
            CREATE TRIGGER trg_user_profiles_updated_at
            BEFORE UPDATE ON app.user_profiles
            FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();
          END IF;
        END $$;
        """
    )

    op.execute(
        """
        ALTER TABLE IF EXISTS app.mood_checkins
          ADD COLUMN IF NOT EXISTS time_bucket text NOT NULL DEFAULT 'other';
        """
    )
    op.execute(
        """
        ALTER TABLE IF EXISTS app.mood_checkins
          DROP CONSTRAINT IF EXISTS uq_mood_per_day,
          DROP CONSTRAINT IF EXISTS mood_checkins_user_id_logged_date_key;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('app.mood_checkins') IS NOT NULL
             AND NOT EXISTS (
               SELECT 1
               FROM pg_constraint
               WHERE conrelid = 'app.mood_checkins'::regclass
                 AND conname = 'uq_mood_checkin_bucket'
             )
          THEN
            ALTER TABLE app.mood_checkins
              ADD CONSTRAINT uq_mood_checkin_bucket
              UNIQUE (user_id, logged_date, time_bucket);
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("SET search_path TO app, extensions")
    op.execute("ALTER TABLE IF EXISTS app.mood_checkins DROP CONSTRAINT IF EXISTS uq_mood_checkin_bucket")
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('app.mood_checkins') IS NOT NULL
             AND NOT EXISTS (
               SELECT 1
               FROM pg_constraint
               WHERE conrelid = 'app.mood_checkins'::regclass
                 AND conname = 'uq_mood_per_day'
             )
          THEN
            ALTER TABLE app.mood_checkins
              ADD CONSTRAINT uq_mood_per_day UNIQUE (user_id, logged_date);
          END IF;
        END $$;
        """
    )
