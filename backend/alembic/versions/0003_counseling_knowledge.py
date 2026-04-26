"""Add counseling_knowledge table for RAG corpus.

Revision ID: 0003_counseling_knowledge
Revises: 0002_memory_columns
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_counseling_knowledge"
down_revision = "0002_memory_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "counseling_knowledge" in inspector.get_table_names():
        return

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE TABLE counseling_knowledge (
                id          TEXT PRIMARY KEY,
                question    TEXT NOT NULL,
                response    TEXT NOT NULL,
                source      VARCHAR(50) NOT NULL DEFAULT 'mental_health_v1',
                embedding   vector(1536),
                created_at  TIMESTAMP NOT NULL DEFAULT now()
            )
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_counseling_knowledge_embedding_hnsw "
            "ON counseling_knowledge USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )
    else:
        op.create_table(
            "counseling_knowledge",
            sa.Column("id", sa.String(50), primary_key=True),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("response", sa.Text(), nullable=False),
            sa.Column("source", sa.String(50), nullable=False, server_default="mental_health_v1"),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_counseling_knowledge_embedding_hnsw")
    op.drop_table("counseling_knowledge")
