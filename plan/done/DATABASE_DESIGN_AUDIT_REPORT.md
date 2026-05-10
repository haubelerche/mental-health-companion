# DATABASE DESIGN AUDIT REPORT - SERENE MENTAL HEALTH AI SYSTEM

## 1. Executive Summary

| Item | Assessment |
|---|---|
| Overall verdict | PARTIAL |
| Risk level | Critical |
| Main architectural risk | PostgreSQL is documented as source of truth, but the active outbox worker does not apply Neo4j graph events, while Mem0 can configure a direct Neo4j graph store outside the outbox boundary. |
| Main privacy/safety risk | Raw or insufficiently governed user-derived memory can bypass `sync_outbox` through Mem0, and dashboard endpoints expose clinical/risk fields to authenticated users. |
| Main schema drift risk | `core_sql.sql`, Alembic revisions, SQLAlchemy models, legacy core workers, docs, and frontend contracts disagree on tables, columns, queue semantics, and feature ownership. |
| Major refactor required | Yes. The database boundary, outbox contract, dashboard evidence pipeline, and schema source of truth require coordinated cleanup. |
| Keep Neo4j for MVP | Keep only as static/internal taxonomy plus optional sanitized derived aggregate graph. Remove or quarantine runtime/user-sensitive graph paths until outbox governance is repaired. |

The system has a sound target principle: Supabase/PostgreSQL owns durable user data, product state, safety audit, memory, rewards, dashboard insight materialization, and operational queues; Neo4j should remain reference/derived; Redis should remain ephemeral. The implementation partially follows that model, but several code paths invalidate the boundary. The most urgent issue is not that Neo4j exists; it is that there are multiple graph-write concepts with different contracts, and the active application worker marks outbox events done without applying the intended Neo4j sync.

### Post-Refactor Validation Update (2026-05-08)

The original audit captured real critical issues at audit time. The current codebase now resolves the highest-risk findings:

- Mem0 no longer enables Neo4j graph-store writes for user-derived memory (`backend/app/services/mem0_service.py`).
- Session close no longer enqueues user-derived graph events (`session.ended`, `trigger.observed`, `coping.attempted`) to Neo4j for MVP (`backend/app/services/session_summary.py`).
- Dashboard overview no longer exposes `phq9_score`, `gad7_score`, or `crisis_level` (`backend/app/api/v1/routers/dashboard.py`).
- Outbox contracts are aligned on `retry_count/error_message/processing_started_at` and no longer use legacy `attempts` (`backend/app/services/db/models.py`, `backend/app/core/outbox_worker.py`, `scripts/outbox_worker.py`, migration `0019_sync_outbox_worker_columns`).
- Startup-time DDL repair was removed; schema ownership is migration-driven (`backend/app/main.py`, migration `0018_outbox_identity`).

Validation results after migration alignment:

- `alembic upgrade head` completed to revisions `0017_admin_audit_align`, `0018_outbox_identity`, `0019_sync_outbox_worker_columns`.
- `python -m pytest backend/tests/test_database_boundary_regression.py backend/tests/test_dashboard_reflect.py backend/tests/test_db_integration.py -q` passed (`41 passed`).
- `python -m pytest backend/tests -q` passed with high confidence (`321 passed, 18 skipped, 1 warning`).
  - Skips are environment-gated/infra-protective (including pool-soak capacity guard and optional live-dependency suites).
- `python -m pytest backend/tests/test_graph_outbox_contract.py -q` passed (`3 passed`) to enforce `sync_outbox` payload boundary checks.

Release handoff updates (2026-05-08):

- Four previously open audit findings are now closed:
  - Raw screening answers are moved out of `clinical_profiles` coverage JSON into dedicated backend-only storage.
  - Risk safety writers now persist safety/risk trail records.
  - Analyst pipeline writers now persist `analyst_signals` and `insight_hypotheses`.
  - Dead heuristic dashboard insight-card code has been removed from the safe insight path.
- Breaking change:
  - `build_safe_insight_cards` removed the `profile_data` parameter; all known callers were updated in the same PR.
- Required production step:
  - Run migration `0021_screening_answers_table` before deployment.
- Remaining open findings from this audit report:
  - None.

Residual risk still worth tracking:

- `docs/PRD.md` and implementation were drifted during audit; updated table naming has now been aligned for reward and voice queue terminology, but broader docs/spec parity should continue to be enforced via CI checks.

Scope note:

- Sections 2-8 in this file are the original audit snapshot and intentionally preserve pre-refactor findings for traceability.
- Current implementation readiness should be interpreted from this post-refactor validation update plus `DATABASE_REFACTOR_PHASE_PLAN.md`.

## 2. Current Database Architecture Map

### Supabase/PostgreSQL

#### Tables

| Category | Tables or views | Evidence |
|---|---|---|
| Identity/auth source of truth | `users`, `refresh_tokens`, `user_identities`, `email_verification_tokens`, `password_reset_tokens` | `backend/app/data/core_sql.sql:78`, `backend/app/data/core_sql.sql:110`, `backend/app/data/core_sql.sql:124`; models in `backend/app/services/db/models.py:50`, `backend/app/services/db/models.py:69`, `backend/app/services/db/models.py:88` |
| Conversation source of truth | `conversations`, `messages` | `backend/app/data/core_sql.sql:168`, `backend/app/data/core_sql.sql:191`; models in `backend/app/services/db/models.py:124`, `backend/app/services/db/models.py:138` |
| Check-in/self-report source of truth | `mood_checkins`, `nutrition_meal_checkins` | `backend/app/data/core_sql.sql:231`; `backend/alembic/versions/0016_create_app_feature_tables.py:156`; models in `backend/app/services/db/models.py:161`, `backend/app/services/db/models.py:685` |
| Memory source of truth | `conversation_memories`, `memory_cards`, `memory_card_audit_events` | `backend/app/data/core_sql.sql:331`; `backend/alembic/versions/0016_create_app_feature_tables.py:192`; models in `backend/app/services/db/models.py:305`, `backend/app/services/db/models.py:824`, `backend/app/services/db/models.py:935` |
| Cache/rollup/audit history | `user_profiles`, `user_profile_snapshots`, `session_summaries_archive` | `backend/app/data/core_sql.sql:382`, `backend/app/data/core_sql.sql:400`, `backend/app/data/core_sql.sql:423`; models in `backend/app/services/db/models.py:347`, `backend/app/services/db/models.py:574`, `backend/app/services/db/models.py:594` |
| Safety/backend-only | `clinical_profiles`, `risk_inference_log`, `session_risk_snapshots`, `crisis_logs`, `admin_audit_log` | `backend/app/data/core_sql.sql:451`, `backend/app/data/core_sql.sql:487`, `backend/app/data/core_sql.sql:508`, `backend/app/data/core_sql.sql:536`, `backend/app/data/core_sql.sql:718`; models in `backend/app/services/db/models.py:190`, `backend/app/services/db/models.py:370`, `backend/app/services/db/models.py:395`, `backend/app/services/db/models.py:219`, `backend/app/services/db/models.py:562` |
| Analyst/dashboard derived | `analyst_signals`, `insight_hypotheses`, `dashboard_safe_insights` | `backend/app/data/core_sql.sql:562`, `backend/app/data/core_sql.sql:603`, `backend/app/data/core_sql.sql:666`; models in `backend/app/services/db/models.py:440`, `backend/app/services/db/models.py:490` |
| Rewards/product state | `heart_wallets`, `heart_reward_events`, `heart_spend_events`, `reward_store_items`, `user_inventory_items`, `persona_unlock_states` | `backend/alembic/versions/0016_create_app_feature_tables.py:57`, `backend/alembic/versions/0016_create_app_feature_tables.py:74`, `backend/alembic/versions/0016_create_app_feature_tables.py:106`, `backend/alembic/versions/0016_create_app_feature_tables.py:121`, `backend/alembic/versions/0016_create_app_feature_tables.py:142`, `backend/alembic/versions/0016_create_app_feature_tables.py:175`; models in `backend/app/services/db/models.py:638`, `backend/app/services/db/models.py:656`, `backend/app/services/db/models.py:749`, `backend/app/services/db/models.py:766`, `backend/app/services/db/models.py:788`, `backend/app/services/db/models.py:805` |
| Knowledge/product content | `resources`, `bookmarks`, `play_events`, `counseling_knowledge`, `knowledge_packs`, `knowledge_cards`, `user_knowledge_progress` | `backend/app/data/core_sql.sql:270`, `backend/app/data/core_sql.sql:298`, `backend/app/data/core_sql.sql:310`; `backend/alembic/versions/0003_counseling_knowledge.py:28`; `backend/alembic/versions/0016_create_app_feature_tables.py:242`, `backend/alembic/versions/0016_create_app_feature_tables.py:259`, `backend/alembic/versions/0016_create_app_feature_tables.py:276`; models in `backend/app/services/db/models.py:262`, `backend/app/services/db/models.py:278`, `backend/app/services/db/models.py:288`, `backend/app/services/db/models.py:603`, `backend/app/services/db/models.py:876`, `backend/app/services/db/models.py:899`, `backend/app/services/db/models.py:913` |
| Operational queues | `sync_outbox`, voice/TTS jobs encoded as `sync_outbox` event `voice.tts_request` | `backend/app/data/core_sql.sql:689`; model in `backend/app/services/db/models.py:617`; voice usage in `backend/app/services/proactive_voice.py:37`, `backend/app/services/proactive_voice.py:203` |

