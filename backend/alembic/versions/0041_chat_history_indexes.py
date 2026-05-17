"""Add indexes for chat history reads.

Revision ID: 0041_chat_history_indexes
Revises: 0040_analyst_evidence_refs
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0041_chat_history_indexes"
down_revision = "0040_analyst_evidence_refs"
branch_labels = None
depends_on = None


def _has_index(bind: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    if not _has_index(bind, table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_once(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    if _has_index(bind, table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    _create_index_once(
        "conversations",
        "idx_conversations_user_last_active",
        ["user_id", "deleted_at", "last_message_at"],
    )
    _create_index_once(
        "messages",
        "idx_messages_session_created",
        ["session_id", "created_at"],
    )
    _create_index_once(
        "messages",
        "idx_messages_session_role_created",
        ["session_id", "role", "created_at"],
    )


def downgrade() -> None:
    _drop_index_once("messages", "idx_messages_session_role_created")
    _drop_index_once("messages", "idx_messages_session_created")
    _drop_index_once("conversations", "idx_conversations_user_last_active")
