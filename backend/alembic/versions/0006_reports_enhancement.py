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


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols = _column_names("reports")

    # Add report_category column (VARCHAR for flexibility, can be converted to ENUM later)
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

    # Add report_status column for moderation workflow
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

    # Create index for admin queries: filtering by category, status, and sorting by date
    op.create_index(
        "idx_reports_category_status",
        "reports",
        ["report_category", "report_status", "created_at"],
    )

    # Create index for querying by reporter_id (for user's own reports)
    op.create_index(
        "idx_reports_reporter",
        "reports",
        ["reporter_id", "created_at"],
    )

    # Create index for querying by letter_id (for duplicate prevention)
    op.create_index(
        "idx_reports_letter",
        "reports",
        ["letter_id"],
    )


def downgrade() -> None:
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
