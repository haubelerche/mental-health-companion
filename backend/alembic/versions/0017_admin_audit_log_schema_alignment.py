"""Align admin_audit_log schema with ORM contract.

Revision ID: 0017_admin_audit_log_schema_alignment
Revises: 0016_create_app_feature_tables
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_admin_audit_align"
down_revision = "0016_create_app_feature_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Ensure created_at exists even on older environments that used `timestamp`.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'app' AND table_name = 'admin_audit_log'
              ) THEN
                IF NOT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = 'app' AND table_name = 'admin_audit_log' AND column_name = 'created_at'
                ) THEN
                  ALTER TABLE app.admin_audit_log
                    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
                END IF;

                IF EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema = 'app' AND table_name = 'admin_audit_log' AND column_name = 'timestamp'
                ) THEN
                  UPDATE app.admin_audit_log
                    SET created_at = COALESCE(created_at, "timestamp");
                END IF;
              END IF;
            END $$;
            """
        )
    )

    # Ensure ip_address uses inet when the column exists.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'app' AND table_name = 'admin_audit_log' AND column_name = 'ip_address'
              ) THEN
                ALTER TABLE app.admin_audit_log
                  ALTER COLUMN ip_address TYPE inet
                  USING NULLIF(ip_address::text, '')::inet;
              END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    # Intentionally no-op: this migration normalizes schema shape safely.
    return
