# Serene Database Architecture

This document is the canonical database ownership contract for Serene. It is derived from `DATABASE_DESIGN_AUDIT_REPORT.md` and supersedes older database notes when ownership or source-of-truth boundaries conflict.

## 1. System Roles

| Store | Role | Hard boundary |
|---|---|---|
| Supabase/PostgreSQL | Primary source of truth for durable user, product, safety, memory, dashboard, reward, persona, TTS, and operational state. | Any user-specific durable state must be persisted here first. |
| pgvector | Semantic retrieval over approved, masked, or summarized memory content. | It is part of PostgreSQL ownership, not a separate source of truth. |
| Redis | Runtime cache, rate limit, guest/session optimization, and short-lived idempotency. | Redis must not be durable product state. |
| Neo4j | Static/internal ontology and optional sanitized derived aggregate graph. | Neo4j must not store raw messages, PII, crisis logs, raw questionnaire answers, clinical scores, direct diagnosis labels, or operational state. |
| `sync_outbox` | PostgreSQL-owned async dispatch queue for derived side effects. | Unsupported events must fail visibly; they must not be marked `done` without dispatch. |

## 2. Canonical Source-of-Truth Matrix

| Data domain | Source of truth | Classification | Frontend access |
|---|---|---|---|
| User account, consent, policy acknowledgement | `users` | Source of truth | Backend API or safe user DTO |
| Auth tokens and OAuth identities | `refresh_tokens`, `user_identities`, `email_verification_tokens`, `password_reset_tokens` | Source of truth | Backend-only |
| Chat sessions | `conversations` | Source of truth | Backend API |
| Raw or masked chat transcript | `messages` | Source of truth | Backend API only; no Neo4j |
| Mood check-ins | `mood_checkins` | Source of truth | Backend API |
| Nutrition/self-report | `nutrition_meal_checkins` | Source of truth | Backend API |
| Long-term semantic memory | `mem0_memories` | Source of truth for retrieval memory and the Chat “Ký ức” UI | Backend API, scoped to the authenticated user |
| Structured profile rollup | `user_profiles` | Derived rollup for personalization and summaries, not canonical retrieval memory | Backend-only unless projected through a safe DTO/view |
| Session summary archive | `session_summaries_archive` | Durable summary history | Backend-only |
| Profile rollup | `user_profiles` | Cache/rollup, not source of truth | Backend-only unless projected through a safe DTO/view |
| Profile history | `user_profile_snapshots` | Audit/history | Backend-only |
| Clinical/screening profile | `clinical_profiles` | Backend-only safety/clinical-adjacent state | Backend-only |
| Risk inference log | `risk_inference_log` | Backend-only safety audit | Backend-only |
| Session risk snapshots | `session_risk_snapshots` | Backend-only safety audit | Backend-only |
| Crisis/SOS logs | `crisis_logs` | Backend-only safety audit | Admin/safety-only |
| Raw analyst signals | `analyst_signals` | Backend-only derived analyst output | Backend-only |
| User-facing insight instances | `insight_hypotheses` | Derived dashboard source | Expose only safe fields |
| Safe dashboard insight view | `dashboard_safe_insights` | Frontend-safe view | Frontend-safe |
| Rewards/hearts wallet | `heart_wallets`, `heart_reward_events`, `heart_spend_events` | Product source of truth | Backend API; backend-owned mutations |
| Store and inventory | `reward_store_items`, `user_inventory_items` | Product source of truth | Backend API |
| Persona unlocks | `persona_unlock_states` | Product source of truth | Backend API; backend-owned mutations |
| Knowledge unlocks | `knowledge_packs`, `knowledge_cards`, `user_knowledge_progress` | Product source of truth | Backend API |
| TTS jobs and voice status | Dedicated `tts_jobs` table or typed `sync_outbox` event family | Operational state | Backend API |
| Graph sync queue | `sync_outbox` | Operational queue | Backend-only |
| Mental-health ontology | Neo4j or static taxonomy | Static/internal reference | Backend-only |
| Coping strategy taxonomy | Neo4j or static taxonomy | Static/internal reference | Backend-only |
| Sanitized user-derived graph aggregates | PostgreSQL source plus optional Neo4j derived projection | Derived aggregate | Backend-only |

## 3. Table Ownership Rules

### Source-of-truth tables

These tables own durable user or product state and must not be duplicated as independent truth in Neo4j or Redis:

- `users`
- `conversations`
- `messages`
- `mood_checkins`
- `nutrition_meal_checkins`
- `mem0_memories`
- `clinical_profiles`
- `risk_inference_log`
- `session_risk_snapshots`
- `crisis_logs`
- `heart_wallets`
- `heart_reward_events`
- `heart_spend_events`
- `reward_store_items`
- `user_inventory_items`
- `persona_unlock_states`
- `knowledge_packs`
- `knowledge_cards`
- `user_knowledge_progress`

### Cache and rollup tables

These tables are derived from source-of-truth data and must be treated as rebuildable or auditable projections:

- `user_profiles`
- `user_profile_snapshots`
- `session_summaries_archive`