#### Responsibilities

PostgreSQL currently stores identity, conversation transcripts, check-ins, long-term memory, memory-card review state, clinical/safety logs, dashboard insights, rewards/hearts, persona unlocks, knowledge progression, notifications, and voice job payloads. This mostly matches the stated architecture, except that some backend-only/internal information is exposed through user APIs or user-readable JSONB rollups.

#### Read paths

| Flow | Current read path | Evidence |
|---|---|---|
| Chat context | `UserProfile`, recent `Conversation` and `Message`, mood/check-in context, optional memory services | `backend/app/api/v1/routers/chat.py:126`, `backend/app/services/chat_context.py:66`, `backend/app/services/chat_context.py:86` |
| Dashboard overview | Reads `Conversation`, `MoodCheckin`, `ClinicalProfile`, `UserProfile` | `backend/app/api/v1/routers/dashboard.py:114`, `backend/app/api/v1/routers/dashboard.py:118`, `backend/app/api/v1/routers/dashboard.py:130`, `backend/app/api/v1/routers/dashboard.py:131` |
| Safe dashboard insights | Reads `InsightHypothesis`, then falls back to profile-derived heuristic cards | `backend/app/dashboard/service.py:158`, `backend/app/dashboard/service.py:246`, `backend/app/dashboard/service.py:277`, `backend/app/dashboard/service.py:305` |
| Memory cards | Reads `MemoryCard` by user and status | `backend/app/memory/service.py:46`, `backend/app/memory/service.py:119` |
| Rewards/persona | Reads and writes wallet, reward events, inventory, persona unlock state through backend services | `backend/app/rewards/purchase_service.py:13`, `backend/app/services/persona_unlock_persistence.py:28` |
| Voice/TTS | Reads and mutates `SyncOutbox` rows as durable voice job records | `backend/app/services/proactive_voice.py:278`, `backend/app/services/proactive_voice.py:450`, `backend/app/services/proactive_voice.py:572`, `backend/app/services/proactive_voice.py:595` |

#### Write paths

| Flow | Current write path | Evidence |
|---|---|---|
| User chat message | `Message(content=mask_pii(raw_text))` | `backend/app/api/v1/routers/chat.py:504`, `backend/app/api/v1/routers/chat.py:506`, `backend/app/api/v1/routers/chat.py:511` |
| Assistant message | `Message(content=mask_pii(assistant_content))` | `backend/app/api/v1/routers/chat.py:659`, `backend/app/api/v1/routers/chat.py:664` |
| Crisis event | `CrisisLog` plus `AdminAuditLog` | `backend/app/api/v1/routers/chat.py:153`, `backend/app/api/v1/routers/chat.py:163`, `backend/app/api/v1/routers/chat.py:200`, `backend/app/api/v1/routers/chat.py:210` |
| Screening | Writes raw questionnaire answer maps into `clinical_profiles.phq9_coverage` or `gad7_coverage` | `backend/app/api/v1/routers/screening.py:53`, `backend/app/api/v1/routers/screening.py:55`, `backend/app/api/v1/routers/screening.py:57`, `backend/app/api/v1/routers/screening.py:58` |
| Session summary | Updates `user_profiles`, enqueues `session.ended`, `trigger.observed`, and `coping.attempted`, creates memory cards, then calls Mem0 | `backend/app/services/session_summary.py:114`, `backend/app/services/session_summary.py:145`, `backend/app/services/session_summary.py:153`, `backend/app/services/session_summary.py:173`, `backend/app/services/session_summary.py:180` |
| Voice/TTS | Enqueues and mutates `sync_outbox` rows with voice payload and audio data URI | `backend/app/services/proactive_voice.py:203`, `backend/app/services/proactive_voice.py:363`, `backend/app/services/proactive_voice.py:473` |

#### Backend-only tables

`clinical_profiles`, `risk_inference_log`, `session_risk_snapshots`, `crisis_logs`, `analyst_signals`, `sync_outbox`, `admin_audit_log`, `user_profile_snapshots`, and internal parts of `user_profiles.profile` should be backend-only. SQL RLS enables these tables but intentionally omits user policies for most internal tables (`backend/app/data/core_sql.sql:772` to `backend/app/data/core_sql.sql:779`). However, `user_profiles` has an owner-select policy (`backend/app/data/core_sql.sql:840`) despite containing `clinical_snapshot` in `backend/app/data/user_profile_schema.json:92`.

#### Frontend-safe views/APIs

| Interface | Current safety posture | Evidence |
|---|---|---|
| `app.dashboard_safe_insights` | View selects only safe columns from active/display-allowed `insight_hypotheses` | `backend/app/data/core_sql.sql:666`, `backend/app/data/core_sql.sql:680`, `backend/app/data/core_sql.sql:681`, `backend/app/data/core_sql.sql:682` |
| `/dashboard/safe-insights` | Uses backend service, but may include heuristic profile-derived insight not materialized as `insight_hypotheses` | `backend/app/api/v1/routers/dashboard.py:401`, `backend/app/dashboard/service.py:805` |
| `/dashboard/overview` | Not fully safe because it returns clinical scores and crisis level | `backend/app/api/v1/routers/dashboard.py:130`, `backend/app/api/v1/routers/dashboard.py:134`, `backend/app/api/v1/routers/dashboard.py:135`, `backend/app/api/v1/routers/dashboard.py:137` |
| Frontend TypeScript dashboard contracts | Expects safe insight cards and mood score scale fields | `frontend/src/services/dashboardService.ts:23`, `frontend/src/services/dashboardService.ts:53`, `frontend/src/services/dashboardService.ts:69`, `frontend/src/services/dashboardService.ts:101` |

### Neo4j

#### Labels

Static/reference labels found in `backend/app/data/neo4j_bootstrap_v3.cypher` and patch files include `Disorder`, `DisorderCategory`, `DiagnosticCriterion`, `Instrument`, `Item`, `Symptom`, `Emotion`, `Trigger`, `CopingAction`, `CopingCategory`, `Resource`, `ResourceCategory`, `CognitiveDistortion`, `PsychProcess`, `MedicalCondition`, `SafetyKeyword`, `Substance`, `Agent`, and `AgentCapability`.

Sensitive/runtime labels include `User`, `Session`, `RiskProfile`, `MemoryNode`, and `Assessment` (`backend/app/data/neo4j_bootstrap_v3.cypher:31` to `backend/app/data/neo4j_bootstrap_v3.cypher:40`; runtime contract comments at `backend/app/data/neo4j_bootstrap_v3.cypher:1052` and `backend/app/data/neo4j_bootstrap_v3.cypher:1279`).

#### Relationships

| Relationship class | Examples | Evidence |
|---|---|---|
| Static ontology | `HAS_CRITERION`, `HAS_SYMPTOM`, `HAS_EPISODE`, `DIFFERENTIAL_WITH`, `FLAGS_ITEM`, `MEASURES` | `backend/app/data/neo4j_bootstrap_v3.cypher:757`, `backend/app/data/neo4j_bootstrap_v3.cypher:765`, `backend/app/data/neo4j_bootstrap_v3.cypher:783`, `backend/app/data/neo4j_bootstrap_v3.cypher:803`, `backend/app/data/neo4j_bootstrap_v3.cypher:1048`, `backend/app/data/neo4j_bootstrap_v3.cypher:1336` |
| Sanitized derived aggregate | `EXPERIENCED`, `FELT`, `USED_COPING`, `HAS_SESSION`, `MENTIONS_TRIGGER` | Contract comments in `backend/app/data/neo4j_bootstrap_v3.cypher:1078`, `backend/app/data/neo4j_bootstrap_v3.cypher:1085`, `backend/app/data/neo4j_bootstrap_v3.cypher:1092`; legacy applier in `backend/app/core/outbox_worker.py:139`, `backend/app/core/outbox_worker.py:154`, `backend/app/core/outbox_worker.py:183` |
| Potentially clinical/user-risk | `SUBMITTED_ASSESSMENT`, `INCLUDES_ASSESSMENT`, possible `RiskProfile` relationships | `backend/app/data/neo4j_bootstrap_v3.cypher:1279`, `backend/app/data/neo4j_bootstrap_v3.cypher:1289`, `backend/app/data/neo4j_bootstrap_v3.cypher:1292` |
| Agent/orchestration | `HAS_CAPABILITY`, `HANDLES_DOMAIN` | `backend/app/data/neo4j_bootstrap_v3.cypher:1187`, `backend/app/data/neo4j_bootstrap_v3.cypher:1195`, `backend/app/data/neo4j_bootstrap_v3.cypher:1201` |

