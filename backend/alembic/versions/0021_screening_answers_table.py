"""Create app.screening_answers — backend-only raw questionnaire answer store.

Separates raw PHQ-9/GAD-7 answers from clinical_profiles coverage fields so
clinical_profiles.phq*_coverage stores only boolean coverage metadata.

Revision ID: 0021_screening_answers_table
Revises: 0020_letter_guardrail_schema
Create Date: 2026-05-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_screening_answers_table"
down_revision = "0020_letter_guardrail_schema"
branch_labels = None
depends_on = None

APP_SCHEMA = "app"


def _table_exists(table: str, schema: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, table, schema=schema)


def upgrade() -> None:
    if not _table_exists("screening_answers", APP_SCHEMA):
        op.create_table(
            "screening_answers",
            sa.Column("answer_id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column(
                "user_id",
                sa.String(),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("instrument_id", sa.String(10), nullable=False),
            sa.Column("raw_score", sa.Integer(), nullable=False),
            sa.Column(
                "answers",
                sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="{}",
            ),
            sa.Column(
                "submitted_at",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("answer_id"),
            sa.CheckConstraint(
                "instrument_id IN ('phq9','gad7')",
                name="ck_screening_answers_instrument",
            ),
            schema=APP_SCHEMA,
        )
        op.create_index(
            "idx_screening_answers_user_instrument",
            "screening_answers",
            ["user_id", "instrument_id", "submitted_at"],
            schema=APP_SCHEMA,
        )


def downgrade() -> None:
    op.drop_index(
        "idx_screening_answers_user_instrument",
        table_name="screening_answers",
        schema=APP_SCHEMA,
        if_exists=True,
    )
    op.drop_table("screening_answers", schema=APP_SCHEMA, if_exists=True)
