-- =============================================================================
-- File: schema/postgres_additions.sql
-- Purpose: Additive migrations for DB_SCHEMA v1.2 → v2.0 (Serene data layer)
--          Adds user_profiles, snapshots, outbox, and archive tables.
--          DO NOT MODIFY existing tables — this file only ADDs new objects.
-- Dependencies: DB_SCHEMA v1.2 (users, conversations, conversation_memories)
-- Version: 2.0 | Last updated: 2026-04-14
-- Run order: This file must run AFTER base schema (DB_SCHEMA v1.2) is applied.
-- Rollback: See ROLLBACK section at bottom of file.
-- =============================================================================

-- Assumptions:
--   - app_user role exists (created in base schema setup)
--   - service_role exists and has BYPASSRLS (for internal service operations)
--   - pgvector extension already enabled (for conversation_memories compatibility)
--   - current_setting('app.current_user_id', true) pattern consistent with v1.2

-- =============================================================================
-- TABLE: user_profiles
-- One row per user. Aggregated profile object: traits, summaries, triggers.
-- Hot-path: read every chat turn (via Redis cache → Postgres fallback).
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    -- Identity
    user_id             VARCHAR(50) PRIMARY KEY
                            REFERENCES users(user_id) ON DELETE CASCADE,

    -- Optimistic concurrency control (increment on every write)
    version             INTEGER NOT NULL DEFAULT 1,

    -- Schema evolution marker (allows future migrations of JSONB structure)
    schema_version      VARCHAR(10) NOT NULL DEFAULT 'v1',

    -- Main profile payload (see schema/user_profile_schema.json for full spec)
    profile             JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Denormalized hot fields for fast filtering without JSONB parse
    current_crisis_level    INTEGER NOT NULL DEFAULT 0
                                CHECK (current_crisis_level >= 0 AND current_crisis_level <= 5),
    last_active_session_id  VARCHAR(50) REFERENCES conversations(session_id) ON DELETE SET NULL,
    summary_count           INTEGER NOT NULL DEFAULT 0 CHECK (summary_count >= 0),

    -- Audit
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- GIN indexes for JSONB sub-field queries (partial index on non-empty)
CREATE INDEX IF NOT EXISTS idx_profile_traits
    ON user_profiles USING GIN ((profile -> 'traits'))
    WHERE profile ? 'traits';

CREATE INDEX IF NOT EXISTS idx_profile_trigger_tags
    ON user_profiles USING GIN ((profile -> 'trigger_tags'))
    WHERE profile ? 'trigger_tags';

-- Partial index: fast lookup of elevated crisis users (Supervisor routing)
CREATE INDEX IF NOT EXISTS idx_profile_crisis_elevated
    ON user_profiles (current_crisis_level)
    WHERE current_crisis_level >= 3;

-- Standard timestamp index for admin queries
CREATE INDEX IF NOT EXISTS idx_profile_updated
    ON user_profiles (updated_at DESC);

-- RLS: user can only read/write their own profile
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;

CREATE POLICY rls_profile_isolation ON user_profiles
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    )
    WITH CHECK (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- service_role can read all profiles (for Celery workers, summarizer)
-- Grant is managed at role level, not policy level — service_role has BYPASSRLS.

-- =============================================================================
-- TABLE: user_profile_snapshots
-- Append-only version history of user_profiles. Used for rollback, audit,
-- and evolution analysis (e.g., "how did trigger_tags change over 3 months").
-- Never UPDATE or DELETE rows — new snapshot = new row.
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profile_snapshots (
    snapshot_id     BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL
                        REFERENCES users(user_id) ON DELETE CASCADE,

    -- Version matches user_profiles.version at time of snapshot
    version         INTEGER NOT NULL,

    -- Full copy of profile JSONB at snapshot time
    profile         JSONB NOT NULL,

    -- Why this snapshot was taken
    reason          VARCHAR(50) NOT NULL
                        CHECK (reason IN (
                            'session_end',
                            'weekly_rollup',
                            'crisis_event',
                            'trait_update',
                            'manual',
                            'migration'
                        )),

    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for per-user history queries (admin dashboard, rollback lookup)
CREATE INDEX IF NOT EXISTS idx_snapshot_user_time
    ON user_profile_snapshots (user_id, created_at DESC);

-- Composite index for specific version lookup
CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshot_user_version
    ON user_profile_snapshots (user_id, version);

-- RLS: snapshots are admin-readable + service_role; user cannot access their own
-- (raw clinical snapshot may contain scores)
ALTER TABLE user_profile_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profile_snapshots FORCE ROW LEVEL SECURITY;

CREATE POLICY rls_snapshot_admin_only ON user_profile_snapshots
    FOR ALL
    USING (current_setting('app.current_role', true)::text = 'admin')
    WITH CHECK (current_setting('app.current_role', true)::text = 'admin');

-- Prevent accidental UPDATE/DELETE (append-only contract)
REVOKE UPDATE, DELETE ON user_profile_snapshots FROM PUBLIC;
REVOKE UPDATE, DELETE ON user_profile_snapshots FROM app_user;

-- =============================================================================
-- TABLE: sync_outbox
-- Outbox pattern for Postgres → Neo4j async sync.
-- Producers: app layer (trigger events), session summarizer (session.ended).
-- Consumer: outbox_worker.py (polls every 5s, batch 50, MERGE into Neo4j).
-- All payloads must be PII-masked before INSERT.
-- =============================================================================

CREATE TABLE IF NOT EXISTS sync_outbox (
    outbox_id       BIGSERIAL PRIMARY KEY,

    -- Routing key for the outbox worker
    event_type      VARCHAR(50) NOT NULL
                        CHECK (event_type IN (
                            'memory.created',
                            'trigger.observed',
                            'session.ended',
                            'coping.attempted',
                            'profile.updated'
                        )),

    -- PII-masked event payload (no raw content, no scores)
    payload         JSONB NOT NULL,

    -- For worker routing (Neo4j MERGE needs this)
    user_id         VARCHAR(50) NOT NULL,

    -- Processing state machine: pending → processing → done | failed
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'done', 'failed')),

    -- Retry counter
    attempts        INTEGER NOT NULL DEFAULT 0
                        CHECK (attempts >= 0 AND attempts <= 3),

    -- Timestamps
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMP

    -- Note: no FK to users.user_id intentionally —
    -- outbox must survive even if user is soft-deleted.
);

