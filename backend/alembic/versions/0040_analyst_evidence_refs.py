"""Add evidence_refs JSON column to analyst_signals.

Revision ID: 0040_analyst_evidence_refs
Revises: 0039_message_client_metadata
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0040_analyst_evidence_refs"
down_revision = "0039_message_client_metadata"
branch_labels = None
depends_on = None


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "analyst_signals", "evidence_refs"):
        return
    op.add_column(
        "analyst_signals",
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "analyst_signals", "evidence_refs"):
        op.drop_column("analyst_signals", "evidence_refs")
