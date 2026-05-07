"""sync core schema

Revision ID: 0012_sync_core_schema
Revises: 0011_mood_checkin_time_bucket
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0012_sync_core_schema"
down_revision = "0011_mood_checkin_time_bucket"
branch_labels = None
depends_on = None


APP_SCHEMA = "app"


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name, schema=APP_SCHEMA)
    return any(col["name"] == column_name for col in cols)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public, extensions")
    # Rename only when legacy names still exist.
    if _has_column("messages", "tone_cam_xuc") and not _has_column("messages", "assistant_tone"):
        with op.batch_alter_table("messages", schema=APP_SCHEMA) as batch_op:
            batch_op.alter_column("tone_cam_xuc", new_column_name="assistant_tone")

    if _has_column("crisis_logs", "muc_do") and not _has_column("crisis_logs", "severity_level"):
        with op.batch_alter_table("crisis_logs", schema=APP_SCHEMA) as batch_op:
            batch_op.alter_column("muc_do", new_column_name="severity_level")

    # mood_checkins
    if not _has_column("mood_checkins", "source"):
        op.add_column(
            "mood_checkins",
            sa.Column("source", sa.String(length=20), nullable=False, server_default="self_report"),
            schema=APP_SCHEMA,
        )

    # conversation_memories
    if not _has_column("conversation_memories", "pii_checked"):
        op.add_column(
            "conversation_memories",
            sa.Column("pii_checked", sa.Boolean(), nullable=False, server_default="false"),
            schema=APP_SCHEMA,
        )
    if not _has_column("conversation_memories", "expires_at"):
        op.add_column(
            "conversation_memories",
            sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
            schema=APP_SCHEMA,
        )
    if not _has_column("conversation_memories", "source"):
        op.add_column(
            "conversation_memories",
            sa.Column("source", sa.String(length=20), nullable=False, server_default="chat_turn"),
            schema=APP_SCHEMA,
        )

    # user_profiles
    if not _has_column("user_profiles", "schema_version"):
        op.add_column(
            "user_profiles",
            sa.Column("schema_version", sa.String(length=10), nullable=False, server_default="v1"),
            schema=APP_SCHEMA,
        )
    if not _has_column("user_profiles", "last_active_session_id"):
        op.add_column(
            "user_profiles",
            sa.Column("last_active_session_id", sa.String(), nullable=True),
            schema=APP_SCHEMA,
        )
    if not _has_column("user_profiles", "summary_count"):
        op.add_column(
            "user_profiles",
            sa.Column("summary_count", sa.Integer(), nullable=False, server_default="0"),
            schema=APP_SCHEMA,
        )

    # clinical_profiles
    if not _has_column("clinical_profiles", "score_source"):
        op.add_column(
            "clinical_profiles",
            sa.Column("score_source", sa.String(length=30), nullable=True),
            schema=APP_SCHEMA,
        )
    if not _has_column("clinical_profiles", "model_version"):
        op.add_column(
            "clinical_profiles",
            sa.Column("model_version", sa.String(length=50), nullable=True),
            schema=APP_SCHEMA,
        )


def downgrade() -> None:
    if _has_column("clinical_profiles", "model_version"):
        op.drop_column("clinical_profiles", "model_version", schema=APP_SCHEMA)
    if _has_column("clinical_profiles", "score_source"):
        op.drop_column("clinical_profiles", "score_source", schema=APP_SCHEMA)
    if _has_column("user_profiles", "summary_count"):
        op.drop_column("user_profiles", "summary_count", schema=APP_SCHEMA)
    if _has_column("user_profiles", "last_active_session_id"):
        op.drop_column("user_profiles", "last_active_session_id", schema=APP_SCHEMA)
    if _has_column("user_profiles", "schema_version"):
        op.drop_column("user_profiles", "schema_version", schema=APP_SCHEMA)
    if _has_column("conversation_memories", "source"):
        op.drop_column("conversation_memories", "source", schema=APP_SCHEMA)
    if _has_column("conversation_memories", "expires_at"):
        op.drop_column("conversation_memories", "expires_at", schema=APP_SCHEMA)
    if _has_column("conversation_memories", "pii_checked"):
        op.drop_column("conversation_memories", "pii_checked", schema=APP_SCHEMA)
    if _has_column("mood_checkins", "source"):
        op.drop_column("mood_checkins", "source", schema=APP_SCHEMA)

    if _has_column("crisis_logs", "severity_level") and not _has_column("crisis_logs", "muc_do"):
        with op.batch_alter_table("crisis_logs", schema=APP_SCHEMA) as batch_op:
            batch_op.alter_column("severity_level", new_column_name="muc_do")

    if _has_column("messages", "assistant_tone") and not _has_column("messages", "tone_cam_xuc"):
        with op.batch_alter_table("messages", schema=APP_SCHEMA) as batch_op:
            batch_op.alter_column("assistant_tone", new_column_name="tone_cam_xuc")
