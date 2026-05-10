Dưới đây là bản tóm tắt dưới 200 dòng, giữ đủ ý chính để agent đọc nhanh và không bị context bloat. Nội dung dựa trên file `SERENE_DATABASE_CONTEXT.md`. 

````markdown
# SERENE_DATABASE_CONTEXT_SHORT.md

## 1. Core Principle

Serene dùng PostgreSQL/Supabase làm primary source of truth cho toàn bộ dữ liệu ứng dụng.

Neo4j chỉ là derived/reference graph store, dùng cho knowledge graph hoặc pattern graph đã được sanitize và sync bất đồng bộ qua `sync_outbox`.

Frontend không được đọc trực tiếp các bảng internal như risk, clinical, analyst raw output, crisis logs, sync queue hoặc admin audit.

---

## 2. Database Roles

| Store | Role |
|---|---|
| PostgreSQL/Supabase | Source of truth cho user data, chat, check-in, memory, safety, analyst insight, dashboard, rewards, operational state |
| Neo4j | Derived/reference graph, không lưu raw user data hoặc crisis data |
| `sync_outbox` | Queue đồng bộ từ PostgreSQL sang Neo4j |
| Frontend | Chỉ đọc qua backend API hoặc safe views |

---

## 3. Non-Negotiable Rules

1. Chat transcript lưu ở `messages`.
2. Long-term memory lưu ở `conversation_memories`.
3. Session summary lưu ở `session_summaries_archive`.
4. Internal Analyst raw output lưu ở `analyst_signals`.
5. User-facing dashboard insight lưu ở `insight_hypotheses` và expose qua `dashboard_safe_insights`.
6. Risk, crisis, clinical note, analyst raw output là backend-only.
7. `user_profiles` chỉ là cache/rollup, không phải source of truth.
8. Neo4j không được lưu raw messages, PII, crisis logs, clinical diagnosis, hoặc runtime state.

---

## 4. Schema Domains

| Domain | Tables / Views | Purpose |
|---|---|---|
| Identity | `users`, `refresh_tokens` | Account, consent, auth tokens |
| Conversation | `conversations`, `messages` | Chat session và transcript |
| Mood / Reflect | `mood_checkins` | Mood trend, self-report, dashboard evidence |
| Content | `resources`, `bookmarks`, `play_events` | Wellness content và engagement |
| Memory | `conversation_memories`, `session_summaries_archive`, `user_profiles`, `user_profile_snapshots` | Memory, summaries, rollup, versioning |
| Safety | `clinical_profiles`, `risk_inference_log`, `session_risk_snapshots`, `crisis_logs` | Internal risk/safety audit |
| Analyst Insight | `analyst_signals`, `insight_hypotheses`, `dashboard_safe_insights` | Analyst output và user-safe insights |
| Graph Sync | `sync_outbox` | Async Neo4j sync queue |
| Admin | `admin_audit_log` | Backend/admin audit |

---

## 5. Core Tables

### `users`
Stores user account, consent, policy acknowledgement, and retention configuration.

Key fields:
- `user_id`
- `auth_user_id`
- `display_name`
- `email`
- `disclaimer_accepted`
- `analytics_opt_in`
- `data_retention_days`
- `policy_acknowledged_at`
- `policy_version_ack`

### `conversations`
Stores session-level chat metadata.

Key fields:
- `session_id`
- `user_id`
- `message_count`
- `started_at`
- `last_message_at`
- `anonymous_summary`
- `summarized_at`

`anonymous_summary` is lightweight cache only. Full summaries belong in `session_summaries_archive`.

### `messages`
Stores user and assistant chat transcript.

Key fields:
- `message_id`
- `session_id`
- `user_id`
- `role`
- `content`
- `assistant_tone`
- `sos_triggered`
- `distress_score`
- `created_at`

This is the source of truth for chat content.

### `mood_checkins`
Stores daily mood self-report.

Key fields:
- `checkin_id`
- `user_id`
- `mood`
- `mood_score`
- `emoji`
- `note`
- `emotions`
- `triggers`
- `logged_date`
- `logged_at`

Used for mood trend, Reflect dashboard, and insight evidence.

