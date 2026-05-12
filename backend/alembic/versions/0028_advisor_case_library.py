"""Create processed advisor case library.

Revision ID: 0028_advisor_case_library
Revises: 0027_drop_memory_cards
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "0028_advisor_case_library"
down_revision = "0027_drop_memory_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app.advisor_case_library (
            case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            raw_case_id text,
            language text NOT NULL DEFAULT 'vi',
            user_context text NOT NULL,
            primary_problem text,
            topic_tags text[] NOT NULL DEFAULT ARRAY[]::text[],
            emotional_state_tags text[] NOT NULL DEFAULT ARRAY[]::text[],
            interaction_need text,
            cognitive_pattern_tags text[] NOT NULL DEFAULT ARRAY[]::text[],
            counseling_goal text,
            recommended_approach text,
            intervention_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
            reflection_questions jsonb NOT NULL DEFAULT '[]'::jsonb,
            do_say jsonb NOT NULL DEFAULT '[]'::jsonb,
            do_not_say jsonb NOT NULL DEFAULT '[]'::jsonb,
            risk_flags text[] NOT NULL DEFAULT ARRAY[]::text[],
            source_response_summary text,
            safety_review_status text NOT NULL DEFAULT 'pending',
            quality_score numeric,
            embedding vector(1536),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_advisor_case_safety_status
                CHECK (safety_review_status IN ('pending', 'approved', 'rejected', 'needs_review')),
            CONSTRAINT ck_advisor_case_quality_score
                CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_library_embedding_hnsw
        ON app.advisor_case_library
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_advisor_case_library_status_need
        ON app.advisor_case_library (safety_review_status, interaction_need)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_advisor_case_library_raw_case
        ON app.advisor_case_library (raw_case_id)
        WHERE raw_case_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_raw_case")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_status_need")
    op.execute("DROP INDEX IF EXISTS app.idx_advisor_case_library_embedding_hnsw")
    op.execute("DROP TABLE IF EXISTS app.advisor_case_library")
