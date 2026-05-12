"""Retire legacy schema duplicate tables.

Revision ID: 0024_retire_legacy_dupes
Revises: 0023_retire_memory_cards
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op


revision = "0024_retire_legacy_dupes"
down_revision = "0023_retire_memory_cards"
branch_labels = None
depends_on = None

BACKUP_SCHEMA = "schema_cleanup_backup_20260512"
RETIRE_TARGETS = (
    ("app", "screening_results"),
    ("app", "conversation_memories"),
    ("app", "mem0_memories_entities"),
    ("app", "mem0migrations"),
    ("app", "analyst_bundles"),
    ("app", "async_outbox"),
    ("public", "screening_results"),
    ("public", "conversation_memories"),
    ("public", "mem0_memories_entities"),
    ("public", "mem0migrations"),
    ("public", "memory_cards"),
    ("public", "memory_card_audit_events"),
    ("public", "analyst_bundles"),
    ("public", "async_outbox"),
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
                IF EXISTS (
                    SELECT 1
                    FROM pg_depend dep
                    JOIN pg_rewrite rw ON rw.oid = dep.objid
                    JOIN pg_class dep_rel ON dep_rel.oid = rw.ev_class
                    JOIN pg_namespace dep_ns ON dep_ns.oid = dep_rel.relnamespace
                    WHERE dep.refobjid = to_regclass('{schema_name}.{table_name}')
                      AND dep_rel.relkind IN ('v', 'm')
                      AND dep_ns.nspname <> '{BACKUP_SCHEMA}'
                ) THEN
                    RAISE EXCEPTION 'Cannot retire %.%: view/materialized-view dependencies still exist', '{schema_name}', '{table_name}';
                END IF;
                EXECUTE 'CREATE TABLE IF NOT EXISTS {BACKUP_SCHEMA}.{schema_name}_{table_name} '
                        || '(LIKE {schema_name}.{table_name} INCLUDING ALL)';
                EXECUTE 'INSERT INTO {BACKUP_SCHEMA}.{schema_name}_{table_name} '
                        || 'SELECT * FROM {schema_name}.{table_name} ON CONFLICT DO NOTHING';
                EXECUTE 'DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT';
              END IF;
            END $$;
            """
        )


def downgrade() -> None:
    raise RuntimeError(
        "0024_retire_legacy_schema_duplicates is intentionally irreversible. "
        f"Restore from {BACKUP_SCHEMA} manually if rollback is required."
    )