`user_profiles.profile` must not be used as the canonical source for dashboard insight, clinical state, reward state, persona unlocks, or safety state.

### Derived and analytics tables

These tables store internal or frontend-safe derived outputs:

- `analyst_signals`
- `insight_hypotheses`
- `dashboard_safe_insights`

`analyst_signals` is internal-only. `dashboard_safe_insights` is the safe frontend-facing projection.

### Operational queues

`sync_outbox` owns async side-effect state. It may enqueue graph sync, notification dispatch, or TTS work only if event families have explicit payload contracts and dispatch behavior. Long-term audio bytes and large blobs should not live in `sync_outbox.payload`.

## 4. Frontend Access Boundary

Frontend may consume data through backend APIs or safe views for:

- user profile display fields explicitly returned by backend DTOs;
- conversations and messages for the authenticated user;
- mood/check-in history;
- resources, bookmarks, and play events;
- canonical user memories from `mem0_memories`, through authenticated backend APIs only;
- rewards, inventory, and persona progress through backend APIs;
- `dashboard_safe_insights` or equivalent safe dashboard API responses;
- TTS job status through backend APIs.

Frontend must not directly consume or mutate:

- `clinical_profiles`;
- `risk_inference_log`;
- `session_risk_snapshots`;
- `crisis_logs`;
- `analyst_signals`;
- `sync_outbox`;
- `admin_audit_log`;
- `user_profile_snapshots`;
- raw `user_profiles.profile` if it contains clinical, safety, or analyst-derived internals;
- wallet, reward, persona unlock, or safety state outside backend-owned mutation endpoints.

## 5. Neo4j Boundary

### Allowed in Neo4j

Neo4j may contain:

- static/internal coping strategy taxonomy;
- static/internal emotion and trigger taxonomy;
- static/internal resource relationship taxonomy;
- static/internal CBT thinking-pattern taxonomy;
- static/internal safety keyword ontology;
- optional sanitized aggregate edges produced from PostgreSQL events, such as trigger counts or coping-action effectiveness.

### Forbidden in Neo4j

Neo4j must not contain:

- raw user messages;
- PII or precise identifying information;
- raw mood/check-in notes;
- raw questionnaire answers;
- crisis logs or crisis transcript summaries;
- `phq9_score`, `gad7_score`, raw screening results, or clinical profile values;
- direct diagnosis labels;
- `User -> Disorder`, `User -> DiagnosticCriterion`, or equivalent assignment edges;
- wallet, reward, persona unlock, TTS job, or other operational state.

### MVP graph posture

For MVP, Neo4j should be treated as static/internal taxonomy only. User-derived graph projections are post-MVP unless the outbox dispatcher, payload validators, and regression tests prove that only sanitized aggregate data can enter the graph.

## 6. Migration Authority

Alembic is the production migration authority.

`backend/app/data/core_sql.sql` is a bootstrap/reference artifact until it is regenerated from the canonical migrations. It must not be treated as the production migration path because it can drift from Alembic and contains bootstrap-style DDL that is unsafe to run blindly in production.

Production schema changes must satisfy:

- explicit `app.` schema ownership;
- no runtime DDL from FastAPI startup;
- no destructive downgrade assumptions for production;
- parity between Alembic, SQLAlchemy models, Pydantic payloads, and frontend contracts where applicable;
- index and RLS policies included in migrations or in a documented post-migration step.

## 7. Required Flow Contracts

### Conversation flow

```text
User message
-> PostgreSQL messages
-> Safety Agent reads minimal required context
-> Conversation Agent reads PostgreSQL/pgvector context
-> assistant message persisted to messages
-> async side effects enqueued
-> Neo4j write, if any, runs after response through validated outbox
```

Normal chat must not depend on Neo4j write success.

### Analyst flow

```text
messages/check-ins/self-report
-> Internal Analyst structured signal
-> analyst_signals
-> insight aggregation
-> insight_hypotheses
-> dashboard_safe_insights
-> frontend
```

Analyst output must remain internal until transformed into a safe insight.

### Safety flow

```text
incoming message
-> Safety Agent
-> synchronous PostgreSQL safety writes when risk is elevated
-> crisis_logs when needed
-> no raw crisis sync to Neo4j
```

Safety-critical persistence failures are release blockers and operational incidents.

### TTS flow

```text
chat response
-> optional TTS job enqueue
-> durable job status in PostgreSQL or dedicated queue
-> audio storage reference returned through backend API
```

TTS failure must not block the text response. Large audio data should not be stored in generic JSONB queue payloads.

## 8. Phase Execution Order

Implementation must follow `DATABASE_REFACTOR_PHASE_PLAN.md`:

1. Documentation Freeze.
2. Schema Drift Fix.
3. PostgreSQL Cleanup.
4. Neo4j Boundary Fix.
5. Agent Read/Write Path Fix.
6. Validation and Regression Tests.

Current execution status:

- The phase plan has been executed end-to-end and validated against real PostgreSQL migrations plus full backend regression tests.
- Latest verification evidence is tracked in `DATABASE_REFACTOR_PHASE_PLAN.md` under Phase 5 validation evidence.