#### Static/reference graph

The static graph contains mental-health taxonomy, instruments, items, symptoms, coping actions, resource categories, safety keywords, cognitive distortions, medical-condition priors, and disorder differential links. This can be retained only as internal reference ontology with strict non-diagnostic usage.

#### Derived/user-pattern graph

The intended derived graph is user-anchored aggregates such as `(User)-[:EXPERIENCED]->(Trigger)`, `(User)-[:FELT]->(Emotion)`, `(User)-[:USED_COPING]->(CopingAction)`, and `(User)-[:HAS_SESSION]->(Session)`. The design is privacy-sensitive because user IDs and session IDs are still user-linked operational state.

#### Suspicious user/runtime state

`User`, `Session`, `RiskProfile`, `MemoryNode`, and `Assessment` duplicate PostgreSQL source-of-truth concepts and can become unsafe if they contain raw summaries, item answers, scores, crisis flags, or risk interpretations.

#### Read paths

Direct Neo4j runtime reads are not clearly wired through `backend/app/services/neo4j_client.py`, which only returns a driver (`backend/app/services/neo4j_client.py:12`). The chat model path states its primary knowledge retrieval source is `counseling_knowledge` in Supabase pgvector (`backend/app/services/langgraph_chat.py:419`). Therefore Neo4j appears non-essential for the current hot chat path. Unknown: whether external deployment processes run `backend/app/core/outbox_worker.py` outside FastAPI.

#### Write paths

| Path | Status | Evidence | Risk |
|---|---|---|---|
| Active FastAPI lifespan worker | Does not apply Neo4j graph writes; only notification events are dispatched, then rows are marked done | `backend/app/main.py:52`, `backend/app/services/outbox_worker.py:28`, `backend/app/services/outbox_worker.py:34`, `backend/app/services/outbox_worker.py:68`, `backend/app/services/outbox_worker.py:71` | Silent graph sync loss |
| Legacy/core worker | Has Neo4j applier, but is not wired by FastAPI lifespan and expects different outbox columns | `backend/app/core/outbox_worker.py:94`, `backend/app/core/outbox_worker.py:106`, `backend/app/core/outbox_worker.py:376`, `backend/app/core/outbox_worker.py:381` | Contract drift and likely runtime failure if used with current schema |
| Mem0 graph store | Bypasses `sync_outbox` and can write user-derived memory to Neo4j when env is configured | `backend/app/services/mem0_service.py:77`, `backend/app/services/mem0_service.py:117`, `backend/app/services/session_summary.py:180` | Source-of-truth, privacy, and audit violation |
| Cypher bootstrap/patch scripts | Static writes, forbidden to execute during audit | `backend/app/data/neo4j_bootstrap_v3.cypher:11`, `backend/app/data/neo4j_patch_cbt_workbook.cypher:7` | Acceptable as deployment seed only after clinical scope review |

## 3. Detected Design Problems

| Severity | Problem | Evidence | Why It Matters | Recommended Fix |
|---|---|---|---|---|
| Critical | Mem0 can bypass `sync_outbox` and write user-derived memory to Neo4j. | `backend/app/services/mem0_service.py:get_mem0_config` enables `graph_store` at line 77; `MemoryManager.add_session` calls `self._client.add` at line 117; `backend/app/services/session_summary.py:close_session_summary` passes raw `m.content` at line 180. | Violates "Neo4j derived/reference only"; raw or sensitive user text may be processed into graph outside audit, masking, retry, and allowed-payload controls. | Disable Mem0 Neo4j graph store for MVP; use pgvector only; if graph memory is reintroduced, write sanitized aggregate events only via `sync_outbox`. |
| Critical | Active outbox worker marks non-notification graph events done without applying Neo4j writes. | `backend/app/main.py:_outbox_loop` imports `app.services.outbox_worker` at line 53; `_dispatch_async` only handles notification event types at `backend/app/services/outbox_worker.py:34`; processing marks row `done` at line 71. | `session.ended`, `trigger.observed`, and `coping.attempted` events can be lost while appearing successfully processed. | Split notification queue from graph sync or implement one canonical dispatcher that fails unsupported events instead of marking them done. |
| Critical | Legacy Neo4j outbox worker expects schema columns not present in canonical SQL/model. | `backend/app/core/outbox_worker.py:_process_batch` returns `o.attempts` and uses `processing_started_at` at lines 376 to 381; `backend/app/data/core_sql.sql:689` defines `retry_count` but not `attempts` or `processing_started_at`; `backend/app/services/db/models.py:617` has no `attempts` or `processing_started_at`. | The only worker with graph logic is schema-incompatible, while the active worker lacks graph logic. | Reconcile `sync_outbox` schema and worker contract; choose `retry_count` and `processing_started_at` or migrate all code to a canonical alternative. |
| Critical | User-facing dashboard overview exposes clinical/risk state. | `backend/app/api/v1/routers/dashboard.py:overview` reads `ClinicalProfile` at line 130 and returns `phq9_score`, `gad7_score`, `crisis_level` at lines 134 to 137. | Violates frontend boundary and can imply diagnosis or risk classification to users. | Remove clinical fields from `/dashboard/overview`; expose only non-diagnostic wellness summaries through safe DTOs. |
| High | `user_profiles` is client-readable despite containing internal clinical snapshot schema. | RLS owner-select policy at `backend/app/data/core_sql.sql:840`; `backend/app/data/user_profile_schema.json:92` describes `clinical_snapshot` as denormalized copy of `clinical_profiles` and internal only. | Direct Supabase reads could expose clinical/risk rollup and safety flags. | Remove direct user select on full `user_profiles`; create `user_profiles_safe` view or backend-only access. |
| High | Analyst signal and insight materialization pipeline appears incomplete. | `AnalystSignal` and `InsightHypothesis` models exist at `backend/app/services/db/models.py:440` and `backend/app/services/db/models.py:490`, but repository search found no `AnalystSignal(` or `InsightHypothesis(` writer outside models. | Dashboard insight can rely on heuristics instead of auditable analyst evidence. | Implement explicit `analyst_signals -> insight_hypotheses` writer before claiming evidence-backed dashboard intelligence. |
| High | Dashboard safe-insight service falls back to heuristic profile cards. | SQL insight fetch at `backend/app/dashboard/service.py:158`; heuristic cards generated at lines 246, 277, and 305. | User-facing claims may not have persisted evidence rows, evidence windows, or stable audit IDs. | Persist heuristic results as low-confidence `insight_hypotheses` or label them as non-insight hints. |
| High | Screening API stores raw questionnaire answers inside `clinical_profiles` JSON fields. | `backend/app/api/v1/routers/screening.py:55` and line 58 set `{"answers": payload.answers}` in coverage JSON. | Raw questionnaire answers are sensitive clinical-adjacent data; storing them in generic coverage fields complicates access control and retention. | Store only coverage booleans in `clinical_profiles`; if raw answers are retained, use a dedicated backend-only `screening_answers` table with retention policy. |
| High | Neo4j contains diagnostic/differential graph semantics that can imply clinical reasoning if used in user-facing paths. | `HAS_CRITERION` at `backend/app/data/neo4j_bootstrap_v3.cypher:757`; `HAS_SYMPTOM` at line 765; `HAS_EPISODE` at line 783; `DIFFERENTIAL_WITH` at line 803; `AgentCapability` `differential_diagnosis` at line 1180. | Clinical ontology can drive diagnostic overreach without licensed clinical governance. | Keep internal-only and post-MVP; rename to safer abstractions or quarantine from generation context. |
| Medium | `core_sql.sql` omits feature tables implemented by Alembic and SQLAlchemy models. | `core_sql.sql` defines core tables through `sync_outbox` at `backend/app/data/core_sql.sql:689`; feature tables are created in `backend/alembic/versions/0016_create_app_feature_tables.py:57`, `:192`, `:242`; models include them at `backend/app/services/db/models.py:638`, `:824`, `:876`. | Environment setup differs depending on whether SQL file or Alembic is used. | Declare Alembic as canonical production migration path or regenerate SQL from migrations. |
| Medium | Some Alembic revisions create unqualified tables and later migrate them into `app`. | `backend/alembic/versions/0003_counseling_knowledge.py:28` creates `counseling_knowledge` without explicit schema; later revisions move feature tables from `public` to `app` in `backend/alembic/versions/0016_create_app_feature_tables.py:20` and line 49. | Search-path dependent migrations are fragile in Supabase/PostgreSQL. | Use explicit `schema="app"` or fully qualified DDL for every production migration. |
| Medium | `sync_outbox` is overloaded as graph queue, notification queue, and voice/TTS durable job table. | Notification event set in `backend/app/services/outbox_worker.py:14`; voice event type in `backend/app/services/proactive_voice.py:37`; graph event producers in `backend/app/services/session_summary.py:33`, `:47`, `:153`. | Mixed lifecycle semantics cause latency, retry, payload, and ownership conflicts. | Split into `sync_outbox`, `notification_outbox`, and `tts_jobs`, or add strict typed event families and dispatchers. |
| Medium | TTS audio is persisted as `audio_data_uri` inside `sync_outbox.payload`. | `backend/app/services/proactive_voice.py:363` embeds audio bytes; `backend/app/services/proactive_voice.py:473` repairs payload with data URI. | Large JSONB payloads bloat queue rows and degrade polling/index performance. | Store audio in object storage or dedicated blob table; keep only job status and storage key in queue. |
| Medium | JSONB is used for operationally important fields without enough schema enforcement. | `user_profiles.profile` at `backend/app/services/db/models.py:590`; `SyncOutbox.payload` at line 627; reward metadata/requirements at lines 781 and 782; `memory_cards.metadata` at line 862. | Queryability, validation, and RLS become weaker; schema drift can hide in JSON. | Keep JSONB for flexible metadata only; move frequently queried or sensitive fields to typed columns. |
| Medium | Risk inference and session risk snapshot tables exist but writer paths are unclear. | Models exist at `backend/app/services/db/models.py:370` and `backend/app/services/db/models.py:395`; search found no `RiskInferenceLog(` or `SessionRiskSnapshot(` constructor outside models. | Safety audit trail may be incomplete despite docs requiring it. | Add synchronous risk snapshot/log writes for safety-relevant turns or update docs to reflect actual state. |
| Medium | `dashboard_safe_insights` SQL view exists but backend does not read the view directly. | View at `backend/app/data/core_sql.sql:666`; backend reads `InsightHypothesis` model in `backend/app/dashboard/service.py:158`. | Security relies on backend filtering instead of one canonical safe view. | Use the view or mirror its exact field contract in one service DTO with tests. |
| Low | Missing repository locations requested by audit prompt. | `supabase/migrations/**` and `database/**` were not present; only `scripts/supabase` directory was found. | Evidence cannot confirm Supabase migration parity. | Document absence and make Alembic/core SQL canonical decision explicit. |

