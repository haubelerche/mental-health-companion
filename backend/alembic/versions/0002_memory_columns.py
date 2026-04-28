"""memory columns alignment

Revision ID: 0002_memory_columns
Revises: 0001_init_schema
Create Date: 2026-04-23 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_memory_columns"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_profiles_columns = {col["name"] for col in inspector.get_columns("user_profiles")}
    if "version" not in user_profiles_columns:
        op.add_column(
            "user_profiles",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )

    outbox_columns = {col["name"] for col in inspector.get_columns("sync_outbox")}
    if "user_id" not in outbox_columns:
        op.add_column(
            "sync_outbox",
            sa.Column("user_id", sa.String(length=50), nullable=True),
        )
        op.create_foreign_key(
            "fk_sync_outbox_user_id_users",
            "sync_outbox",
            "users",
            ["user_id"],
            ["user_id"],
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_mem_embedding_hnsw "
            "ON conversation_memories USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_conv_mem_embedding_hnsw")

    inspector = sa.inspect(bind)
    outbox_columns = {col["name"] for col in inspector.get_columns("sync_outbox")}
    if "user_id" in outbox_columns:
        op.drop_constraint("fk_sync_outbox_user_id_users", "sync_outbox", type_="foreignkey")
        op.drop_column("sync_outbox", "user_id")

    user_profiles_columns = {col["name"] for col in inspector.get_columns("user_profiles")}
    if "version" in user_profiles_columns:
        op.drop_column("user_profiles", "version")
