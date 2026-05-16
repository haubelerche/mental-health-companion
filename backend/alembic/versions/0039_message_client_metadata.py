"""Add client metadata to chat messages.

Revision ID: 0039_message_client_metadata
Revises: 0038_fix_archive_id_sqlite_autoincrement
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0039_message_client_metadata"
down_revision = "0038_fix_archive_id_sqlite_autoincrement"
branch_labels = None
depends_on = None


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "messages", "metadata"):
        return
    op.add_column(
        "messages",
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "messages", "metadata"):
        op.drop_column("messages", "metadata")
