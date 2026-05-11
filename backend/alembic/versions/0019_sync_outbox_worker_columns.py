"""Align sync_outbox columns used by workers.

Revision ID: 0019_sync_outbox_worker_columns
Revises: 0018_sync_outbox_identity_contract
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_sync_outbox_worker_columns"
down_revision = "0018_outbox_identity"
branch_labels = None
depends_on = None


APP_SCHEMA = "app"


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(
        col["name"] == column_name
        for col in inspector.get_columns(table_name, schema=APP_SCHEMA)
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    if not _has_column("sync_outbox", "error_message"):
        op.add_column(
            "sync_outbox",
            sa.Column("error_message", sa.Text(), nullable=True),
            schema=APP_SCHEMA,
        )
    if not _has_column("sync_outbox", "processing_started_at"):
        op.add_column(
            "sync_outbox",
            sa.Column("processing_started_at", sa.DateTime(), nullable=True),
            schema=APP_SCHEMA,
        )


def downgrade() -> None:
    if _has_column("sync_outbox", "processing_started_at"):
        op.drop_column("sync_outbox", "processing_started_at", schema=APP_SCHEMA)
    if _has_column("sync_outbox", "error_message"):
        op.drop_column("sync_outbox", "error_message", schema=APP_SCHEMA)
