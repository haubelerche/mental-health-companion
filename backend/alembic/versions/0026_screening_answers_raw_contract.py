"""Harden screening_answers raw traceability contract.

Revision ID: 0026_screening_raw_contract
Revises: 0025_onboarding_tour_states
Create Date: 2026-05-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0026_screening_raw_contract"
down_revision = "0025_onboarding_tour_states"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, column_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {row["name"] for row in inspector.get_columns(table_name, schema="app")}
    if column_name not in existing_columns:
        op.add_column(table_name, column, schema="app")


def upgrade() -> None:
    _add_column_if_missing(
        "screening_answers",
        "screening_type",
        sa.Column("screening_type", sa.String(length=10), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "question_id",
        sa.Column("question_id", sa.String(length=32), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "question_key",
        sa.Column("question_key", sa.String(length=32), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "answer_value",
        sa.Column("answer_value", sa.Integer(), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "answer_label",
        sa.Column("answer_label", sa.String(length=120), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "question_text_version",
        sa.Column("question_text_version", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "answer_options_version",
        sa.Column("answer_options_version", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "session_id",
        sa.Column("session_id", sa.String(length=50), nullable=True),
    )
    _add_column_if_missing(
        "screening_answers",
        "locale",
        sa.Column("locale", sa.String(length=16), nullable=True),
    )
    op.execute("UPDATE app.screening_answers SET screening_type = instrument_id WHERE screening_type IS NULL")
    op.execute("UPDATE app.screening_answers SET locale = 'vi-VN' WHERE locale IS NULL")
    op.alter_column("screening_answers", "screening_type", schema="app", existing_type=sa.String(length=10), nullable=False)
    op.alter_column("screening_answers", "locale", schema="app", existing_type=sa.String(length=16), nullable=False)


def downgrade() -> None:
    raise RuntimeError("0026_screening_answers_raw_contract is intentionally irreversible.")
