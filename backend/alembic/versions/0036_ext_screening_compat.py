"""Compatibility marker for legacy external screening migration.

Revision ID: 0036_ext_screening
Revises: 0035_memory_text_dedup
Create Date: 2026-05-16

Some shared Supabase environments were stamped with this revision by an
older branch. The current canonical schema no longer needs an additional
DDL step here, but Alembic must still be able to resolve the revision before
it can run or verify migrations.
"""

from __future__ import annotations


revision = "0036_ext_screening"
down_revision = "0035_memory_text_dedup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
