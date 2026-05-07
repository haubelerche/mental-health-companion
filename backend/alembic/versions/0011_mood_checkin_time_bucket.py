"""Add time_bucket to mood_checkins for intraday multi-check-in support.

Revision ID: 0011_mood_checkin_time_bucket
Revises: 0010_oauth_identities
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_mood_checkin_time_bucket"
down_revision = "0010_oauth_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public, extensions")
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("mood_checkins", schema="app")]
    if "time_bucket" not in cols:
        op.add_column(
            "mood_checkins",
            sa.Column("time_bucket", sa.String(length=20), nullable=False, server_default="other"),
            schema="app",
        )

    for constraint_name in ("uq_mood_per_day", "mood_checkins_user_id_logged_date_key"):
        try:
            op.drop_constraint(constraint_name, "mood_checkins", type_="unique", schema="app")
        except Exception:
            pass

    inspector = sa.inspect(bind)
    existing_uc = [u["name"] for u in inspector.get_unique_constraints("mood_checkins", schema="app")]
    if "uq_mood_checkin_bucket" not in existing_uc:
        op.create_unique_constraint(
            "uq_mood_checkin_bucket",
            "mood_checkins",
            ["user_id", "logged_date", "time_bucket"],
            schema="app",
        )


def downgrade() -> None:
    try:
        op.drop_constraint("uq_mood_checkin_bucket", "mood_checkins", type_="unique", schema="app")
    except Exception:
        pass
    try:
        op.drop_column("mood_checkins", "time_bucket", schema="app")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_mood_per_day",
        "mood_checkins",
        ["user_id", "logged_date"],
        schema="app",
    )