## 4. Supabase/PostgreSQL Audit Result

### Correct tables

| Table | Classification | Current assessment |
|---|---|---|
| `users` | Source of truth | Correct owner for identity and consent, with optional Supabase auth mapping in `backend/app/data/core_sql.sql:81`. |
| `conversations`, `messages` | Source of truth | Correct transcript/session SoT; chat writes masked user messages in `backend/app/api/v1/routers/chat.py:504` to `:511`. |
| `mood_checkins` | Source of truth | Correct self-report table; mood score constrained 1 to 5 in SQL at `backend/app/data/core_sql.sql:236`. |
| `memory_cards` | Source of truth for user-controlled memory review | Correct product state table in `backend/alembic/versions/0016_create_app_feature_tables.py:192`, but absent from `core_sql.sql`. |
| `conversation_memories` | Source of truth for semantic memory | Correct pgvector table in `backend/app/data/core_sql.sql:331`, but strict PII and source governance must be enforced. |
| `clinical_profiles`, `risk_inference_log`, `session_risk_snapshots`, `crisis_logs` | Backend-only safety/clinical audit | Correct location, but write paths for risk tables are incomplete or unclear. |
| `analyst_signals`, `insight_hypotheses`, `dashboard_safe_insights` | Derived analyst/dashboard layer | Correct target design, but pipeline writer evidence is missing. |
| Rewards/hearts/persona tables | Product source of truth | Correctly PostgreSQL-only in models and Alembic; should not be in Neo4j. |
| `sync_outbox` | Operational queue | Correct location, but overloaded and contract-drifted. |

### Missing tables

| Expected from docs or code | Current evidence | Required action |
|---|---|---|
| `tts_jobs` | Docs mention `tts_jobs` in `docs/PRD.md:845` and `docs/PRD.md:1031`; implementation uses `sync_outbox` voice payloads in `backend/app/services/proactive_voice.py:203`. | Create dedicated `tts_jobs` or formally document `sync_outbox` voice-job contract and add typed payload constraints. |
| `heart_ledger`, `reward_inventory` | Docs mention these in `docs/PRD.md:844`; implementation uses `heart_reward_events`, `heart_spend_events`, and `user_inventory_items`. | Update docs or add compatibility views if external contracts expect old names. |
| Supabase migrations | `supabase/migrations/**` absent. | Mark Alembic as canonical or add Supabase migration export. |
| `database/**` | Directory absent. | Remove from audit checklist or create canonical database docs location. |

### Redundant tables

| Tables | Redundancy risk | Recommendation |
|---|---|---|
| `conversation_memories` and `memory_cards` | Both store memory-like content; one is semantic/RAG memory, the other is user-reviewed memory UI state. | Keep both only if semantics are explicit: `conversation_memories` for retrieval, `memory_cards` for user control and consent. Link with optional FK/reference where appropriate. |
| `clinical_profiles`, `risk_inference_log`, `session_risk_snapshots`, `analyst_signals` | Multiple risk/clinical-adjacent stores can diverge. | Define ownership: safety snapshots/logs own risk events; clinical profile owns current screening summary; analyst signals own non-user-facing observations. |
| `user_profiles.profile.clinical_snapshot` and `clinical_profiles` | Denormalized internal copy can expose or drift from source. | Remove clinical snapshot from user-readable profile; keep only backend cache if unavoidable. |
| `sync_outbox` and voice job state | Queue row doubles as durable job record and binary/audio carrier. | Split TTS into dedicated job table or queue family. |

### Tables to merge

| Merge candidate | Decision |
|---|---|
| `heart_reward_events` and `heart_spend_events` | Consider merge into a signed `heart_ledger` only if product needs unified balance audit. Current split is acceptable for MVP if wallet invariants are tested. |
| `user_profile_snapshots` and `session_summaries_archive` | Do not merge; they serve different audit purposes. |
| `analyst_signals` and `risk_inference_log` | Do not merge; analyst observations and safety risk audit should stay separate. |

### Tables to convert to views/materialized views

| Candidate | Recommendation |
|---|---|
| Dashboard summary aggregations | Convert expensive computed dashboard rollups to materialized view or derived table if latency grows; keep `dashboard_safe_insights` as a safe view. |
| `user_profiles` frontend subset | Create `user_profiles_safe` view, or remove direct RLS read and expose backend DTO only. |
| Reward store shelves | If shelf rendering is computed from store metadata, use a view rather than duplicating shelf state. |

### Missing indexes

| Area | Current evidence | Risk | Fix |
|---|---|---|---|
| Feature tables | `indexes.sql` covers core but not all feature tables; `memory_cards` index exists in migration at `backend/alembic/versions/0016_create_app_feature_tables.py:224`. | Wallet/reward/persona/knowledge endpoints may scan under growth. | Add indexes for `heart_reward_events(user_id, created_at)`, `heart_spend_events(user_id, created_at)`, `persona_unlock_states(user_id, unlocked)`, `user_inventory_items(user_id)`, `user_knowledge_progress(user_id, pack_id)`, and voice job event/status if staying in outbox. |
| `sync_outbox` voice polling | `indexes.sql` has `idx_sync_outbox_status_created` at `backend/app/data/indexes.sql:160`, but voice polling filters event type and status in `backend/app/services/proactive_voice.py:572` and `:595`. | Queue polling can degrade as graph, notification, and voice rows mix. | Add composite partial indexes by `event_type`, `status`, `created_at`, or split tables. |
| Dashboard history | Dashboard loads all check-ins for history then filters in Python in `backend/app/api/v1/routers/dashboard.py:385`. | Latency and memory overhead for active users. | Apply DB date range filters and maintain `(user_id, logged_date, logged_at)` index. |

### Missing constraints

| Table/field | Current issue | Fix |
|---|---|---|
| `SyncOutbox.status` model | SQL has status check at `backend/app/data/core_sql.sql:695`; model lacks equivalent check at `backend/app/services/db/models.py:628`. | Add model-level or migration-level parity test. |
| `SyncOutbox.payload` | No event-specific validation. | Add Pydantic payload validators per event family. |
| `ClinicalProfile.phq9_coverage/gad7_coverage` | JSON accepts raw answers and arbitrary shape. | Separate coverage from raw answers; validate keys and values. |
| `UserProfile.profile` | JSON schema file exists, but runtime validation evidence is unclear. | Validate before insert/update or replace sensitive subtrees with typed columns. |

### Excessive JSONB

