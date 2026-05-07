-- ============================================================
-- FAST CORE VERSION: TABLES + CONSTRAINTS + TRIGGERS + RLS, NO INDEXES
--
-- Use this when Supabase SQL Editor times out while running the full file.
-- Step 1: Run this file first.
-- Step 2: Run the optional index file afterwards in smaller batches.
--
-- WARNING:
--   This still drops old app schema and old business tables in extensions.*.
--   Run only after backup / on dev-staging first.
-- ============================================================

-- ============================================================


-- ============================================================
-- 0. EXTENSIONS
-- ============================================================

create schema if not exists extensions;

create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;


-- ============================================================
-- 1. DROP OLD / REBUILD TARGET SCHEMA
-- ============================================================

-- Drop old user/business tables accidentally created inside extensions schema.
-- Do not drop the extensions schema itself because PostgreSQL extensions live there.

drop table if exists extensions.admin_audit_log cascade;
drop table if exists extensions.bookmarks cascade;
drop table if exists extensions.clinical_profiles cascade;
drop table if exists extensions.conversation_memories cascade;
drop table if exists extensions.conversations cascade;
drop table if exists extensions.crisis_logs cascade;
drop table if exists extensions.messages cascade;
drop table if exists extensions.mood_checkins cascade;
drop table if exists extensions.play_events cascade;
drop table if exists extensions.refresh_tokens cascade;
drop table if exists extensions.resources cascade;
drop table if exists extensions.risk_inference_log cascade;
drop table if exists extensions.session_risk_snapshots cascade;
drop table if exists extensions.session_summaries_archive cascade;
drop table if exists extensions.sync_outbox cascade;
drop table if exists extensions.user_profile_snapshots cascade;
drop table if exists extensions.user_profiles cascade;
drop table if exists extensions.users cascade;

-- Rebuild clean application schema.
drop schema if exists app cascade;
create schema app;

set search_path = app, public, extensions;


-- ============================================================
-- 2. SHARED UTILITY
-- ============================================================

create or replace function app.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- ============================================================
-- 3. IDENTITY / AUTH
-- ============================================================

create table app.users (
  user_id text primary key default extensions.gen_random_uuid()::text,

  -- Optional mapping to Supabase Auth.
  -- If you use Supabase Auth, store auth.users.id here.
  -- If you use custom FastAPI auth, this can remain null.
  auth_user_id uuid unique,

  display_name text not null,
  email text not null unique,
  password_hash text,

  disclaimer_accepted boolean not null default false,
  analytics_opt_in boolean not null default false,
  data_retention_days integer not null default 90 check (data_retention_days between 1 and 3650),

  is_active boolean not null default true,

  created_at timestamptz not null default now(),
  last_active timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  policy_acknowledged_at timestamptz,
  policy_version_ack text,
  email_verified_at timestamptz
);

create trigger trg_users_updated_at
before update on app.users
for each row execute function app.set_updated_at();


