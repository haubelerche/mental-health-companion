"""Retire legacy memory cards in favor of mem0 memories.

Revision ID: 0023_retire_memory_cards
Revises: 0022_public_to_app
Create Date: 2026-05-10
"""

from __future__ import annotations

from alembic import op


revision = "0023_retire_memory_cards"
down_revision = "0022_public_to_app"
branch_labels = None
depends_on = None

BACKUP_SCHEMA = "schema_cleanup_backup_20260510"
RETIRED_TABLES = (
    "memory_card_audit_events",
    "memory_cards",
)


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {BACKUP_SCHEMA}")
    for table in RETIRED_TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF to_regclass('app.{table}') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1
                    FROM pg_constraint con
                    JOIN pg_class dep_rel ON dep_rel.oid = con.conrelid
                    JOIN pg_namespace dep_ns ON dep_ns.oid = dep_rel.relnamespace
                    WHERE con.contype = 'f'
                      AND con.confrelid = to_regclass('app.{table}')
                      AND NOT (dep_ns.nspname = 'app' AND dep_rel.relname = '{table}')
                ) THEN
                    RAISE EXCEPTION 'Cannot retire app.%: foreign-key dependencies still exist', '{table}';
                END IF;
                EXECUTE 'CREATE TABLE IF NOT EXISTS {BACKUP_SCHEMA}.app_{table} '
                        || '(LIKE app.{table} INCLUDING ALL)';
                EXECUTE 'INSERT INTO {BACKUP_SCHEMA}.app_{table} '
                        || 'SELECT * FROM app.{table} ON CONFLICT DO NOTHING';
                EXECUTE 'DROP TABLE IF EXISTS app.{table} RESTRICT';
              END IF;
            END $$;
            """
        )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'app'
              AND table_name = 'user_notification_preferences'
              AND column_name = 'memory_card_review'
          ) THEN
            ALTER TABLE app.user_notification_preferences DROP COLUMN memory_card_review;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "0023_retire_memory_cards is intentionally irreversible. "
        f"Restore from {BACKUP_SCHEMA} manually if rollback is required."
    )
