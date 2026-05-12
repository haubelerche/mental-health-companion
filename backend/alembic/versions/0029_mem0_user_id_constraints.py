"""Enforce mem0 ownership contract and add expression indexes.

Revision ID: 0029_mem0_user_id_constraints
Revises: 0028_advisor_case_library, 0028_retire_journal_res_risk
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "0029_mem0_user_id_constraints"
down_revision = ("0028_advisor_case_library", "0028_retire_journal_res_risk")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute(
        """
        ALTER TABLE app.mem0_memories
        ADD CONSTRAINT ck_mem0_memories_payload_has_user_id
        CHECK (payload ? 'user_id')
        """
    )
    op.execute(
        """
        ALTER TABLE app.mem0_memories
        ADD CONSTRAINT ck_mem0_memories_payload_user_id_nonempty
        CHECK (COALESCE(payload->>'user_id', '') <> '')
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mem0_memories_payload_user_id
        ON app.mem0_memories ((payload->>'user_id'))
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mem0_memories_payload_created_at
        ON app.mem0_memories ((payload->>'created_at'))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_mem0_memories_payload_created_at")
    op.execute("DROP INDEX IF EXISTS app.idx_mem0_memories_payload_user_id")
    op.execute("ALTER TABLE app.mem0_memories DROP CONSTRAINT IF EXISTS ck_mem0_memories_payload_user_id_nonempty")
    op.execute("ALTER TABLE app.mem0_memories DROP CONSTRAINT IF EXISTS ck_mem0_memories_payload_has_user_id")
