-- ============================================================
-- Version: 2026-05-05
--
-- If Supabase SQL Editor still times out, run indexes one section at a time.
--
-- For production with existing large data, prefer CREATE INDEX CONCURRENTLY
-- from a migration tool or psql session, not inside a transaction.
-- ============================================================

set search_path = app, extensions;

-- ============================================================
-- NORMAL BTREE / GIN INDEXES
-- ============================================================


create index idx_refresh_tokens_user_id on app.refresh_tokens(user_id);


create index idx_conversations_user_id_last_message
on app.conversations(user_id, last_message_at desc);


create index idx_conversations_user_id_started_at
on app.conversations(user_id, started_at desc);


create index idx_messages_session_created
on app.messages(session_id, created_at asc);


create index idx_messages_user_created
on app.messages(user_id, created_at desc);


create index idx_messages_sos
on app.messages(user_id, created_at desc)
where sos_triggered = true;


create index idx_mood_checkins_user_date
on app.mood_checkins(user_id, logged_date desc);


create index idx_mood_checkins_emotions_gin
on app.mood_checkins using gin (emotions);


create index idx_mood_checkins_triggers_gin
on app.mood_checkins using gin (triggers);


create index idx_resources_category_active
on app.resources(category, is_active);


create index idx_resources_tags_gin
on app.resources using gin (tags);


create index idx_bookmarks_user_created
on app.bookmarks(user_id, bookmarked_at desc);


create index idx_play_events_user_tracked
on app.play_events(user_id, tracked_at desc);


create index idx_play_events_resource_tracked
on app.play_events(resource_id, tracked_at desc);


create index idx_session_summaries_user_archived
on app.session_summaries_archive(user_id, archived_at desc);


create index idx_session_summaries_summary_gin
on app.session_summaries_archive using gin (summary);


create index idx_user_profiles_profile_gin
on app.user_profiles using gin (profile);


create index idx_user_profile_snapshots_user_created
on app.user_profile_snapshots(user_id, created_at desc);


create index idx_clinical_profiles_user
on app.clinical_profiles(user_id);


create index idx_risk_inference_user_created
on app.risk_inference_log(user_id, created_at desc);


create index idx_risk_inference_session_created
on app.risk_inference_log(session_id, created_at desc);


create index idx_risk_inference_detail_gin
on app.risk_inference_log using gin (detail);


create index idx_session_risk_user_created
on app.session_risk_snapshots(user_id, created_at desc);


create index idx_session_risk_session_created
on app.session_risk_snapshots(session_id, created_at desc);


create index idx_session_risk_crisis
on app.session_risk_snapshots(user_id, created_at desc)
where crisis_mode = true or escalation_flag = true;


create index idx_crisis_logs_user_triggered
on app.crisis_logs(user_id, triggered_at desc);


create index idx_crisis_logs_reviewed
on app.crisis_logs(reviewed, triggered_at desc);


create index idx_analyst_signals_user_created
on app.analyst_signals(user_id, created_at desc);


create index idx_analyst_signals_session_created
on app.analyst_signals(session_id, created_at desc);


create index idx_analyst_signals_risk_gin
on app.analyst_signals using gin (risk_indicators);


create index idx_insight_hypotheses_user_status_created
on app.insight_hypotheses(user_id, status, created_at desc);


create index idx_insight_hypotheses_user_type
on app.insight_hypotheses(user_id, hypothesis_type);


create index idx_insight_hypotheses_rationale_gin
on app.insight_hypotheses using gin (internal_rationale);


create index idx_sync_outbox_status_created
on app.sync_outbox(status, created_at asc);


create index idx_sync_outbox_user_created
on app.sync_outbox(user_id, created_at desc);


create index idx_sync_outbox_payload_gin
on app.sync_outbox using gin (payload);


create index idx_admin_audit_created
on app.admin_audit_log(created_at desc);


create index idx_admin_audit_admin_created
on app.admin_audit_log(admin_id, created_at desc);


create index idx_admin_audit_metadata_gin
on app.admin_audit_log using gin (metadata);


-- ============================================================
-- END
-- ============================================================