create table app.refresh_tokens (
  token_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  token_hash text not null,
  ip_address inet,
  user_agent text,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.
create index idx_refresh_tokens_expires_at on app.refresh_tokens(expires_at);

create table app.user_identities (
  identity_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  provider text not null,
  provider_user_id text not null,
  provider_email text,
  provider_name text,
  provider_picture_url text,
  provider_email_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_user_identity_provider_uid unique (provider, provider_user_id),
  constraint uq_user_identity_user_provider unique (user_id, provider)
);

create trigger trg_user_identities_updated_at
before update on app.user_identities
for each row execute function app.set_updated_at();

create table app.email_verification_tokens (
  token_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  used_at timestamptz,
  resend_count integer not null default 0,
  last_sent_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table app.password_reset_tokens (
  token_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);


-- ============================================================
-- 4. CONVERSATION CORE
-- ============================================================

create table app.conversations (
  session_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,

  message_count integer not null default 0 check (message_count >= 0),

  started_at timestamptz not null default now(),
  last_message_at timestamptz not null default now(),

  deleted_at timestamptz,
  hard_deleted_at timestamptz,

  -- Lightweight cached summary only.
  -- Source of truth for session summary should be session_summaries_archive.
  anonymous_summary jsonb,
  summarized_at timestamptz
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.messages (
  message_id text primary key default extensions.gen_random_uuid()::text,
  session_id text not null references app.conversations(session_id) on delete cascade,
  user_id text not null references app.users(user_id) on delete cascade,

  role text not null check (role in ('user', 'assistant')),
  content text not null check (length(content) <= 8000),

  -- Normalized replacement for old tone_cam_xuc.
  assistant_tone text check (
    assistant_tone is null or assistant_tone in (
      'supportive',
      'validating',
      'cheerful',
      'calming',
      'mentor',
      'neutral'
    )
  ),

  sos_triggered boolean not null default false,

  -- Optional turn-level score for routing observability.
  distress_score double precision check (
    distress_score is null or distress_score between 0 and 1
  ),

  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- ============================================================

create table app.mood_checkins (
  checkin_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,

  mood text not null,
  mood_score smallint check (mood_score between 1 and 5),
  emoji text,

  note text check (note is null or length(note) <= 3000),

  emotions jsonb not null default '[]'::jsonb,
  triggers jsonb not null default '[]'::jsonb,

  source text not null default 'self_report'
    check (source in ('self_report', 'imported', 'system')),

  logged_date date not null,
  logged_at timestamptz not null default now(),
  updated_at timestamptz,
  time_bucket text not null default 'other',

  constraint uq_mood_checkin_bucket unique (user_id, logged_date, time_bucket)
);

create trigger trg_mood_checkins_updated_at
before update on app.mood_checkins
for each row execute function app.set_updated_at();

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 6. CONTENT / RESOURCES / ENGAGEMENT
-- ============================================================

create table app.resources (
  resource_id text primary key default extensions.gen_random_uuid()::text,

  category text not null,
  title text not null,
  description text,

  format text not null check (
    format in ('article', 'audio', 'video', 'exercise', 'breathing', 'external')
  ),

  duration_sec integer not null default 0 check (duration_sec >= 0),

  storage_key text,
  thumbnail_key text,
  external_url text,

  tags jsonb not null default '[]'::jsonb,

  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.bookmarks (
  bookmark_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  resource_id text not null references app.resources(resource_id) on delete cascade,
  bookmarked_at timestamptz not null default now(),

  unique (user_id, resource_id)
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.play_events (
  event_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  resource_id text not null references app.resources(resource_id) on delete cascade,

  event text not null check (event in ('started', 'paused', 'completed')),
  duration_sec integer not null default 0 check (duration_sec >= 0),
  percent integer not null default 0 check (percent between 0 and 100),

  tracked_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 7. MEMORY / PROFILE / SESSION SUMMARY
-- ============================================================

create table app.conversation_memories (
  memory_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null references app.users(user_id) on delete cascade,
  session_id text references app.conversations(session_id) on delete set null,

  -- Store sanitized memory extracted from chat/check-in/session summary.
  -- Do not store raw message text here because app.messages already stores transcript.
  content text not null,

  memory_type text check (
    memory_type is null or memory_type in (
      'preference',
      'goal',
      'trait',
      'trigger',
      'coping',
      'relationship',
      'routine',
      'summary',
      'other'
    )
  ),

  source text not null default 'chat_turn'
    check (source in ('chat_turn', 'session_summary', 'checkin', 'manual', 'system')),

  embedding extensions.vector(1536),

  importance_score double precision check (
    importance_score is null or importance_score between 0 and 1
  ),
  confidence double precision check (
    confidence is null or confidence between 0 and 1
  ),

  pii_checked boolean not null default false,
  is_deleted boolean not null default false,

  expires_at timestamptz,
  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- Optional vector index.
-- If your dataset is still small, you can create this later.
-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.session_summaries_archive (
  archive_id bigint generated always as identity primary key,
  user_id text not null references app.users(user_id) on delete cascade,
  session_id text references app.conversations(session_id) on delete set null,

  summary jsonb not null,
  session_started_at timestamptz,
  dominant_emotion text,
  sos_triggered boolean not null default false,

  archived_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.user_profiles (
  user_id text primary key references app.users(user_id) on delete cascade,

  version integer not null default 1 check (version >= 1),
  schema_version text not null default 'v1',

  -- Cache/rollup only. Do not use as the primary source for analyst insights.
  profile jsonb not null default '{}'::jsonb,

  last_active_session_id text references app.conversations(session_id) on delete set null,
  summary_count integer not null default 0 check (summary_count >= 0),

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger trg_user_profiles_updated_at
before update on app.user_profiles
for each row execute function app.set_updated_at();

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.user_profile_snapshots (
  snapshot_id bigint generated always as identity primary key,
  user_id text not null references app.users(user_id) on delete cascade,

  version integer not null check (version >= 1),
  profile jsonb not null,

  reason text not null check (
    reason in (
      'session_end',
      'weekly_rollup',
      'crisis_event',
      'trait_update',
      'manual',
      'migration'
    )
  ),

  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 8. SAFETY / RISK / CLINICAL PROFILE
-- ============================================================

create table app.clinical_profiles (
  profile_id text primary key default extensions.gen_random_uuid()::text,
  user_id text not null unique references app.users(user_id) on delete cascade,

  -- Use only if derived from actual questionnaire or explicitly documented scoring.
  phq9_score integer check (phq9_score is null or phq9_score between 0 and 27),
  gad7_score integer check (gad7_score is null or gad7_score between 0 and 21),

  phq9_coverage jsonb not null default '{}'::jsonb,
  gad7_coverage jsonb not null default '{}'::jsonb,

  crisis_level integer not null default 0 check (crisis_level between 0 and 5),

  score_source text check (
    score_source is null or score_source in (
      'self_report',
      'questionnaire',
      'analyst_inference',
      'clinician_review',
      'system'
    )
  ),

  model_version text,

  last_scored_at timestamptz,
  updated_at timestamptz not null default now()
);

create trigger trg_clinical_profiles_updated_at
before update on app.clinical_profiles
for each row execute function app.set_updated_at();

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.risk_inference_log (
  log_id bigint generated always as identity primary key,
  user_id text not null references app.users(user_id) on delete cascade,
  session_id text references app.conversations(session_id) on delete set null,

  inferred_signal text not null,
  model_version text,

  score double precision check (score is null or score between 0 and 1),
  detail jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.session_risk_snapshots (
  snapshot_id bigint generated always as identity primary key,
  session_id text not null references app.conversations(session_id) on delete cascade,
  user_id text not null references app.users(user_id) on delete cascade,

  risk_score double precision not null check (risk_score between 0 and 1),
  intent_severity double precision not null check (intent_severity between 0 and 1),
  intent_immediacy double precision not null check (intent_immediacy between 0 and 1),

  crisis_mode boolean not null default false,
  escalation_flag boolean not null default false,

  components jsonb not null default '{}'::jsonb,

  source text not null check (
    source in ('supervisor', 'sos_override', 'batch_recalc', 'system', 'safety_agent')
  ),

  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.crisis_logs (
  log_id text primary key default extensions.gen_random_uuid()::text,
  session_id text not null references app.conversations(session_id) on delete cascade,
  user_id text not null references app.users(user_id) on delete cascade,

  severity_level text not null check (
    severity_level in ('low', 'moderate', 'high', 'imminent', 'unknown')
  ),

  context_summary text,

  reviewed boolean not null default false,
  triggered_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text references app.users(user_id) on delete set null
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 9. INTERNAL ANALYST PIPELINE
-- ============================================================

create table app.analyst_signals (
  signal_id text primary key default extensions.gen_random_uuid()::text,

  user_id text not null references app.users(user_id) on delete cascade,
  session_id text references app.conversations(session_id) on delete set null,
  message_id text references app.messages(message_id) on delete set null,

  created_at timestamptz not null default now(),

  -- Internal analyst output.
  emotional_theme text,
  suggested_focus text,
  clinical_note_internal text,

  -- Internal-only. Do not expose directly to frontend.
  risk_indicators jsonb not null default '[]'::jsonb,

  distress_score double precision check (
    distress_score is null or distress_score between 0 and 1
  ),
  confidence double precision check (
    confidence is null or confidence between 0 and 1
  ),

  model_version text,
  graph_context_used boolean not null default false,

  source text not null default 'analyst_node'
    check (source in ('analyst_node', 'batch_rollup', 'manual_review', 'system')),

  -- Raw signals should not be displayed directly.
  display_allowed boolean not null default false
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


create table app.insight_hypotheses (
  insight_id text primary key default extensions.gen_random_uuid()::text,

  user_id text not null references app.users(user_id) on delete cascade,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  hypothesis_type text not null check (
    hypothesis_type in (
      'stress_pattern',
      'sleep_disruption',
      'social_withdrawal',
      'low_mood_trend',
      'anxiety_like_worry_loop',
      'coping_success',
      'engagement_pattern',
      'other'
    )
  ),

  title text not null,

  -- Frontend-safe text. No diagnosis, no raw clinical language.
  user_safe_summary text not null,

  -- Internal evidence/rationale for audit and aggregation.
  internal_rationale jsonb not null default '{}'::jsonb,

  evidence_window_start timestamptz,
  evidence_window_end timestamptz,
  evidence_count integer not null default 0 check (evidence_count >= 0),

  confidence double precision check (
    confidence is null or confidence between 0 and 1
  ),

  severity_band text check (
    severity_band is null or severity_band in ('low', 'moderate', 'elevated')
  ),

  status text not null default 'active'
    check (status in ('active', 'dismissed', 'expired', 'superseded')),

  display_allowed boolean not null default true,

  source text not null default 'analyst_pipeline'
    check (source in ('analyst_pipeline', 'weekly_rollup', 'manual_review', 'system'))
);

create trigger trg_insight_hypotheses_updated_at
before update on app.insight_hypotheses
for each row execute function app.set_updated_at();

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- Frontend-safe view for dashboard.
-- Excludes clinical_note_internal and raw risk indicators.
create or replace view app.dashboard_safe_insights as
select
  insight_id,
  user_id,
  hypothesis_type,
  title,
  user_safe_summary,
  confidence,
  severity_band,
  evidence_count,
  evidence_window_start,
  evidence_window_end,
  created_at,
  updated_at
from app.insight_hypotheses
where status = 'active'
  and display_allowed = true;


-- ============================================================
-- 10. NEO4J / GRAPH SYNC OUTBOX
-- ============================================================

create table app.sync_outbox (
  outbox_id bigint generated always as identity primary key,

  event_type text not null,
  payload jsonb not null,

  status text not null default 'pending'
    check (status in ('pending', 'processing', 'done', 'failed', 'dead_letter')),

  retry_count integer not null default 0 check (retry_count >= 0),
  error_message text,

  created_at timestamptz not null default now(),
  processed_at timestamptz,

  user_id text references app.users(user_id) on delete set null
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 11. ADMIN / AUDIT
-- ============================================================

create table app.admin_audit_log (
  audit_id bigint generated always as identity primary key,

  -- admin_id is a virtual ID (e.g., adm_...) generated on login, not present in app.users
  admin_id text,
  action text not null,
  resource_accessed text,

  ip_address inet,
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.

-- INDEX REMOVED FROM FAST CORE SCRIPT. Run optional index script after core migration.


-- ============================================================
-- 12. SUPABASE RLS SUPPORT
-- ============================================================

-- This helper maps Supabase auth.uid() to app.users.user_id.
-- If you use custom FastAPI auth only, backend service role will bypass RLS.
create or replace function app.current_app_user_id()
returns text
language sql
stable
security definer
set search_path = app, public, extensions
as $$
  select u.user_id
  from app.users u
  where u.auth_user_id = auth.uid()
     or u.user_id = auth.uid()::text
  limit 1
$$;


-- Enable RLS.
alter table app.users enable row level security;
alter table app.refresh_tokens enable row level security;
alter table app.conversations enable row level security;
alter table app.messages enable row level security;
alter table app.mood_checkins enable row level security;
alter table app.resources enable row level security;
alter table app.bookmarks enable row level security;
alter table app.play_events enable row level security;
alter table app.conversation_memories enable row level security;
alter table app.session_summaries_archive enable row level security;
alter table app.user_profiles enable row level security;
alter table app.user_profile_snapshots enable row level security;
alter table app.clinical_profiles enable row level security;
alter table app.risk_inference_log enable row level security;
alter table app.session_risk_snapshots enable row level security;
alter table app.crisis_logs enable row level security;
alter table app.analyst_signals enable row level security;
alter table app.insight_hypotheses enable row level security;
alter table app.sync_outbox enable row level security;
alter table app.admin_audit_log enable row level security;


-- User can read/update their own user profile row.
create policy users_self_select
on app.users for select
using (user_id = app.current_app_user_id());

create policy users_self_update
on app.users for update
using (user_id = app.current_app_user_id())
with check (user_id = app.current_app_user_id());


-- Generic user-owned policies for frontend-safe tables.
-- Internal tables intentionally have no direct client policy.

create policy conversations_owner_all
on app.conversations
for all
using (user_id = app.current_app_user_id())
with check (user_id = app.current_app_user_id());

create policy messages_owner_select
on app.messages
for select
using (user_id = app.current_app_user_id());

create policy messages_owner_insert
on app.messages
for insert
with check (user_id = app.current_app_user_id());

create policy mood_checkins_owner_all
on app.mood_checkins
for all
using (user_id = app.current_app_user_id())
with check (user_id = app.current_app_user_id());

create policy resources_read_active
on app.resources
for select
using (is_active = true);

create policy bookmarks_owner_all
on app.bookmarks
for all
using (user_id = app.current_app_user_id())
with check (user_id = app.current_app_user_id());

create policy play_events_owner_all
on app.play_events
for all
using (user_id = app.current_app_user_id())
with check (user_id = app.current_app_user_id());

create policy conversation_memories_owner_select
on app.conversation_memories
for select
using (user_id = app.current_app_user_id() and is_deleted = false);

create policy user_profiles_owner_select
on app.user_profiles
for select
using (user_id = app.current_app_user_id());

create policy dashboard_insights_owner_select
on app.insight_hypotheses
for select
using (
  user_id = app.current_app_user_id()
  and display_allowed = true
  and status = 'active'
);


-- Allow select from frontend-safe view.
-- RLS on underlying app.insight_hypotheses still applies.
grant usage on schema app to authenticated;
grant select on app.dashboard_safe_insights to authenticated;


-- ============================================================
-- 13. POST-REBUILD CHECKS
-- ============================================================

-- Check table count:
-- select table_schema, count(*) from information_schema.tables
-- where table_schema = 'app'
-- group by table_schema;

-- Check critical tables:
-- select table_name
-- from information_schema.tables
-- where table_schema = 'app'
--   and table_name in (
--     'users',
--     'conversations',
--     'messages',
--     'mood_checkins',
--     'analyst_signals',
--     'insight_hypotheses',
--     'sync_outbox'
--   )
-- order by table_name;

-- select table_name
-- from information_schema.tables
-- where table_schema = 'app'

-- Check vector extension:
-- select extname, extversion from pg_extension where extname = 'vector';

-- ============================================================
-- END
-- ============================================================