-- Primary consumer index: pending events, oldest first
CREATE INDEX IF NOT EXISTS idx_outbox_pending_fifo
    ON sync_outbox (created_at ASC)
    WHERE status = 'pending';

-- Dead-letter queue view: failed events for alerting
CREATE INDEX IF NOT EXISTS idx_outbox_failed
    ON sync_outbox (created_at DESC)
    WHERE status = 'failed';

-- Per-user event lookup (for idempotency check)
CREATE INDEX IF NOT EXISTS idx_outbox_user_event
    ON sync_outbox (user_id, event_type, created_at DESC);

-- RLS: outbox is internal service only — app_user has no access
ALTER TABLE sync_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_outbox FORCE ROW LEVEL SECURITY;

CREATE POLICY rls_outbox_service_only ON sync_outbox
    FOR ALL
    USING (current_setting('app.current_role', true)::text IN ('admin', 'service'))
    WITH CHECK (current_setting('app.current_role', true)::text IN ('admin', 'service'));

-- =============================================================================
-- TABLE: session_summaries_archive
-- Overflow storage for session_summaries[] that exceed the 50-entry cap
-- in user_profiles.profile. Written by session_summarizer.py during trim.
-- Read rarely (only for deep history analysis or user data export).
-- =============================================================================

CREATE TABLE IF NOT EXISTS session_summaries_archive (
    archive_id      BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL
                        REFERENCES users(user_id) ON DELETE CASCADE,

    -- Original session reference (may be NULL if conversation hard-deleted)
    session_id      VARCHAR(50)
                        REFERENCES conversations(session_id) ON DELETE SET NULL,

    -- Full summary object (same structure as profile.session_summaries[] element)
    summary         JSONB NOT NULL,

    -- Denormalized for fast filtering without JSONB parse
    session_started_at  TIMESTAMP,
    dominant_emotion    VARCHAR(50),
    sos_triggered       BOOLEAN NOT NULL DEFAULT FALSE,

    -- When this was pushed out of the hot profile
    archived_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Per-user chronological query (for data export, GDPR, deep history)
CREATE INDEX IF NOT EXISTS idx_archive_user_time
    ON session_summaries_archive (user_id, session_started_at DESC);

-- SOS filter for admin review of archived sessions
CREATE INDEX IF NOT EXISTS idx_archive_sos
    ON session_summaries_archive (user_id, archived_at DESC)
    WHERE sos_triggered = TRUE;

-- RLS: user can read their own archived summaries (for data export endpoint)
ALTER TABLE session_summaries_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_summaries_archive FORCE ROW LEVEL SECURITY;

CREATE POLICY rls_archive_isolation ON session_summaries_archive
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- =============================================================================
-- TRIGGER: auto-update updated_at on user_profiles
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_user_profiles_updated_at'
    ) THEN
        CREATE TRIGGER trg_user_profiles_updated_at
            BEFORE UPDATE ON user_profiles
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

-- =============================================================================
-- GRANTS (run as superuser / migration role)
-- =============================================================================

-- app_user: can read/write own profile (RLS enforces row isolation)
GRANT SELECT, INSERT, UPDATE ON user_profiles TO app_user;

-- app_user: can read own archived summaries
GRANT SELECT ON session_summaries_archive TO app_user;

-- service_role (Celery workers): full access to internal tables
GRANT SELECT, INSERT, UPDATE ON sync_outbox TO service_role;
GRANT SELECT, INSERT ON user_profile_snapshots TO service_role;
GRANT SELECT, INSERT, UPDATE ON user_profiles TO service_role;
GRANT SELECT, INSERT ON session_summaries_archive TO service_role;

-- Sequences for BIGSERIAL columns
GRANT USAGE, SELECT ON SEQUENCE sync_outbox_outbox_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE user_profile_snapshots_snapshot_id_seq TO service_role;
GRANT USAGE, SELECT ON SEQUENCE session_summaries_archive_archive_id_seq TO service_role;

-- =============================================================================
-- ROLLBACK PLAN (run in reverse order if migration fails)
-- =============================================================================
-- DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- DROP TABLE IF EXISTS session_summaries_archive CASCADE;
-- DROP TABLE IF EXISTS sync_outbox CASCADE;
-- DROP TABLE IF EXISTS user_profile_snapshots CASCADE;
-- DROP TABLE IF EXISTS user_profiles CASCADE;