| Field | Evidence | Risk | Fix |
|---|---|---|---|
| `user_profiles.profile` | `backend/app/services/db/models.py:590`; schema includes many domains including clinical snapshot. | Overbroad cache becomes hidden source of truth and exposure risk. | Split frontend-safe profile, internal rollup, and clinical/safety fields. |
| `sync_outbox.payload` | `backend/app/services/db/models.py:627`; voice stores audio data URI in payload at `backend/app/services/proactive_voice.py:363`. | Queue bloat and untyped payload drift. | Typed payloads; keep blobs out of JSONB. |
| `clinical_profiles.*_coverage` | `backend/app/services/db/models.py:203`, `:204`; raw answers written in `screening.py:55`, `:58`. | Sensitive clinical answers hidden in generic JSON. | Dedicated screening answer table or strict coverage booleans. |
| Reward/item/persona metadata | `backend/app/services/db/models.py:781`, `:782`, `:814`, `:815`. | Acceptable if metadata is display-only, risky if used for entitlement logic. | Move entitlement-critical fields to typed columns. |

### RLS/security gaps

| Gap | Evidence | Risk | Fix |
|---|---|---|---|
| `user_profiles` owner select includes internal JSON. | `backend/app/data/core_sql.sql:840`; `user_profile_schema.json:92`. | Clinical/safety rollup exposure. | Backend-only table plus safe view. |
| `conversation_memories` owner select may reveal extracted memory content. | Policy at `backend/app/data/core_sql.sql:835`. | Users may read memories not yet reviewed or safety-approved. | Expose user-reviewed `memory_cards`; restrict raw semantic memory to backend. |
| Internal tables RLS has no direct user policy, which is good, but backend APIs leak some fields. | `/dashboard/overview` evidence above. | API bypasses intended frontend boundary. | DTO tests for no clinical/risk fields. |
| Feature tables RLS not shown in `core_sql.sql` for all Alembic-created feature tables. | Feature tables are absent from `core_sql.sql`; created in Alembic 0016. | Direct Supabase access may be inconsistent if feature RLS not applied elsewhere. | Add explicit RLS policies for all app-scoped feature tables or force backend-only access. |

### Dangerous migration patterns

| Migration/file | Issue | Risk | Fix |
|---|---|---|---|
| `backend/app/data/core_sql.sql` | Contains `drop table if exists extensions.* cascade` at lines 35 to 47. | Unsafe if run in production without review. | Mark bootstrap-only; never use as production migration. |
| `backend/alembic/versions/0001_init_schema.py` | Uses `Base.metadata.create_all` and `drop_all` at lines 16 and 21. | Alembic history can become model-state dependent and downgrade destructive. | Replace with explicit generated migration or forbid downgrade in production. |
| `backend/alembic/versions/0003_counseling_knowledge.py` | Unqualified `CREATE TABLE counseling_knowledge` at line 28. | Search-path dependent schema placement. | Qualify `app.counseling_knowledge`. |
| `backend/app/main.py` | Runtime startup attempts `ALTER TABLE sync_outbox` and swallows errors at lines 24 to 33. | Runtime DDL is operationally unsafe and invisible on failure. | Move schema repair to migration. |

### Source-of-truth conflicts

`user_profiles` is documented as cache/rollup but is used as dashboard input and contains clinical snapshot fields. `InsightHypothesis` is documented as dashboard insight source of truth, but backend can generate heuristic cards directly from `user_profiles`. Neo4j `User`, `Session`, `Assessment`, `RiskProfile`, and `MemoryNode` duplicate PostgreSQL entities and must remain derived only.

### Dashboard evidence issues

Safe SQL insight rows include `evidence_count` and windows, but fallback heuristic cards create user-facing observations from profile aggregates without persisted evidence rows. The frontend expects `InsightCard.evidence_count`, `evidence_sources`, and confidence fields in `frontend/src/services/dashboardService.ts:23`; backend can supply those even when not backed by `insight_hypotheses`.

### Reward/persona/TTS storage correctness

Rewards, hearts, inventory, and persona unlocks are correctly stored in PostgreSQL-only tables. TTS jobs are not correctly isolated: they use `sync_outbox` with large JSON payloads and embedded audio. This is acceptable as a prototype but not as an MVP-safe durable queue under healthcare-adjacent constraints.

## 5. Neo4j Audit Result

### Sensitive label classification

| Label | Classification | Decision | Evidence | Reason |
|---|---|---|---|---|
| `User` | User-derived runtime anchor | Keep only as sanitized derived aggregate or remove for MVP | `backend/app/data/neo4j_bootstrap_v3.cypher:31`, `backend/app/data/neo4j_bootstrap_v3.cypher:1056` | Duplicates PostgreSQL user; privacy-sensitive. |
| `Session` | User-derived runtime summary | Keep only if sanitized and outbox-derived; otherwise move to PostgreSQL only | `backend/app/data/neo4j_bootstrap_v3.cypher:32`, `backend/app/data/neo4j_bootstrap_v3.cypher:1060` | Session state is PostgreSQL SoT. |
| `RiskProfile` | Runtime/safety state | Remove from Neo4j for MVP | `backend/app/data/neo4j_bootstrap_v3.cypher:34` | Risk belongs in backend-only PostgreSQL tables. |
| `MemoryNode` | Runtime memory pointer | Remove or keep only hash/id without content post-MVP | `backend/app/data/neo4j_bootstrap_v3.cypher:35`, `backend/app/data/neo4j_bootstrap_v3.cypher:1103` | Memory content and review state belong in PostgreSQL/pgvector. |
| `Assessment` | Clinical/screening runtime state | Move to PostgreSQL backend-only | `backend/app/data/neo4j_bootstrap_v3.cypher:40`, `backend/app/data/neo4j_bootstrap_v3.cypher:1279` | Assessment history and raw answers are sensitive. |
| `Agent`, `AgentCapability` | Static orchestration metadata | Defer post-MVP or remove from Neo4j | `backend/app/data/neo4j_bootstrap_v3.cypher:38`, `backend/app/data/neo4j_bootstrap_v3.cypher:1162`, `backend/app/data/neo4j_bootstrap_v3.cypher:1180` | Agent boundaries are code contracts, not graph product data. |
| `Disorder`, `DisorderCategory` | Static clinical ontology | Keep static/internal only or defer | `backend/app/data/neo4j_bootstrap_v3.cypher:11`, `backend/app/data/load_data.py:84` | Too clinical for user-facing logic. |
| `DiagnosticCriterion` | Static clinical ontology | Defer post-MVP or keep internal-only | `backend/app/data/neo4j_bootstrap_v3.cypher:14`, `backend/app/data/neo4j_bootstrap_v3.cypher:757` | Diagnostic criteria can imply diagnosis. |
| `Instrument`, `Item` | Static screening taxonomy | Keep static/internal only | `backend/app/data/neo4j_bootstrap_v3.cypher:17`, `backend/app/data/neo4j_bootstrap_v3.cypher:278` | Useful for metadata, not storage of answers. |
| `Symptom` | Static ontology | Rename to safer abstraction if user-facing, e.g. `WellnessSignal` | `backend/app/data/neo4j_bootstrap_v3.cypher:765` | `Symptom` increases clinical framing. |
| `Emotion`, `Trigger` | Static taxonomy plus aggregate anchors | Keep as safer static taxonomy/sanitized aggregate | `backend/app/data/neo4j_bootstrap_v3.cypher:28`, `backend/app/data/neo4j_bootstrap_v3.cypher:29` | Useful for non-diagnostic patterns. |
| `CopingAction`, `CopingCategory` | Static taxonomy | Keep static taxonomy | `backend/app/data/neo4j_bootstrap_v3.cypher:26`, `backend/app/data/neo4j_patch_cbt_workbook.cypher:143` | Product-aligned and low clinical risk. |
| `Resource`, `ResourceCategory` | Static/reference content | Prefer PostgreSQL for product catalog; Neo4j optional taxonomy | `backend/app/data/neo4j_bootstrap_v3.cypher:24`; PostgreSQL `resources` at `backend/app/data/core_sql.sql:270` | Resource availability/product state belongs in PostgreSQL. |
| `CognitiveDistortion` | Static CBT taxonomy | Keep static/internal or rename to `ThinkingPattern` | `backend/app/data/neo4j_patch_cbt_workbook.cypher:7` | Useful but should avoid pathologizing labels in UI. |
| `MedicalCondition` | Static medical ontology | Defer post-MVP | `backend/app/data/neo4j_bootstrap_v3.cypher:20`, `backend/app/data/neo4j_bootstrap_v3.cypher:1223` | Medical differential logic is high-risk. |
| `SafetyKeyword` | Static safety keyword ontology | Keep internal-only | `backend/app/data/neo4j_bootstrap_v3.cypher:30`, `backend/app/data/neo4j_bootstrap_v3.cypher:1024` | Safety reference is useful, but raw crisis events must not sync. |

### Correct labels

For MVP, correct labels are limited to `Emotion`, `Trigger`, `CopingAction`, `CopingCategory`, optional `ResourceCategory`, optional `CognitiveDistortion` renamed or guarded, and internal-only safety keyword taxonomy. These should be static or sanitized aggregate anchors only.

### Correct relationships

`IN_COPING_CATEGORY`, `TARGETS_SYMPTOM` only if `Symptom` is not user-facing, `COMMONLY_TRIGGERS`, and sanitized aggregate `EXPERIENCED`, `FELT`, `USED_COPING` are acceptable if every write goes through a validated outbox event and carries no raw text, PII, crisis content, direct score, or diagnosis assignment.

