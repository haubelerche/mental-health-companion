"""Create missing app-scoped feature tables.

Revision ID: 0016_create_app_feature_tables
Revises: 0015_feature_tables_app_schema
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


revision = "0016_create_app_feature_tables"
down_revision = "0015_feature_tables_app_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public, extensions")
    op.execute(
        """
        DO $$
        DECLARE
          feature_table text;
        BEGIN
          FOREACH feature_table IN ARRAY ARRAY[
            'heart_wallets',
            'heart_reward_events',
            'heart_spend_events',
            'streak_states',
            'nutrition_meal_checkins',
            'persona_unlock_states',
            'reward_store_items',
            'user_inventory_items',
            'memory_cards',
            'memory_card_audit_events',
            'knowledge_packs',
            'knowledge_cards',
            'user_knowledge_progress',
            'user_notifications',
            'user_notification_preferences'
          ]
          LOOP
            IF to_regclass(format('app.%I', feature_table)) IS NULL
               AND to_regclass(format('public.%I', feature_table)) IS NOT NULL
            THEN
              EXECUTE format('ALTER TABLE public.%I SET SCHEMA app', feature_table);
            END IF;
          END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.heart_wallets (
          user_id text PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
          balance integer NOT NULL DEFAULT 0,
          lifetime_earned integer NOT NULL DEFAULT 0,
          lifetime_spent integer NOT NULL DEFAULT 0,
          daily_earned_today integer NOT NULL DEFAULT 0,
          daily_earned_date date,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_wallet_balance_nonneg CHECK (balance >= 0),
          CONSTRAINT chk_wallet_earned_nonneg CHECK (lifetime_earned >= 0),
          CONSTRAINT chk_wallet_spent_nonneg CHECK (lifetime_spent >= 0)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.heart_reward_events (
          event_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          event_type text NOT NULL,
          amount integer NOT NULL,
          source_tab text NOT NULL,
          idempotency_key text NOT NULL UNIQUE,
          status text NOT NULL DEFAULT 'granted',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_reward_amount_pos CHECK (amount > 0)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_heart_reward_events_user_created "
        "ON app.heart_reward_events (user_id, created_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.streak_states (
          user_id text PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
          current_mood_checkin_streak integer NOT NULL DEFAULT 0,
          longest_mood_checkin_streak integer NOT NULL DEFAULT 0,
          last_mood_checkin_date date,
          last_7d_bonus_streak_count integer NOT NULL DEFAULT 0,
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.heart_spend_events (
          event_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          item_id text NOT NULL,
          amount integer NOT NULL,
          idempotency_key text NOT NULL UNIQUE,
          status text NOT NULL DEFAULT 'spent',
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_spend_amount_pos CHECK (amount > 0)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.reward_store_items (
          item_id text PRIMARY KEY,
          item_type text NOT NULL,
          title text NOT NULL,
          subtitle text,
          description text,
          price_hearts integer NOT NULL,
          tier integer NOT NULL,
          icon_key text,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          requirements jsonb NOT NULL DEFAULT '{}'::jsonb,
          is_active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_price_range CHECK (price_hearts >= 100 AND price_hearts <= 10000),
          CONSTRAINT chk_tier_pos CHECK (tier >= 1)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_inventory_items (
          inventory_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          item_id text NOT NULL REFERENCES app.reward_store_items(item_id),
          acquired_source text NOT NULL,
          spend_event_id text REFERENCES app.heart_spend_events(event_id),
          acquired_at timestamptz NOT NULL DEFAULT now(),
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          CONSTRAINT uq_inventory_item UNIQUE (user_id, item_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.nutrition_meal_checkins (
          checkin_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          meal_date date NOT NULL,
          meal_slot text NOT NULL,
          items_text text NOT NULL,
          photo_url text,
          mood_before text,
          mood_after text,
          reward_event_id text REFERENCES app.heart_reward_events(event_id),
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_nutrition_slot UNIQUE (user_id, meal_date, meal_slot),
          CONSTRAINT chk_meal_slot CHECK (meal_slot IN ('breakfast', 'lunch', 'dinner'))
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.persona_unlock_states (
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          persona_id text NOT NULL,
          unlocked boolean NOT NULL DEFAULT false,
          unlocked_at timestamptz,
          unlock_source text,
          required_hearts integer NOT NULL DEFAULT 0,
          progress jsonb NOT NULL DEFAULT '{}'::jsonb,
          requirements jsonb NOT NULL DEFAULT '{}'::jsonb,
          boundary_accepted boolean NOT NULL DEFAULT false,
          updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (user_id, persona_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.memory_cards (
          card_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          source_session_id text,
          memory_type text NOT NULL,
          title text NOT NULL,
          content text NOT NULL,
          confidence double precision,
          status text NOT NULL DEFAULT 'pending_user_review',
          safety_review_status text NOT NULL DEFAULT 'pending',
          personalization_disabled boolean NOT NULL DEFAULT false,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_memory_type CHECK (
            memory_type IN (
              'preference', 'emotional_pattern', 'coping_history',
              'current_stressor', 'nutrition_pattern', 'kindness_pattern',
              'persona_preference'
            )
          ),
          CONSTRAINT chk_memory_status CHECK (
            status IN (
              'pending_user_review', 'active', 'edited_by_user',
              'deleted_by_user', 'rejected_by_guardrail'
            )
          ),
          CONSTRAINT chk_safety_review_status CHECK (safety_review_status IN ('pending', 'approved', 'rejected'))
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_cards_user_status "
        "ON app.memory_cards (user_id, status, created_at)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.memory_card_audit_events (
          event_id text PRIMARY KEY,
          memory_card_id text NOT NULL REFERENCES app.memory_cards(card_id) ON DELETE CASCADE,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          action text NOT NULL,
          old_value jsonb,
          new_value jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.knowledge_packs (
          pack_id text PRIMARY KEY,
          title text NOT NULL,
          description text,
          category text NOT NULL,
          price_hearts integer,
          required_item_id text REFERENCES app.reward_store_items(item_id),
          is_active boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chk_kp_price_range CHECK (
            price_hearts IS NULL OR (price_hearts >= 100 AND price_hearts <= 10000)
          )
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.knowledge_cards (
          card_id text PRIMARY KEY,
          pack_id text NOT NULL REFERENCES app.knowledge_packs(pack_id) ON DELETE CASCADE,
          title text NOT NULL,
          content_markdown text NOT NULL,
          order_index integer NOT NULL,
          estimated_read_seconds integer,
          reflection_prompt text
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_cards_pack "
        "ON app.knowledge_cards (pack_id, order_index)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_knowledge_progress (
          progress_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          pack_id text NOT NULL REFERENCES app.knowledge_packs(pack_id),
          card_id text NOT NULL REFERENCES app.knowledge_cards(card_id),
          completed_at timestamptz,
          reward_event_id text REFERENCES app.heart_reward_events(event_id),
          CONSTRAINT uq_user_card_progress UNIQUE (user_id, card_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_notification_preferences (
          user_id text PRIMARY KEY REFERENCES app.users(user_id) ON DELETE CASCADE,
          letter_replied boolean NOT NULL DEFAULT true,
          letter_reported boolean NOT NULL DEFAULT true,
          memory_card_review boolean NOT NULL DEFAULT true,
          reward_earned boolean NOT NULL DEFAULT true,
          persona_unlocked boolean NOT NULL DEFAULT true,
          knowledge_completed boolean NOT NULL DEFAULT true,
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.user_notifications (
          notification_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          notification_type text NOT NULL,
          title text NOT NULL,
          body text NOT NULL,
          data jsonb NOT NULL DEFAULT '{}'::jsonb,
          is_read boolean NOT NULL DEFAULT false,
          read_at timestamptz,
          action_url text,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_notifications_user_created "
        "ON app.user_notifications (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_notifications_unread "
        "ON app.user_notifications (user_id, is_read) WHERE is_read = false"
    )


def downgrade() -> None:
    for table_name in (
        "user_notifications",
        "user_notification_preferences",
        "user_knowledge_progress",
        "knowledge_cards",
        "knowledge_packs",
        "memory_card_audit_events",
        "memory_cards",
        "persona_unlock_states",
        "nutrition_meal_checkins",
        "user_inventory_items",
        "reward_store_items",
        "heart_spend_events",
        "streak_states",
        "heart_reward_events",
        "heart_wallets",
    ):
        op.execute(f"DROP TABLE IF EXISTS app.{table_name}")
