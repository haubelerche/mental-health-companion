"""Add safety guardrail columns to therapy_letters and create letter_review_events.

Revision ID: 0020_letter_guardrail_schema
Revises: 0019_sync_outbox_worker_columns
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0020_letter_guardrail_schema"
down_revision = "0019_sync_outbox_worker_columns"
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


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names(schema=APP_SCHEMA)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    # --- therapy_letters: new guardrail columns -------------------------
    new_cols = [
        ("review_status", sa.Column("review_status", sa.String(40), nullable=False, server_default="not_reviewed")),
        ("review_reason_code", sa.Column("review_reason_code", sa.String(80), nullable=True)),
        ("content_masked", sa.Column("content_masked", sa.Text(), nullable=True)),
        ("safety_event_id", sa.Column("safety_event_id", sa.String(50), nullable=True)),
        ("reviewed_at", sa.Column("reviewed_at", sa.DateTime(), nullable=True)),
    ]
    for col_name, col_def in new_cols:
        if not _has_column("therapy_letters", col_name):
            op.add_column("therapy_letters", col_def, schema=APP_SCHEMA)

    # --- letter_review_events: new audit table --------------------------
    if not _table_exists("letter_review_events"):
        op.create_table(
            "letter_review_events",
            sa.Column("event_id", sa.String(50), primary_key=True),
            sa.Column("letter_id", sa.String(50), sa.ForeignKey(f"{APP_SCHEMA}.therapy_letters.letter_id"), nullable=False),
            sa.Column("user_id", sa.String(50), sa.ForeignKey(f"{APP_SCHEMA}.users.user_id"), nullable=False),
            sa.Column("validator_version", sa.String(30), nullable=False),
            sa.Column("verdict", sa.String(50), nullable=False),
            sa.Column("reason_codes", sa.JSON(), nullable=True),
            sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            schema=APP_SCHEMA,
        )
        op.create_index(
            "ix_letter_review_events_letter_id",
            "letter_review_events",
            ["letter_id"],
            schema=APP_SCHEMA,
        )
        op.create_index(
            "ix_letter_review_events_user_id",
            "letter_review_events",
            ["user_id"],
            schema=APP_SCHEMA,
        )


def downgrade() -> None:
    if _table_exists("letter_review_events"):
        op.drop_index("ix_letter_review_events_user_id", "letter_review_events", schema=APP_SCHEMA)
        op.drop_index("ix_letter_review_events_letter_id", "letter_review_events", schema=APP_SCHEMA)
        op.drop_table("letter_review_events", schema=APP_SCHEMA)

    for col_name in ("reviewed_at", "safety_event_id", "content_masked", "review_reason_code", "review_status"):
        if _has_column("therapy_letters", col_name):
            op.drop_column("therapy_letters", col_name, schema=APP_SCHEMA)
