"""Retire empty legacy tables left by legacy external-screening branch.

Revision ID: 0037_ext_screening_cleanup
Revises: 0036_ext_screening
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op


revision = "0037_ext_screening_cleanup"
down_revision = "0036_ext_screening"
branch_labels = None
depends_on = None


def _drop_if_empty(table_name: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
          row_count BIGINT;
        BEGIN
          IF to_regclass('app.{table_name}') IS NULL THEN
            RETURN;
          END IF;

          EXECUTE 'SELECT COUNT(*) FROM app.{table_name}' INTO row_count;
          IF row_count <> 0 THEN
            RAISE EXCEPTION 'Refusing to drop non-empty legacy table app.{table_name}: % rows', row_count;
          END IF;

          EXECUTE 'DROP TABLE IF EXISTS app.{table_name} CASCADE';
        END $$;
        """
    )


def upgrade() -> None:
    op.execute("SET search_path TO app, extensions")
    for table_name in (
        "journal_entries",
        "journal_prompts",
        "bookmarks",
        "play_events",
        "risk_inference_log",
    ):
        _drop_if_empty(table_name)


def downgrade() -> None:
    pass
