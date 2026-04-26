"""Add emotions and triggers columns to mood_checkins.

Revision ID: 0004_checkin_emotions
Revises: 0003_counseling_knowledge
Create Date: 2026-04-25 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_checkin_emotions"
down_revision = "0003_counseling_knowledge"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols = _column_names("mood_checkins")
    if "emotions" not in cols:
        op.add_column("mood_checkins", sa.Column("emotions", sa.JSON(), nullable=True))
    if "triggers" not in cols:
        op.add_column("mood_checkins", sa.Column("triggers", sa.JSON(), nullable=True))


def downgrade() -> None:
    cols = _column_names("mood_checkins")
    if "triggers" in cols:
        op.drop_column("mood_checkins", "triggers")
    if "emotions" in cols:
        op.drop_column("mood_checkins", "emotions")
