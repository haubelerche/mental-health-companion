"""Heart economy, reward store, persona unlock tables.

Plans 03, 04, 05: heart_wallets, heart_reward_events, heart_spend_events,
streak_states, nutrition_meal_checkins, therapy_letters,
reward_store_items, user_inventory_items, persona_unlock_states.

Revision ID: 0007_heart_economy
Revises: 0006_reports_enhancement
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_heart_economy"
down_revision = "0006_reports_enhancement"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("heart_wallets"):
        op.create_table(
            "heart_wallets",
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
            sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lifetime_earned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lifetime_spent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("daily_earned_today", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("daily_earned_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("balance >= 0", name="chk_wallet_balance_nonneg"),
            sa.CheckConstraint("lifetime_earned >= 0", name="chk_wallet_earned_nonneg"),
            sa.CheckConstraint("lifetime_spent >= 0", name="chk_wallet_spent_nonneg"),
        )

    if not _table_exists("heart_reward_events"):
        op.create_table(
            "heart_reward_events",
            sa.Column("event_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("source_tab", sa.String(50), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="granted"),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("amount > 0", name="chk_reward_amount_pos"),
            sa.UniqueConstraint("idempotency_key", name="uq_reward_idempotency"),
        )
        op.create_index("idx_heart_reward_events_user_created", "heart_reward_events", ["user_id", "created_at"])

    if not _table_exists("streak_states"):
        op.create_table(
            "streak_states",
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
            sa.Column("current_mood_checkin_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("longest_mood_checkin_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_mood_checkin_date", sa.Date(), nullable=True),
            sa.Column("last_7d_bonus_streak_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("nutrition_meal_checkins"):
        op.create_table(
            "nutrition_meal_checkins",
            sa.Column("checkin_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("meal_date", sa.Date(), nullable=False),
            sa.Column("meal_slot", sa.String(20), nullable=False),
            sa.Column("items_text", sa.Text(), nullable=False),
            sa.Column("photo_url", sa.String(500), nullable=True),
            sa.Column("mood_before", sa.String(50), nullable=True),
            sa.Column("mood_after", sa.String(50), nullable=True),
            sa.Column("reward_event_id", sa.String(50), sa.ForeignKey("heart_reward_events.event_id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", "meal_date", "meal_slot", name="uq_nutrition_slot"),
            sa.CheckConstraint("meal_slot IN ('breakfast', 'lunch', 'dinner')", name="chk_meal_slot"),
        )

    if not _table_exists("therapy_letters"):
        op.create_table(
            "therapy_letters",
            sa.Column("letter_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("recipient_type", sa.String(50), nullable=True),
            sa.Column("letter_text", sa.Text(), nullable=False),
            sa.Column("normalized_text", sa.Text(), nullable=True),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
            sa.Column("reward_event_id", sa.String(50), sa.ForeignKey("heart_reward_events.event_id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_therapy_letters_user_created", "therapy_letters", ["user_id", "created_at"])

    if not _table_exists("heart_spend_events"):
        op.create_table(
            "heart_spend_events",
            sa.Column("event_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.String(100), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="spent"),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("amount > 0", name="chk_spend_amount_pos"),
            sa.UniqueConstraint("idempotency_key", name="uq_spend_idempotency"),
        )

    if not _table_exists("reward_store_items"):
        op.create_table(
            "reward_store_items",
            sa.Column("item_id", sa.String(100), primary_key=True),
            sa.Column("item_type", sa.String(50), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("subtitle", sa.String(255), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price_hearts", sa.Integer(), nullable=False),
            sa.Column("tier", sa.Integer(), nullable=False),
            sa.Column("icon_key", sa.String(100), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("requirements", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("price_hearts >= 100 AND price_hearts <= 10000", name="chk_price_range"),
            sa.CheckConstraint("tier >= 1", name="chk_tier_pos"),
        )

    if not _table_exists("user_inventory_items"):
        op.create_table(
            "user_inventory_items",
            sa.Column("inventory_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.String(100), sa.ForeignKey("reward_store_items.item_id"), nullable=False),
            sa.Column("acquired_source", sa.String(50), nullable=False),
            sa.Column("spend_event_id", sa.String(50), sa.ForeignKey("heart_spend_events.event_id"), nullable=True),
            sa.Column("acquired_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.UniqueConstraint("user_id", "item_id", name="uq_inventory_item"),
        )

    if not _table_exists("persona_unlock_states"):
        op.create_table(
            "persona_unlock_states",
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
            sa.Column("persona_id", sa.String(50), primary_key=True),
            sa.Column("unlocked", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("unlocked_at", sa.DateTime(), nullable=True),
            sa.Column("unlock_source", sa.String(50), nullable=True),
            sa.Column("required_hearts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("progress", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("requirements", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("boundary_accepted", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    for table in [
        "persona_unlock_states",
        "user_inventory_items",
        "reward_store_items",
        "heart_spend_events",
        "therapy_letters",
        "nutrition_meal_checkins",
        "streak_states",
        "heart_reward_events",
        "heart_wallets",
    ]:
        if _table_exists(table):
            op.drop_table(table)
