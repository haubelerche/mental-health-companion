"""Align advisor case library runtime schema.

Revision ID: 0030_advisor_runtime_alignment
Revises: 0029_mem0_user_id_constraints
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op


revision = "0030_advisor_runtime_alignment"
down_revision = "0029_mem0_user_id_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute(
        """
        COMMENT ON TABLE app.counseling_knowledge IS
        'Raw counseling Q&A source dataset. Not a final-answer source. Runtime should use approved advisor_case_library rows.'
        """
    )
    op.execute(
        """
        ALTER TABLE app.advisor_case_library
        ADD COLUMN IF NOT EXISTS source text,
        ADD COLUMN IF NOT EXISTS advisor_domains text[] NOT NULL DEFAULT ARRAY[]::text[],
        ADD COLUMN IF NOT EXISTS safety_constraints jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN IF NOT EXISTS reviewed_by text,
        ADD COLUMN IF NOT EXISTS reviewed_at timestamptz
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_library_domains
        ON app.advisor_case_library USING gin (advisor_domains)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_library_topics
        ON app.advisor_case_library USING gin (topic_tags)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_library_patterns
        ON app.advisor_case_library USING gin (cognitive_pattern_tags)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_domains (
            domain_id text PRIMARY KEY,
            runtime_advisor_id text NOT NULL,
            display_name text NOT NULL,
            description text,
            enabled boolean NOT NULL DEFAULT true,
            max_cases_per_turn int NOT NULL DEFAULT 3,
            latency_budget_ms int NOT NULL DEFAULT 120,
            min_quality_score numeric(4,3),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_advisor_domains_max_cases
                CHECK (max_cases_per_turn >= 0 AND max_cases_per_turn <= 10),
            CONSTRAINT ck_advisor_domains_latency_budget
                CHECK (latency_budget_ms >= 0 AND latency_budget_ms <= 10000),
            CONSTRAINT ck_advisor_domains_min_quality
                CHECK (min_quality_score IS NULL OR (min_quality_score >= 0 AND min_quality_score <= 1))
        )
        """
    )
    op.execute(
        """
        INSERT INTO app.advisor_domains(
          domain_id, runtime_advisor_id, display_name, description,
          enabled, max_cases_per_turn, latency_budget_ms, min_quality_score, metadata
        )
        VALUES
          ('empathy', 'empathy_advisor', 'Empathy Advisor', 'Detect emotional validation needs and tone moves', true, 3, 120, NULL, '{}'::jsonb),
          ('cbt_pattern', 'cbt_pattern_advisor', 'CBT Pattern Advisor', 'Detect thinking traps and support reframing', true, 3, 120, NULL, '{}'::jsonb),
          ('reflection', 'reflection_advisor', 'Reflection Advisor', 'Suggest one useful reflective question', true, 3, 120, NULL, '{}'::jsonb),
          ('strategy', 'strategy_resource_advisor', 'Strategy Resource Advisor', 'Suggest practical next steps', true, 3, 120, NULL, '{}'::jsonb),
          ('safety', 'counseling_advisor', 'Safety Guidance', 'Attach safety constraints to counseling guidance', true, 3, 120, NULL, '{}'::jsonb),
          ('relevance', 'relevance_naturalness_critic', 'Relevance Naturalness Critic', 'Keep response on-topic and natural', true, 3, 120, NULL, '{}'::jsonb),
          ('nutrition', 'nutrition_support_advisor', 'Nutrition Support Advisor', 'Connect nutrition check-ins with wellness support', true, 3, 120, NULL, '{}'::jsonb)
        ON CONFLICT (domain_id) DO UPDATE SET
          runtime_advisor_id = EXCLUDED.runtime_advisor_id,
          display_name = EXCLUDED.display_name,
          description = EXCLUDED.description,
          enabled = EXCLUDED.enabled,
          max_cases_per_turn = EXCLUDED.max_cases_per_turn,
          latency_budget_ms = EXCLUDED.latency_budget_ms,
          min_quality_score = EXCLUDED.min_quality_score,
          metadata = EXCLUDED.metadata,
          updated_at = now()
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_case_domain_map (
            case_id uuid NOT NULL REFERENCES app.advisor_case_library(case_id) ON DELETE CASCADE,
            domain_id text NOT NULL REFERENCES app.advisor_domains(domain_id),
            runtime_advisor_id text NOT NULL,
            relevance_score numeric(4,3) NOT NULL DEFAULT 1.0,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY(case_id, domain_id),
            CONSTRAINT ck_advisor_case_domain_relevance
                CHECK (relevance_score >= 0 AND relevance_score <= 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_domain_map_runtime
        ON app.advisor_case_domain_map (runtime_advisor_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_dataset_imports (
            import_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            file_name text NOT NULL,
            domain_id text NOT NULL,
            runtime_advisor_id text,
            row_count int NOT NULL DEFAULT 0,
            imported_by text,
            status text NOT NULL DEFAULT 'pending',
            error_message text,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_advisor_dataset_import_status
                CHECK (status IN ('pending', 'validated', 'promoted', 'failed'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_dataset_staging (
            staging_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            import_id uuid REFERENCES app.advisor_dataset_imports(import_id) ON DELETE CASCADE,
            domain_id text NOT NULL,
            runtime_advisor_id text,
            raw_payload jsonb NOT NULL,
            normalized_question text,
            normalized_response text,
            validation_status text NOT NULL DEFAULT 'pending',
            error_message text,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_advisor_dataset_staging_status
                CHECK (validation_status IN ('pending', 'valid', 'invalid'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_consultation_events (
            event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id text NOT NULL,
            session_id text,
            user_id text,
            advisor_ids text[] NOT NULL DEFAULT ARRAY[]::text[],
            advisor_domains text[] NOT NULL DEFAULT ARRAY[]::text[],
            query_text_hash text,
            interaction_need text,
            risk_level text,
            route_reason_codes text[] NOT NULL DEFAULT ARRAY[]::text[],
            retrieved_case_ids text[] NOT NULL DEFAULT ARRAY[]::text[],
            advisor_output_redacted jsonb NOT NULL DEFAULT '{}'::jsonb,
            used_by_friend boolean NOT NULL DEFAULT false,
            final_response_message_id text,
            prompt_included_case_count int NOT NULL DEFAULT 0,
            approved_case_count int NOT NULL DEFAULT 0,
            blocked_case_count int NOT NULL DEFAULT 0,
            raw_response_in_prompt boolean NOT NULL DEFAULT false,
            latency_ms int,
            model_version text,
            retriever_version text,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_advisor_consultation_no_raw_response
                CHECK (raw_response_in_prompt IS FALSE)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_consultation_events_session_created
        ON app.advisor_consultation_events (session_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_consultation_events_session_created")
    op.execute("DROP TABLE IF EXISTS app.advisor_consultation_events")
    op.execute("DROP TABLE IF EXISTS app.advisor_dataset_staging")
    op.execute("DROP TABLE IF EXISTS app.advisor_dataset_imports")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_domain_map_runtime")
    op.execute("DROP TABLE IF EXISTS app.advisor_case_domain_map")
    op.execute("DROP TABLE IF EXISTS app.advisor_domains")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_patterns")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_topics")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_domains")
    op.execute(
        """
        ALTER TABLE app.advisor_case_library
        DROP COLUMN IF EXISTS reviewed_at,
        DROP COLUMN IF EXISTS reviewed_by,
        DROP COLUMN IF EXISTS metadata,
        DROP COLUMN IF EXISTS safety_constraints,
        DROP COLUMN IF EXISTS advisor_domains,
        DROP COLUMN IF EXISTS source
        """
    )
