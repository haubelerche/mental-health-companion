"""Retire journal/resource-engagement tables and merge risk_inference into crisis_logs.

Revision ID: 0028_retire_journal_res_risk
Revises: 0027_drop_memory_cards
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "0028_retire_journal_res_risk"
down_revision = "0027_drop_memory_cards"
branch_labels = None
depends_on = None

BACKUP_SCHEMA = "schema_cleanup_backup_20260512"
RETIRE_TARGETS = (
    ("app", "journal_entries"),
    ("app", "journal_prompts"),
    ("app", "bookmarks"),
    ("app", "play_events"),
    ("app", "risk_inference_log"),
)


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {BACKUP_SCHEMA}")
    for schema_name, table_name in RETIRE_TARGETS:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF to_regclass('{schema_name}.{table_name}') IS NOT NULL THEN
                IF EXISTS (
                    SELECT 1
                    FROM pg_constraint con
                    JOIN pg_class dep_rel ON dep_rel.oid = con.conrelid
                    JOIN pg_namespace dep_ns ON dep_ns.oid = dep_rel.relnamespace
                    WHERE con.contype = 'f'
                      AND con.confrelid = to_regclass('{schema_name}.{table_name}')
                      AND NOT (dep_ns.nspname = '{schema_name}' AND dep_rel.relname = '{table_name}')
                ) THEN
                    RAISE EXCEPTION 'Cannot retire %.%: foreign-key dependencies still exist', '{schema_name}', '{table_name}';
                END IF;
                EXECUTE 'CREATE TABLE IF NOT EXISTS {BACKUP_SCHEMA}.{schema_name}_{table_name} '
                        || '(LIKE {schema_name}.{table_name} INCLUDING ALL)';
                IF '{table_name}' = 'risk_inference_log' THEN
                  EXECUTE 'INSERT INTO {BACKUP_SCHEMA}.{schema_name}_{table_name} OVERRIDING SYSTEM VALUE '
                          || 'SELECT * FROM {schema_name}.{table_name}';
                ELSE
                  EXECUTE 'INSERT INTO {BACKUP_SCHEMA}.{schema_name}_{table_name} '
                          || 'SELECT * FROM {schema_name}.{table_name} ON CONFLICT DO NOTHING';
                END IF;
                EXECUTE 'DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT';
              END IF;
            END $$;
            """
        )


def downgrade() -> None:
    raise RuntimeError(
        "0028_retire_journal_resource_risk is intentionally irreversible. "
        f"Restore from {BACKUP_SCHEMA} manually if rollback is required."
    )