### Labels to remove

Remove or quarantine from MVP: `RiskProfile`, `Assessment`, `MemoryNode`, `Agent`, `AgentCapability`, `MedicalCondition`, and user-linked `Session` unless the implementation proves sanitized outbox-only writes.

### Labels to rename

| Current label | Safer abstraction |
|---|---|
| `Symptom` | `WellnessSignal` or `SupportSignal` |
| `CognitiveDistortion` | `ThinkingPattern` |
| `DiagnosticCriterion` | Keep internal name only; do not expose |
| `Disorder` | Keep internal ontology only; do not expose |

### Relationships that imply diagnosis

`HAS_CRITERION`, `HAS_SYMPTOM`, `HAS_EPISODE`, `DIFFERENTIAL_WITH`, `CAUSES_SYMPTOM`, `RULE_OUT_SCREEN`, `SUBMITTED_ASSESSMENT`, and any possible `User -> Disorder` edge are diagnosis-adjacent. No direct user-to-disorder, user-to-diagnostic-criterion, user-to-medical-condition, or user-has-diagnosis relationship should exist.

### User/runtime data that should not be in Neo4j

Raw messages, PII, raw questionnaire answers, crisis logs, clinical profile values, risk snapshots, direct PHQ/GAD answer maps, direct disorder labels, TTS jobs, rewards, wallet state, persona unlocks, and operational state should remain PostgreSQL-only.

### Graph queries that are justified

Neo4j is justified for reference lookups where graph traversal is materially useful: coping strategy relationships, CBT/thinking-pattern taxonomy, non-diagnostic emotion-trigger-coping relationships, and optional analyst reference retrieval. It is not justified for identity, session history, dashboard instances, wallet/persona state, TTS, or safety audit.

### Graph queries that should be replaced by PostgreSQL

User session history, memory retrieval, dashboard insight retrieval, reward entitlement, persona unlock gating, knowledge progress, screening results, and all safety/risk logic should use PostgreSQL and pgvector.

### Whether Neo4j is useful for Analyst Agent

Useful only as an internal reference ontology. Current evidence shows primary chat retrieval points to Supabase pgvector (`backend/app/services/langgraph_chat.py:419`), so Neo4j is not required for current hot-path reasoning.

### Whether Neo4j should be reduced to static taxonomy for MVP

Yes. The MVP-safe Neo4j scope is static taxonomy plus optional sanitized aggregate graph after the outbox contract is fixed. User-linked runtime graph should be disabled until tests prove no raw, PII, crisis, clinical, diagnostic, or operational state enters Neo4j.

### Supabase vs Neo4j boundary audit

| Data / Logic Type | Current Location | Correct Location | Evidence | Risk If Wrong | Recommended Fix |
|---|---|---|---|---|---|
| User profile | PostgreSQL `user_profiles`; possible Neo4j `User` anchor | Supabase/PostgreSQL | `backend/app/services/db/models.py:574`; Neo4j `User` constraint at `backend/app/data/neo4j_bootstrap_v3.cypher:31` | User profile becomes duplicated and exposed in graph. | Keep profile in PostgreSQL; Neo4j may store only opaque user anchor for aggregates, or remove for MVP. |
| Auth/session tokens | PostgreSQL custom auth tables | Supabase/PostgreSQL | `backend/app/data/core_sql.sql:110`, `:124`, `:143`, `:154` | Token state in graph/cache would be security violation. | Keep PostgreSQL-only. |
| Chat sessions | PostgreSQL and optional Neo4j `Session` | Supabase/PostgreSQL | `backend/app/data/core_sql.sql:168`; Neo4j `Session` at `backend/app/data/neo4j_bootstrap_v3.cypher:32` | Duplicated session SoT and privacy exposure. | Keep PostgreSQL SoT; Neo4j only sanitized session aggregate if needed. |
| Raw chat messages | PostgreSQL `messages` | Supabase/PostgreSQL only | `backend/app/data/core_sql.sql:191`; chat writes at `backend/app/api/v1/routers/chat.py:506` | Raw message in Neo4j violates privacy. | Never sync raw content; disable Mem0 graph store. |
| Memory cards | PostgreSQL `memory_cards` | Supabase/PostgreSQL | `backend/alembic/versions/0016_create_app_feature_tables.py:192` | User review state could diverge if graphed. | Keep PostgreSQL-only. |
| Mood check-ins | PostgreSQL `mood_checkins`; possible aggregate graph triggers/emotions | Supabase/PostgreSQL | `backend/app/data/core_sql.sql:231`; Neo4j aggregate contracts at `backend/app/data/neo4j_bootstrap_v3.cypher:1078` | Raw notes/triggers could leak. | Store raw in PostgreSQL; only sanitized labels may sync. |
| Nutrition/self-report | PostgreSQL `nutrition_meal_checkins` | Supabase/PostgreSQL | `backend/alembic/versions/0016_create_app_feature_tables.py:156` | Health-adjacent self-report in graph increases sensitive surface. | PostgreSQL-only. |
| Safety/SOS events | PostgreSQL `crisis_logs` and audit | PostgreSQL secure/backend-only tables | `backend/app/data/core_sql.sql:536`; writes at `backend/app/api/v1/routers/chat.py:153` | Crisis content in graph is critical privacy violation. | PostgreSQL-only; no outbox to Neo4j. |
| Risk snapshots | PostgreSQL models exist | PostgreSQL backend-only | `backend/app/services/db/models.py:395`; no writer found | Missing audit or graph leakage risk. | Add PostgreSQL-only writes; prohibit Neo4j risk sync. |
| Clinical/screening profile | PostgreSQL `clinical_profiles`; Neo4j `Assessment` contract exists | PostgreSQL backend-only | `backend/app/services/db/models.py:190`; Neo4j assessment at `backend/app/data/neo4j_bootstrap_v3.cypher:1279` | Clinical answer/score duplication. | Move assessment history to PostgreSQL only; remove graph runtime assessment. |
| Analyst raw signals | PostgreSQL model only | PostgreSQL backend-only | `backend/app/services/db/models.py:440`; no writer found | If surfaced or graphed, internal notes leak. | Implement PostgreSQL writer; backend-only access. |
| Dashboard insight instances | PostgreSQL `insight_hypotheses` and view | PostgreSQL derived table/view | `backend/app/data/core_sql.sql:603`, `:666` | Non-evidence dashboard claims. | Read/write only evidence-backed safe insights. |
| Mental-health ontology | Neo4j Cypher static graph | Neo4j or static taxonomy | `backend/app/data/neo4j_bootstrap_v3.cypher:11` | Overengineering if not used. | Keep static/internal; consider JSON/PostgreSQL taxonomy for MVP. |
| Coping strategy taxonomy | Neo4j patch/static graph and app catalog | Neo4j or static taxonomy | `backend/app/data/neo4j_patch_cbt_workbook.cypher:143`; `backend/app/rewards/catalog.py` for product catalog patterns | Low risk if static. | Keep static and non-diagnostic. |
| Disorder taxonomy | Neo4j | Neo4j static/internal only | `backend/app/data/load_data.py:84`; `backend/app/data/neo4j_bootstrap_v3.cypher:11` | Direct diagnosis implications. | Internal-only or defer. |
| Diagnostic criteria | Neo4j | Neo4j static/internal only, if retained | `backend/app/data/neo4j_bootstrap_v3.cypher:14`, `:757` | Diagnostic overreach. | Quarantine from user-facing prompts. |
| User-derived abstract patterns | PostgreSQL profile/memory plus intended Neo4j aggregates | PostgreSQL SoT + optional sanitized Neo4j derived graph | `backend/app/services/session_summary.py:33`, `:47`, `:153`; Neo4j aggregate contracts at `backend/app/data/neo4j_bootstrap_v3.cypher:1078` | Duplicated SoT and privacy leakage. | Outbox-only sanitized aggregates. |
| Rewards/hearts | PostgreSQL | Supabase/PostgreSQL only | `backend/app/services/db/models.py:638`, `:656`, `:749` | Wallet inconsistency. | PostgreSQL-only with backend mutations. |
| Persona unlocks | PostgreSQL | Supabase/PostgreSQL only | `backend/app/services/db/models.py:805`; `backend/app/services/persona_unlock_persistence.py:28` | Persona state could bypass safety if duplicated. | PostgreSQL-only. |
| TTS jobs/status | `sync_outbox` payload | Supabase/PostgreSQL or durable queue, not Neo4j | `backend/app/services/proactive_voice.py:37`, `:203`, `:363` | Queue bloat and wrong graph boundary. | Dedicated `tts_jobs` or typed queue; never Neo4j. |
| Graph sync queue | PostgreSQL `sync_outbox` | Supabase/PostgreSQL `sync_outbox` | `backend/app/data/core_sql.sql:689` | Data loss if dispatcher wrong. | Fix canonical worker and event schema. |

