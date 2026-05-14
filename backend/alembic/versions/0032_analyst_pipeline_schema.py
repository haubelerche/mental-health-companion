"""Analyst pipeline runs, features, and evidence.

Revision ID: 0032_analyst_pipeline_schema
Revises: 0031_restore_memory_cards
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op


revision = "0032_analyst_pipeline_schema"
down_revision = "0031_restore_memory_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.analyst_runs (
          run_id text PRIMARY KEY,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          run_type text NOT NULL,
          status text NOT NULL,
          window_start timestamptz NOT NULL,
          window_end timestamptz NOT NULL,
          data_cutoff_at timestamptz NOT NULL,
          idempotency_key text NOT NULL UNIQUE,
          input_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          source_counts jsonb NOT NULL DEFAULT '{}'::jsonb,
          missing_sources jsonb NOT NULL DEFAULT '[]'::jsonb,
          model_version text,
          feature_version text NOT NULL,
          error_code text,
          created_at timestamptz NOT NULL DEFAULT now(),
          completed_at timestamptz,
          CONSTRAINT ck_analyst_runs_type CHECK (
            run_type IN ('turn','daily','rolling_3d','weekly','on_demand_dashboard','post_screening')
          ),
          CONSTRAINT ck_analyst_runs_status CHECK (
            status IN ('queued','running','completed','failed','skipped_insufficient_data','blocked_by_safety')
          )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analyst_runs_user_created
        ON app.analyst_runs (user_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.analyst_feature_snapshots (
          snapshot_id text PRIMARY KEY,
          run_id text REFERENCES app.analyst_runs(run_id) ON DELETE SET NULL,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          window_start timestamptz NOT NULL,
          window_end timestamptz NOT NULL,
          data_cutoff_at timestamptz NOT NULL,
          window_type text NOT NULL,
          feature_version text NOT NULL,
          features jsonb NOT NULL,
          source_counts jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analyst_feature_snapshots_user_window
        ON app.analyst_feature_snapshots (user_id, window_type, window_end DESC)
        """
    )
    op.execute(
        """
        ALTER TABLE app.analyst_signals
        ADD COLUMN IF NOT EXISTS run_id text REFERENCES app.analyst_runs(run_id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS raw_structured_output jsonb NOT NULL DEFAULT '{}'::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD COLUMN IF NOT EXISTS run_id text REFERENCES app.analyst_runs(run_id) ON DELETE SET NULL
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_type")
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_type CHECK (
          hypothesis_type IN (
            'stress_pattern','sleep_disruption','social_withdrawal','low_mood_trend',
            'anxiety_like_worry_loop','coping_success','engagement_pattern','other',
            'mood_trend','trigger_pattern','nutrition_mood_link','sleep_energy_link',
            'coping_preference','support_style_preference','reflection_pattern',
            'data_quality_notice','screening_context_notice'
          )
        )
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_severity")
    op.execute(
        """
        UPDATE app.insight_hypotheses
        SET severity_band = CASE
          WHEN severity_band = 'moderate' THEN 'medium'
          WHEN severity_band = 'elevated' THEN 'high'
          WHEN severity_band IS NULL THEN 'informational'
          ELSE severity_band
        END
        """
    )
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_severity CHECK (
          severity_band IS NULL OR severity_band IN ('informational','low','medium','high')
        )
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_status")
    op.execute(
        """
        UPDATE app.insight_hypotheses
        SET status = 'dismissed_by_user'
        WHERE status = 'dismissed'
        """
    )
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_status CHECK (
          status IN ('candidate','active','superseded','dismissed_by_user','expired','blocked_by_safety')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.insight_evidence (
          evidence_id text PRIMARY KEY,
          insight_id text NOT NULL REFERENCES app.insight_hypotheses(insight_id) ON DELETE CASCADE,
          user_id text NOT NULL REFERENCES app.users(user_id) ON DELETE CASCADE,
          source_table text NOT NULL,
          source_id text NOT NULL,
          evidence_type text NOT NULL,
          occurred_at timestamptz NOT NULL,
          user_safe_excerpt text,
          numeric_value jsonb,
          weight numeric(4,3),
          sensitivity text NOT NULL DEFAULT 'medium',
          display_allowed boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT ck_insight_evidence_sensitivity CHECK (
            sensitivity IN ('low','medium','high','restricted')
          )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_insight_evidence_insight_display
        ON app.insight_evidence (insight_id, display_allowed, occurred_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_insight_evidence_insight_display")
    op.execute("DROP TABLE IF EXISTS app.insight_evidence")
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_status")
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_status CHECK (
          status IN ('active','dismissed','expired','superseded')
        )
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_severity")
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_severity CHECK (
          severity_band IS NULL OR severity_band IN ('low','moderate','elevated')
        )
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP CONSTRAINT IF EXISTS ck_insight_hyp_type")
    op.execute(
        """
        ALTER TABLE app.insight_hypotheses
        ADD CONSTRAINT ck_insight_hyp_type CHECK (
          hypothesis_type IN ('stress_pattern','sleep_disruption','social_withdrawal',
          'low_mood_trend','anxiety_like_worry_loop','coping_success','engagement_pattern','other')
        )
        """
    )
    op.execute("ALTER TABLE app.insight_hypotheses DROP COLUMN IF EXISTS run_id")
    op.execute("ALTER TABLE app.analyst_signals DROP COLUMN IF EXISTS raw_structured_output")
    op.execute("ALTER TABLE app.analyst_signals DROP COLUMN IF EXISTS run_id")
    op.execute("DROP INDEX IF EXISTS app.idx_analyst_feature_snapshots_user_window")
    op.execute("DROP TABLE IF EXISTS app.analyst_feature_snapshots")
    op.execute("DROP INDEX IF EXISTS app.idx_analyst_runs_user_created")
    op.execute("DROP TABLE IF EXISTS app.analyst_runs")