### `conversation_memories`
Stores cleaned long-term memory extracted from chat/check-ins/session summaries.

Key fields:
- `memory_id`
- `user_id`
- `session_id`
- `content`
- `memory_type`
- `source`
- `embedding`
- `importance_score`
- `confidence`
- `pii_checked`
- `is_deleted`
- `expires_at`
- `created_at`

Do not store raw transcript here. Raw transcript belongs in `messages`.

### `session_summaries_archive`
Stores durable session summaries.

Key fields:
- `archive_id`
- `user_id`
- `session_id`
- `summary`
- `session_started_at`
- `dominant_emotion`
- `sos_triggered`
- `archived_at`

Used for memory rollup, dashboard trends, Analyst context, and Neo4j sync.

### `user_profiles`
Stores profile cache/rollup only.

Key fields:
- `user_id`
- `version`
- `schema_version`
- `profile`
- `last_active_session_id`
- `summary_count`
- `created_at`
- `updated_at`

Do not use this as source of truth for dashboard insights.

### `user_profile_snapshots`
Stores profile version history.

Key fields:
- `snapshot_id`
- `user_id`
- `version`
- `profile`
- `reason`
- `created_at`

Used for audit, rollback, and profile evolution debugging.

---

## 6. Safety Tables

### `clinical_profiles`
Internal screening/risk profile.

Key fields:
- `profile_id`
- `user_id`
- `phq9_score`
- `gad7_score`
- `phq9_coverage`
- `gad7_coverage`
- `crisis_level`
- `score_source`
- `model_version`
- `last_scored_at`

Backend-only. Not a medical diagnosis. Do not expose directly to frontend.

### `risk_inference_log`
Logs each detected risk signal.

Key fields:
- `log_id`
- `user_id`
- `session_id`
- `inferred_signal`
- `model_version`
- `score`
- `detail`
- `created_at`

Used for observability and safety audit.

### `session_risk_snapshots`
Stores risk snapshot by turn/session.

Key fields:
- `snapshot_id`
- `session_id`
- `user_id`
- `risk_score`
- `intent_severity`
- `intent_immediacy`
- `crisis_mode`
- `escalation_flag`
- `components`
- `source`
- `created_at`

Used for Safety Agent routing and crisis audit.

### `crisis_logs`
Stores crisis/SOS events.

Key fields:
- `log_id`
- `session_id`
- `user_id`
- `severity_level`
- `context_summary`
- `reviewed`
- `triggered_at`
- `reviewed_at`
- `reviewed_by`

Backend-only. Never expose directly to UI.

---

## 7. Analyst Insight Pipeline

### `analyst_signals`
Stores raw structured output from Internal Analyst Agent.

Key fields:
- `signal_id`
- `user_id`
- `session_id`
- `message_id`
- `emotional_theme`
- `suggested_focus`
- `clinical_note_internal`
- `risk_indicators`
- `distress_score`
- `confidence`
- `model_version`
- `graph_context_used`
- `source`
- `display_allowed`
- `created_at`

Internal-only. Do not render `clinical_note_internal` or `risk_indicators`.

### `insight_hypotheses`
Stores aggregated, user-safe dashboard insights.

Key fields:
- `insight_id`
- `user_id`
- `hypothesis_type`
- `title`
- `user_safe_summary`
- `internal_rationale`
- `evidence_window_start`
- `evidence_window_end`
- `evidence_count`
- `confidence`
- `severity_band`
- `status`
- `display_allowed`
- `source`
- `created_at`
- `updated_at`

This is the main source for user-facing insights.

### `dashboard_safe_insights`
Safe frontend view.

Exposes:
- `insight_id`
- `user_id`
- `hypothesis_type`
- `title`
- `user_safe_summary`
- `confidence`
- `severity_band`
- `evidence_count`
- `evidence_window_start`
- `evidence_window_end`
- `created_at`
- `updated_at`

Must not expose raw clinical notes, risk indicators, or internal rationale.

---

## 8. Content Tables

### `resources`
Stores wellness content.

Key fields:
- `resource_id`
- `category`
- `title`
- `description`
- `format`
- `duration_sec`
- `storage_key`
- `thumbnail_key`
- `external_url`
- `tags`
- `is_active`
- `created_at`

