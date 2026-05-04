"""Knowledge packs, cards, and user progress tables.

Plan 07: knowledge_packs, knowledge_cards, user_knowledge_progress.

Revision ID: 0009_knowledge_unlocks
Revises: 0008_memory_cards
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_knowledge_unlocks"
down_revision = "0008_memory_cards"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("knowledge_packs"):
        op.create_table(
            "knowledge_packs",
            sa.Column("pack_id", sa.String(100), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(80), nullable=False),
            sa.Column("price_hearts", sa.Integer(), nullable=True),
            sa.Column(
                "required_item_id",
                sa.String(100),
                sa.ForeignKey("reward_store_items.item_id"),
                nullable=True,
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="true",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "price_hearts IS NULL OR (price_hearts >= 100 AND price_hearts <= 10000)",
                name="chk_kp_price_range",
            ),
        )

    if not _table_exists("knowledge_cards"):
        op.create_table(
            "knowledge_cards",
            sa.Column("card_id", sa.String(100), primary_key=True),
            sa.Column(
                "pack_id",
                sa.String(100),
                sa.ForeignKey("knowledge_packs.pack_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("content_markdown", sa.Text(), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.Column("estimated_read_seconds", sa.Integer(), nullable=True),
            sa.Column("reflection_prompt", sa.Text(), nullable=True),
        )
        op.create_index(
            "idx_knowledge_cards_pack",
            "knowledge_cards",
            ["pack_id", "order_index"],
        )

    if not _table_exists("user_knowledge_progress"):
        op.create_table(
            "user_knowledge_progress",
            sa.Column("progress_id", sa.String(50), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(50),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "pack_id",
                sa.String(100),
                sa.ForeignKey("knowledge_packs.pack_id"),
                nullable=False,
            ),
            sa.Column(
                "card_id",
                sa.String(100),
                sa.ForeignKey("knowledge_cards.card_id"),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "reward_event_id",
                sa.String(50),
                sa.ForeignKey("heart_reward_events.event_id"),
                nullable=True,
            ),
            sa.UniqueConstraint("user_id", "card_id", name="uq_user_card_progress"),
        )


def downgrade() -> None:
    if _table_exists("user_knowledge_progress"):
        op.drop_table("user_knowledge_progress")
    if _table_exists("knowledge_cards"):
        op.drop_index("idx_knowledge_cards_pack", table_name="knowledge_cards")
        op.drop_table("knowledge_cards")
    if _table_exists("knowledge_packs"):
        op.drop_table("knowledge_packs")