## 6. Correct Target Architecture

| Data Domain | Correct Database | Reason | Notes |
|---|---|---|---|
| Users | Supabase/PostgreSQL | Identity, consent, and retention are durable product state. | Neo4j may use only opaque anchor if aggregate graph is retained. |
| Sessions | Supabase/PostgreSQL | Session lifecycle and transcript linkage are SoT data. | Neo4j session node optional sanitized aggregate only. |
| Messages | Supabase/PostgreSQL | Raw and masked transcript governance requires SQL audit and retention. | Never write raw messages to Neo4j. |
| Memory cards | Supabase/PostgreSQL | User review, edit, delete, and personalization consent are product state. | Separate from vector retrieval memory. |
| Long-term semantic memory | Supabase/PostgreSQL + pgvector | Retrieval is vector search over approved/masked summaries. | Disable direct graph memory for MVP. |
| Check-ins | Supabase/PostgreSQL | Self-report, notes, and trend evidence are user data. | Sync only sanitized aggregate labels if needed. |
| Nutrition/self-report | Supabase/PostgreSQL | Health-adjacent self-report is sensitive user data. | No Neo4j. |
| Safety events | PostgreSQL secure/backend-only | Synchronous audit and crisis governance. | No frontend direct access. |
| Risk snapshots | PostgreSQL secure/backend-only | Safety routing and audit require durable backend-only records. | No Neo4j. |
| Clinical/screening profile | PostgreSQL secure/backend-only | Clinical-adjacent scores/coverage require access control. | Avoid raw answers in generic JSON. |
| Analyst raw signals | PostgreSQL backend-only | Internal observations and rationale must not surface directly. | Feed safe insight materializer only. |
| Dashboard insights | PostgreSQL derived table/view | User-facing insight instances need evidence and audit. | `dashboard_safe_insights` should be canonical frontend shape. |
| Rewards/hearts | Supabase/PostgreSQL | Wallet and ledger require transactional integrity. | Backend-only mutations. |
| Persona unlocks | Supabase/PostgreSQL | Entitlements and safety gating are product state. | Do not let persona override safety. |
| TTS jobs/status | Supabase/PostgreSQL or durable queue | Durable job status, retry, and storage references. | Prefer dedicated table over generic outbox. |
| Mental-health ontology | Neo4j/static taxonomy | Static reference relationships can help analyst lookup. | Internal-only and non-diagnostic. |
| Coping strategy taxonomy | Neo4j/static taxonomy | Graph traversal can connect triggers, emotions, and coping actions. | Safe if non-clinical. |
| Derived pattern graph | Optional sanitized Neo4j | Can support aggregate pattern reasoning post-MVP. | Outbox-only, no raw text/PII/crisis/diagnosis. |
| Neo4j sync queue | Supabase/PostgreSQL `sync_outbox` | PostgreSQL must own sync state and retry. | One canonical worker and typed payloads. |

Target flow:

```text
PostgreSQL SoT
-> async workers / sync_outbox
-> sanitized Neo4j derived graph
-> Analyst reference lookup
-> AnalystBundle
-> safe PostgreSQL insight
-> dashboard_safe_insights
-> Frontend
```

## 7. Recommended Refactor Plan

### Phase 0 - Documentation Freeze

Create or update `DATABASE_ARCHITECTURE.md` with a canonical source-of-truth matrix. Define allowed and forbidden Neo4j data. Freeze schema naming and table ownership. Mark `core_sql.sql` as bootstrap-only if Alembic is the production migration path.

### Phase 1 - Schema Drift Fix

Align SQL, Alembic migrations, SQLAlchemy models, Pydantic schemas, and frontend TypeScript types. Add parity tests for table existence, column names, check constraints, and enum values. Decide canonical mood/check-in scale and document 1-to-5 mapping. Remove runtime DDL from FastAPI startup. Reconcile `sync_outbox` columns across SQL, models, and worker code.

### Phase 2 - PostgreSQL Cleanup

Clarify `conversation_memories` versus `memory_cards`. Convert `user_profiles` to explicit backend cache semantics and remove user-readable clinical/safety subtrees. Move dashboard insight output to evidence-backed `insight_hypotheses` and `dashboard_safe_insights`. Ensure feature tables have RLS or backend-only access policies. Split TTS jobs from generic outbox or enforce typed voice payloads without embedded audio blobs.

### Phase 3 - Neo4j Boundary Fix

Disable Mem0 Neo4j graph store. Remove or quarantine `RiskProfile`, `Assessment`, `MemoryNode`, and user-linked `Session` from MVP graph sync. Keep static taxonomy and optional sanitized aggregates only. Rename or hide clinical labels from any user-facing prompt path. Ensure every graph write goes through one validated `sync_outbox` dispatcher.

### Phase 4 - Agent Read/Write Path Fix

Conversation Agent should read user context from PostgreSQL and pgvector only; Neo4j write success must never block response. Analyst Agent should read PostgreSQL events and use Neo4j only as internal reference ontology. Safety Agent should synchronously write PostgreSQL-only safety/risk/crisis state. Dashboard should read only safe derived APIs/views. Persona/reward/wallet mutations should remain backend-only.

### Phase 5 - Validation & Regression Tests

Add tests for:

| Test | Expected result |
|---|---|
| No raw message write to Neo4j | Graph payload tests reject `content`, transcript text, and unmasked PII fields. |
| No PII write to Neo4j | Outbox graph payload validator rejects email, phone, address, name-like free text. |
| No crisis/risk log sync to Neo4j | `crisis_logs`, `risk_inference_log`, `session_risk_snapshots` never produce graph events. |
| No direct disorder assignment edge | Reject `User -> Disorder`, `User -> DiagnosticCriterion`, and diagnosis labels. |
| Dashboard insight requires evidence | User-facing insight cards must come from `insight_hypotheses` or be labeled non-insight. |
| Frontend cannot read backend-only tables | RLS/API tests prevent clinical/risk/analyst raw field exposure. |
| Reward/persona/wallet backend-only | Frontend cannot mutate wallet/persona state without backend service. |
| Neo4j unavailable does not break chat | Chat persists messages and returns response while sync remains pending/failed. |
| Sync outbox failure does not block normal response | Failed graph sync records error and retry without affecting user response. |
| Voice job payload size | TTS job rows contain storage references, not large base64 audio JSON. |

## 8. Final Recommendation

### Should Serene keep both Supabase and Neo4j?

Yes, but only with a narrower contract. Supabase/PostgreSQL must remain the sole durable source of truth. Neo4j should be retained only as static/internal mental-health and coping taxonomy plus optional sanitized derived aggregate graph after outbox governance is repaired.

### If yes, what exactly should Neo4j do?

Neo4j should provide internal reference traversal for non-diagnostic ontology: coping actions, emotion/trigger relationships, CBT thinking-pattern taxonomy, resource categories, and safety keyword references. It may later hold sanitized aggregate patterns such as trigger frequency or coping effectiveness, but only through typed outbox events.

### What must be removed from Neo4j immediately?

Disable Mem0 graph-store writes. Remove or quarantine user-specific `RiskProfile`, `Assessment`, `MemoryNode`, and clinical assessment history from the MVP graph. Prevent all raw messages, PII, crisis logs, raw questionnaire answers, clinical scores, direct diagnosis labels, and user-has-disorder edges.

### What must be kept in PostgreSQL only?

Raw messages, PII-bearing text, mood/check-in notes, nutrition/self-report, crisis/SOS events, safety/risk logs, clinical/screening profile, analyst raw signals, dashboard insight instances, rewards/hearts, wallets, persona unlocks, TTS jobs/status, and operational queue state.

### What tables should be merged or converted to views?

Create a safe profile view or remove direct `user_profiles` RLS. Consider a unified heart ledger only if reward audit complexity grows. Keep `conversation_memories` and `memory_cards` separate but document their boundary. Convert dashboard-safe output to a canonical view/API contract and avoid direct heuristic insight cards.

### What is the minimum MVP-safe database architecture?

PostgreSQL/Supabase plus pgvector is sufficient for MVP: users, conversations, messages, check-ins, memory cards, semantic memory, safety audit, dashboard insights, rewards, persona unlocks, knowledge progress, and TTS jobs. Neo4j can be optional and static. Redis remains cache/session/runtime only.

### What can wait until post-MVP?

User-derived Neo4j pattern graph, diagnostic/differential ontology usage, `Assessment` nodes, `RiskProfile` nodes, agent orchestration graph, medical-condition differential graph, and graph-based personalization can wait until governance, tests, and product need are proven.

### Top 5 fixes first

