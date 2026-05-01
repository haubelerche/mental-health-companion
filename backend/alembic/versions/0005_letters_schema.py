"""Add letters columns and letter-related tables

Revision ID: 0005_letters_schema
Revises: 0004_checkin_emotions
Create Date: 2026-05-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_letters_schema"
down_revision = "0004_checkin_emotions"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _table_names()

    # Add missing columns to letters
    if "letters" in tables:
        cols = _column_names("letters")
        if "forward_count" not in cols:
            op.add_column(
                "letters",
                sa.Column("forward_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            )
        if "has_reply" not in cols:
            op.add_column(
                "letters",
                sa.Column("has_reply", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if "is_reported" not in cols:
            op.add_column(
                "letters",
                sa.Column("is_reported", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )

    # Create new tables if they don't exist
    if "letter_flows" not in tables:
        op.create_table(
            "letter_flows",
            sa.Column("flow_id", sa.String(50), primary_key=True),
            sa.Column("letter_id", sa.String(50), sa.ForeignKey("letters.letter_id"), nullable=False),
            sa.Column("from_user_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=True),
            sa.Column("to_user_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("idx_letter_flow_letter", "letter_flows", ["letter_id"])

    if "letter_replies" not in tables:
        op.create_table(
            "letter_replies",
            sa.Column("reply_id", sa.String(50), primary_key=True),
            sa.Column("letter_id", sa.String(50), sa.ForeignKey("letters.letter_id"), nullable=False),
            sa.Column("replier_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("letter_id", name="uq_letter_reply_once"),
        )

    if "letter_reactions" not in tables:
        op.create_table(
            "letter_reactions",
            sa.Column("reaction_id", sa.String(50), primary_key=True),
            sa.Column("reply_id", sa.String(50), sa.ForeignKey("letter_replies.reply_id"), nullable=False),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("reaction_type", sa.String(20), nullable=False),
            sa.UniqueConstraint("reply_id", "user_id", name="uq_letter_reaction_once"),
        )

    if "reports" not in tables:
        op.create_table(
            "reports",
            sa.Column("report_id", sa.String(50), primary_key=True),
            sa.Column("reporter_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("letter_id", sa.String(50), sa.ForeignKey("letters.letter_id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )


def downgrade() -> None:
    tables = _table_names()

    # Drop created tables
    if "reports" in tables:
        op.drop_table("reports")
    if "letter_reactions" in tables:
        op.drop_table("letter_reactions")
    if "letter_replies" in tables:
        op.drop_table("letter_replies")
    if "letter_flows" in tables:
        # drop index first
        try:
            op.drop_index("idx_letter_flow_letter", table_name="letter_flows")
        except Exception:
            pass
        op.drop_table("letter_flows")

    # Drop added columns from letters
    if "letters" in tables:
        cols = _column_names("letters")
        if "is_reported" in cols:
            op.drop_column("letters", "is_reported")
        if "has_reply" in cols:
            op.drop_column("letters", "has_reply")
        if "forward_count" in cols:
            op.drop_column("letters", "forward_count")
