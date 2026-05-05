"""oauth identity links for social login

Revision ID: 0010_oauth_identities
Revises: 0009_knowledge_unlocks
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_oauth_identities"
down_revision = "0009_knowledge_unlocks"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("user_identities"):
        return

    op.create_table(
        "user_identities",
        sa.Column("identity_id", sa.String(length=50), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=50),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column("provider_name", sa.String(length=255), nullable=True),
        sa.Column("provider_picture_url", sa.String(length=500), nullable=True),
        sa.Column("provider_email_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_user_identity_provider_uid"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_identity_user_provider"),
    )


def downgrade() -> None:
    if _table_exists("user_identities"):
        op.drop_table("user_identities")