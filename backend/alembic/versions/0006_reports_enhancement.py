"""Add report categories and status tracking

Revision ID: 0006_reports_enhancement
Revises: 0005_letters_schema
Create Date: 2026-05-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_reports_enhancement"
down_revision = "0005_letters_schema"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {ix["name"] for ix in inspector.get_indexes(table_name)}


def upgrade() -> None:
    # Skip silently when the optional `reports` table is not present in this
    # environment. Older deployments seeded only via Base.metadata.create_all
    # never received a Report model, so the table genuinely does not exist
    # and there is nothing to enhance until a future migration creates it.
    if not _table_exists("reports"):
        return

    cols = _column_names("reports")
    if "report_category" not in cols:
        op.add_column(
            "reports",
            sa.Column(
                "report_category",
                sa.String(50),
                nullable=False,
                server_default="OTHER",
            ),
        )

    if "report_status" not in cols:
        op.add_column(
            "reports",
            sa.Column(
                "report_status",
                sa.String(50),
                nullable=False,
                server_default="pending",
            ),
        )

    existing_indexes = _index_names("reports")
    if "idx_reports_category_status" not in existing_indexes:
        op.create_index(
            "idx_reports_category_status",
            "reports",
            ["report_category", "report_status", "created_at"],
        )

    if "idx_reports_reporter" not in existing_indexes:
        op.create_index(
            "idx_reports_reporter",
            "reports",
            ["reporter_id", "created_at"],
        )

    if "idx_reports_letter" not in existing_indexes:
        op.create_index(
            "idx_reports_letter",
            "reports",
            ["letter_id"],
        )


def downgrade() -> None:
    if not _table_exists("reports"):
        return

    cols = _column_names("reports")

    # Drop indexes
    op.drop_index("idx_reports_letter", table_name="reports", if_exists=True)
    op.drop_index("idx_reports_reporter", table_name="reports", if_exists=True)
    op.drop_index("idx_reports_category_status",
                  table_name="reports", if_exists=True)

    # Drop columns
    if "report_status" in cols:
        op.drop_column("reports", "report_status")

    if "report_category" in cols:
        op.drop_column("reports", "report_category")