### `bookmarks`
Stores saved resources.

Key fields:
- `bookmark_id`
- `user_id`
- `resource_id`
- `bookmarked_at`

### `play_events`
Stores content engagement.

Key fields:
- `event_id`
- `user_id`
- `resource_id`
- `event`
- `duration_sec`
- `percent`
- `tracked_at`

Used for analytics, personalization, and recommendation.

---

## 9. Graph Sync

### `sync_outbox`
Stores events to sync into Neo4j.

Key fields:
- `outbox_id`
- `event_type`
- `payload`
- `status`
- `retry_count`
- `error_message`
- `created_at`
- `processed_at`
- `user_id`

Allowed statuses:
- `pending`
- `processing`
- `done`
- `failed`
- `dead_letter`

Chat response must not depend on Neo4j write success. Backend writes outbox event; worker handles Neo4j sync asynchronously.

---

## 10. Data Flows

### Chat Flow
```text
User message
→ conversations
→ messages
→ Safety Agent
→ Conversation Agent response
→ messages
````

### Memory Flow

```text
messages
→ memory extraction
→ conversation_memories
→ user_profiles cache
→ user_profile_snapshots when needed
```

### Session Summary Flow

```text
conversation end
→ session_summaries_archive
→ user_profiles rollup
→ sync_outbox
→ Neo4j
```

### Analyst Insight Flow

```text
chat turn
→ Internal Analyst Agent
→ analyst_signals
→ insight aggregation
→ insight_hypotheses
→ dashboard_safe_insights
→ Dashboard UI
```

### Safety Flow

```text
incoming message
→ Safety Agent
→ session_risk_snapshots
→ risk_inference_log
→ crisis_logs when needed
```

### Neo4j Flow

```text
PostgreSQL event
→ sync_outbox
→ outbox worker
→ Neo4j derived graph
→ optional graph context for Analyst/Insight service
```

---

## 11. Source of Truth Matrix

| Data                  | Source of Truth                                 |
| --------------------- | ----------------------------------------------- |
| User account          | `users`                                         |
| Chat session          | `conversations`                                 |
| Chat transcript       | `messages`                                      |
| Mood self-report      | `mood_checkins`                                 |
| Long-term memory      | `conversation_memories`                         |
| Session summary       | `session_summaries_archive`                     |
| Profile cache         | `user_profiles`                                 |
| Profile history       | `user_profile_snapshots`                        |
| Clinical/risk profile | `clinical_profiles`                             |
| Risk events           | `risk_inference_log`                            |
| Risk snapshots        | `session_risk_snapshots`                        |
| Crisis events         | `crisis_logs`                                   |
| Raw Analyst output    | `analyst_signals`                               |
| User-facing insights  | `insight_hypotheses`, `dashboard_safe_insights` |
| Neo4j sync queue      | `sync_outbox`                                   |
| Content library       | `resources`                                     |
| Content engagement    | `play_events`                                   |
| Saved content         | `bookmarks`                                     |

---

## 12. Frontend Access Boundary

Frontend may consume:

* `conversations`
* `messages`
* `mood_checkins`
* `resources`
* `bookmarks`
* `play_events`
* `dashboard_safe_insights`

Frontend must not directly consume:

* `analyst_signals`
* `clinical_profiles`
* `risk_inference_log`
* `session_risk_snapshots`
* `crisis_logs`
* `sync_outbox`
* `admin_audit_log`
* `user_profile_snapshots`

---

## 13. Implementation Rules for Coding Agents

1. Use schema `app`.
2. Do not use `extensions.*` for business tables.
3. Persist chat transcript to `messages`.
4. Persist extracted memory to `conversation_memories`.
5. Persist Internal Analyst output to `analyst_signals`.
6. Persist dashboard-ready insight to `insight_hypotheses`.
7. Expose dashboard insight through `dashboard_safe_insights` or equivalent backend API.
8. Keep clinical/risk/analyst raw fields backend-only.
9. Use `sync_outbox` for Neo4j synchronization.
10. Preserve agent contract:

* Conversation Agent speaks to user.
* Internal Analyst Agent produces internal structured signals.
* Safety Agent owns crisis/risk routing.

```
```
