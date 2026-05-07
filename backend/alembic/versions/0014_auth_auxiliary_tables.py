"""Create app auth auxiliary tables.

Revision ID: 0014_auth_auxiliary_tables
Revises: 0013_harden_app_schema_contract
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


revision = "0014_auth_auxiliary_tables"
down_revision = "0013_harden_app_schema_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public, extensions")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_identities (
          identity_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          provider text NOT NULL,
          provider_user_id text NOT NULL,
          provider_email text,
          provider_name text,
          provider_picture_url text,
          provider_email_verified_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_user_identity_provider_uid UNIQUE (provider, provider_user_id),
          CONSTRAINT uq_user_identity_user_provider UNIQUE (user_id, provider)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.email_verification_tokens (
          token_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          token_hash text NOT NULL UNIQUE,
          expires_at timestamptz NOT NULL,
          used_at timestamptz,
          resend_count integer NOT NULL DEFAULT 0,
          last_sent_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.password_reset_tokens (
          token_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          token_hash text NOT NULL UNIQUE,
          expires_at timestamptz NOT NULL,
          used_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'app.user_identities'::regclass
              AND tgname = 'trg_user_identities_updated_at'
          )
          THEN
            CREATE TRIGGER trg_user_identities_updated_at
            BEFORE UPDATE ON app.user_identities
            FOR EACH ROW EXECUTE FUNCTION app.set_updated_at();
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app.password_reset_tokens")
    op.execute("DROP TABLE IF EXISTS app.email_verification_tokens")
    op.execute("DROP TABLE IF EXISTS app.user_identities")