| Rank | Fix | Reason |
|---|---|---|
| 1 | Disable Mem0 direct Neo4j graph store and prevent raw message graph writes. | Highest privacy/source-of-truth risk. |
| 2 | Reconcile and replace the active outbox worker so graph events are either applied correctly or fail visibly. | Current behavior can silently lose sync events. |
| 3 | Remove clinical/risk fields from user-facing dashboard APIs and direct user-readable profile JSON. | Prevents clinical boundary violation. |
| 4 | Make `insight_hypotheses`/`dashboard_safe_insights` the only evidence-backed insight source. | Restores dashboard auditability and user trust. |
| 5 | Choose one canonical schema path and align SQL, Alembic, models, and frontend contracts. | Reduces production migration and drift risk. |

### Evaluation framework

| Criterion | Status | Evidence | Main Risk | Required Fix |
|---|---|---|---|---|
| Source of Truth | Partial | PostgreSQL owns core tables, but Neo4j runtime labels and Mem0 graph store exist. | Duplicated user/session/memory state. | PostgreSQL-only SoT; sanitized outbox-derived graph only. |
| Supabase/Neo4j Boundary | Fail | Mem0 graph store at `backend/app/services/mem0_service.py:77`; active worker does not graph-sync. | Privacy violation and data loss. | Disable bypass and fix canonical graph sync. |
| Safety & Privacy | Fail | Dashboard exposes `crisis_level`; Mem0 receives raw `m.content`; risk writer evidence unclear. | Sensitive data exposure and incomplete safety audit. | API DTO cleanup, Mem0 disablement, safety write tests. |
| Clinical Non-Diagnosis Boundary | Partial | Screening stores PHQ/GAD scores; Neo4j has disorder/criteria/differential graph. | User-facing diagnostic implication. | Internal-only labels, no dashboard clinical scores, no disorder assignment edges. |
| Schema Consistency | Fail | `core_sql.sql`, Alembic, models, docs, and workers disagree on tables/columns. | Deployment drift. | Canonical migration path and parity tests. |
| RLS/Security | Partial | Internal tables lack direct user policies, but `user_profiles` owner select and dashboard API leak fields. | Backend/API bypasses intended policy. | Safe views and DTO contract tests. |
| Scalability | Partial | Mixed-purpose `sync_outbox`, JSONB payloads, dashboard Python-side filtering. | Queue and dashboard latency growth. | Split queues or typed event families; add indexes; push filtering to SQL. |
| Latency | Partial | Neo4j not required for chat write path, but outbox/voice and dashboard aggregation can degrade. | Hot-path or background job contention. | Keep Neo4j async; separate TTS queue; optimize dashboard queries. |
| Dashboard Evidence Quality | Fail | Heuristic insight cards can bypass persisted `insight_hypotheses`. | Unsupported user-facing claims. | Persist evidence-backed insights or label hints as non-insights. |
| Product Simplicity / MVP Fit | Partial | PostgreSQL/pgvector can serve MVP; Neo4j clinical/runtime graph is overextended. | Maintenance and safety overhead. | Reduce Neo4j to static taxonomy for MVP. |

### Schema drift audit

| Drift Type | Example | Evidence | Severity | Required Fix |
|---|---|---|---|---|
| Table exists in docs but not implementation | `tts_jobs`, `heart_ledger`, `reward_inventory` | `docs/PRD.md:844`, `docs/PRD.md:845`, `docs/PRD.md:1031`; implementation uses `sync_outbox` voice payloads and heart event tables. | Medium | Update docs or add compatibility tables/views. |
| Table exists in models but not `core_sql.sql` | `memory_cards`, `knowledge_packs`, `heart_wallets`, `persona_unlock_states` | Models at `backend/app/services/db/models.py:824`, `:876`, `:638`, `:805`; Alembic creates in `0016`; absent from `core_sql.sql`. | Medium | Make Alembic canonical or regenerate core SQL. |
| SQL field type differs from model/worker | `sync_outbox` has `retry_count`; legacy worker expects `attempts`. | `backend/app/data/core_sql.sql:698`; `backend/app/core/outbox_worker.py:381`. | Critical | Reconcile schema and worker. |
| Enum/check constraint differs from API behavior | `InsightHypothesis.severity_band` allows `low/moderate/elevated`, service maps also from `medium/watch/high`. | Model check at `backend/app/services/db/models.py:531`; mapping at `backend/app/dashboard/service.py:103`. | Medium | Normalize severity enum contract. |
| Index exists in indexes.sql but missing in migration | Some core indexes are external optional SQL, while migrations do not clearly apply all of them. | `backend/app/data/indexes.sql:73`, `:99`, `:160`, `:192`. | Medium | Move production indexes into migrations or document post-migration index run. |
| Neo4j label duplicates Postgres table | `User`, `Session`, `Assessment`, `MemoryNode`, `RiskProfile` | Neo4j constraints at `backend/app/data/neo4j_bootstrap_v3.cypher:31` to `:40`; PostgreSQL models in `backend/app/services/db/models.py`. | High | Remove or constrain to sanitized derived aggregates. |
| Frontend expects field not returned by backend | Unknown. Frontend dashboard contracts align broadly with backend reflect summary types. | `frontend/src/services/dashboardService.ts:83`; `backend/app/dashboard/types.py:90`. | Unknown | Add generated OpenAPI/TypeScript contract check. |
| Dashboard reads mock/placeholder instead of real table/view | Heuristic cards and nutrition tips are computed/static rather than from evidence table. | `backend/app/dashboard/service.py:246`; `backend/app/api/v1/routers/dashboard.py:196`. | Medium | Label as static hints or persist evidence-backed rows. |
| Mood score scale drift | SQL constrains `mood_score` 1 to 5, dashboard derives scores from mood enum, frontend renders 1 to 5 and percentage. | `backend/app/data/core_sql.sql:236`; `backend/app/api/v1/routers/dashboard.py:45`; `frontend/src/components/wellness/MoodCalendar.tsx:44`. | Low | Document one canonical 1-to-5 scale and enum mapping. |
| `memory_cards` versus `conversation_memories` | Both store memory content and status-like metadata. | `backend/app/services/db/models.py:305`; `backend/app/services/db/models.py:824`. | Medium | Define semantic retrieval versus user-reviewed card boundary. |
| Clinical profile fields | Raw answers stored in coverage JSON; profile also has clinical snapshot JSON schema. | `backend/app/api/v1/routers/screening.py:55`; `backend/app/data/user_profile_schema.json:92`. | High | Dedicated backend-only screening answer design or coverage-only storage. |
| `dashboard_safe_insights` columns | SQL view columns match safe subset; backend bypasses view and queries model. | `backend/app/data/core_sql.sql:666`; `backend/app/dashboard/service.py:158`. | Medium | Use view or identical DTO test. |
| `sync_outbox` payload shape | Graph, notification, and voice events share one untyped JSONB. | `backend/app/services/session_summary.py:33`; `backend/app/services/outbox_worker.py:14`; `backend/app/services/proactive_voice.py:203`. | High | Typed event schemas and separate dispatchers. |
| Neo4j User/Session/RiskProfile/MemoryNode | Runtime labels exist in bootstrap contracts. | `backend/app/data/neo4j_bootstrap_v3.cypher:31` to `:35`. | High | Remove/quarantine for MVP or make strictly sanitized. |

### MVP overengineering classification

| Object | Classification | Rationale |
|---|---|---|
| `users`, `conversations`, `messages`, `mood_checkins` | MVP Required | Visible product and safety features depend on them. |
| `conversation_memories` with pgvector | MVP Useful | Supports personalized context if masked and governed. |
| `memory_cards` | MVP Useful | Gives user control over memory. |
| `user_profiles` | MVP Useful as cache, but risky | Must be backend-safe cache, not hidden SoT or direct frontend table. |
| `clinical_profiles` | MVP Useful with strict boundary | Screening exists, but must avoid diagnostic presentation. |
| `risk_inference_log`, `session_risk_snapshots` | MVP Required if safety claims remain | Safety audit requires durable records; implementation writer must be confirmed. |
| `analyst_signals` | MVP Useful | Needed for internal reasoning audit; currently missing writer evidence. |
| `insight_hypotheses`, `dashboard_safe_insights` | MVP Required for safe dashboard insights | Should replace heuristic-only insight flow. |
| Rewards/hearts/persona tables | MVP Useful | Product retention features depend on them; PostgreSQL-only. |
| Knowledge unlock tables | MVP Useful/Post-MVP | Keep if visible feature is shipped; otherwise defer. |
| `sync_outbox` | MVP Required | Needed for idempotency and async sync, but should not be generic blob carrier for everything. |
| `tts_jobs` as dedicated table | MVP Useful | Better than voice payloads in generic outbox. |
| Neo4j static coping/emotion taxonomy | MVP Useful | Non-diagnostic reference can help analyst/resource matching. |
| Neo4j disorder/criteria/differential graph | Post-MVP | High clinical governance requirement. |
| Neo4j `User`, `Session`, `RiskProfile`, `MemoryNode`, `Assessment` | Remove or defer | Duplicates PostgreSQL and increases sensitive surface. |
| Neo4j `Agent`, `AgentCapability` | Defer post-MVP | Code-level architecture already defines agent boundaries. |
