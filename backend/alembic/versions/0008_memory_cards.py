"""Memory cards and audit events.

Plan 06: memory_cards, memory_card_audit_events tables.

Revision ID: 0008_memory_cards
Revises: 0007_heart_economy
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_memory_cards"
down_revision = "0007_heart_economy"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("memory_cards"):
        op.create_table(
            "memory_cards",
            sa.Column("card_id", sa.String(50), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(50),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("source_session_id", sa.String(100), nullable=True),
            sa.Column("memory_type", sa.String(50), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column(
                "status",
                sa.String(30),
                nullable=False,
                server_default="pending_user_review",
            ),
            sa.Column(
                "safety_review_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column(
                "personalization_disabled",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "memory_type IN ('preference','emotional_pattern','coping_history',"
                "'current_stressor','nutrition_pattern','kindness_pattern','persona_preference')",
                name="chk_memory_type",
            ),
            sa.CheckConstraint(
                "status IN ('pending_user_review','active','edited_by_user',"
                "'deleted_by_user','rejected_by_guardrail')",
                name="chk_memory_status",
            ),
            sa.CheckConstraint(
                "safety_review_status IN ('pending','approved','rejected')",
                name="chk_safety_review_status",
            ),
        )
        op.create_index(
            "idx_memory_cards_user_status",
            "memory_cards",
            ["user_id", "status", "created_at"],
        )

    if not _table_exists("memory_card_audit_events"):
        op.create_table(
            "memory_card_audit_events",
            sa.Column("event_id", sa.String(50), primary_key=True),
            sa.Column(
                "memory_card_id",
                sa.String(50),
                sa.ForeignKey("memory_cards.card_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.String(50),
                sa.ForeignKey("users.user_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("old_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    if _table_exists("memory_card_audit_events"):
        op.drop_table("memory_card_audit_events")
    if _table_exists("memory_cards"):
        op.drop_index("idx_memory_cards_user_status", table_name="memory_cards")
        op.drop_table("memory_cards")
