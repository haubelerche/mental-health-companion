# Serene Database Refactor Phase Plan

This plan decomposes `DATABASE_DESIGN_AUDIT_REPORT.md` into implementation phases. Phases must be executed in order because later code and migration work depends on the Phase 0 ownership contract.

## Deployment Handoff (2026-05-08)

Status: Ready with one required production migration

- Closed findings from the audit report:
  - Raw screening answers in coverage JSON
  - Missing risk safety writers
  - Missing analyst pipeline writers
  - Dead heuristic dashboard card code
- Breaking change:
  - `build_safe_insight_cards` no longer accepts `profile_data`; all known callers were updated in the same PR.
- Required before production deploy:
  - Run Alembic migration `0021_screening_answers_table` on production database.
- Remaining audit findings:
  - None.

## Phase 0 - Documentation Freeze

Status: Done

Goal: establish one canonical database boundary so future implementation work does not continue schema drift.

Deliverables:

| Deliverable | Status | Notes |
|---|---|---|
| `DATABASE_ARCHITECTURE.md` | Done | Canonical source-of-truth matrix, table ownership, frontend/backend boundaries, and Neo4j allowed/forbidden data. |
| Audit report cross-reference | Done | `DATABASE_DESIGN_AUDIT_REPORT.md` is the evidence base. |
| Migration authority decision | Done | Alembic is the production migration authority; `backend/app/data/core_sql.sql` is bootstrap/reference only until regenerated from migrations. |
| Neo4j MVP boundary | Done | Static/internal taxonomy only, plus optional sanitized aggregate graph after outbox governance is fixed. |

Exit criteria:

- `DATABASE_ARCHITECTURE.md` exists.
- Source-of-truth, cache/rollup, derived, backend-only, frontend-safe, and operational queue ownership are explicit.
- Neo4j allowed/forbidden payloads are explicit.
- Phase 1 work can reference this document without re-deciding database ownership.

## Phase 1 - Schema Drift Fix

Status: Done

Goal: align the codebase around one schema contract.

Build order:

1. Reconcile `sync_outbox` schema across SQLAlchemy model, Alembic, active worker, and legacy graph worker.
2. Move runtime DDL from FastAPI startup into Alembic.
3. Add or update Alembic migrations for missing app-scoped feature tables and indexes.
4. Decide whether `tts_jobs` becomes a dedicated table or remains a typed `sync_outbox` event family for MVP.
5. Normalize mood score scale and dashboard severity enum contracts.

Exit criteria:

- No worker references columns absent from the model/migrations.
- `core_sql.sql` is documented as non-production bootstrap or regenerated.
- Schema parity checks cover table/column presence for critical tables.

Implementation slices:

| Slice | Change | Primary files | Risk | Acceptance check |
|---|---|---|---|---|
| 1.1 | Remove runtime schema repair from app startup and move the `sync_outbox.outbox_id` identity repair into Alembic if still required. | `backend/app/main.py`, `backend/alembic/versions/0018_sync_outbox_identity_contract.py` | Medium | Done: app startup performs no DDL; migration owns schema changes. |
| 1.2 | Reconcile active outbox model and workers around one column contract: `retry_count`, `error_message`, `processing_started_at`, and no `attempts`. | `backend/app/services/db/models.py`, `backend/app/services/outbox_worker.py`, `backend/app/core/outbox_worker.py`, Alembic migration | High | Done: active notification worker and legacy graph workers use `retry_count`; unsupported events fail visibly instead of being marked `done`. |
| 1.3 | Decide and encode the TTS job storage contract for MVP: either dedicated `tts_jobs` or typed `sync_outbox` event family with no audio blob in JSONB. | `backend/app/services/proactive_voice.py`, model/migration files | High | Done: MVP keeps typed `sync_outbox` voice jobs; payload stores lifecycle metadata and audio file reference, not base64 audio. |
| 1.4 | Align documented and implemented reward table names. | `docs/PRD.md`, `DATABASE_ARCHITECTURE.md`, reward models/services | Low | Docs no longer mention `heart_ledger`/`reward_inventory` as implemented tables unless views are added. |
| 1.5 | Normalize dashboard severity and mood scale contracts. | `backend/app/dashboard/types.py`, `backend/app/dashboard/service.py`, frontend dashboard service types | Medium | One enum contract for safe insight severity; mood remains 1-to-5 with documented percentage mapping. |
| 1.6 | Add schema parity verification for critical tables and columns. | `backend/scripts/verify_db_schema.py` or new static test | Medium | Done: verification checks `sync_outbox`, safety tables, insight tables, rewards, memory cards, and knowledge tables. |

## Phase 2 - PostgreSQL Cleanup

Status: Done

Goal: make PostgreSQL boundaries enforce product safety and evidence quality.

Build order:

1. Remove clinical/risk fields from user-facing dashboard overview payloads.
2. Replace direct `user_profiles` frontend exposure with backend DTOs or a safe view.
3. Enforce `conversation_memories` versus `memory_cards` ownership.
4. Ensure dashboard insight cards are backed by `insight_hypotheses` or clearly labeled non-insight hints.
5. Add RLS/mutation tests for rewards, persona unlocks, memory cards, and backend-only safety tables.

Exit criteria:

- Done: frontend-safe dashboard overview no longer queries or returns `phq9_score`, `gad7_score`, or `crisis_level`.
- Done: deprecated reflect summary no longer includes raw clinical snapshot fields in its response payload.
- Done: dashboard safe insight cards now require persisted `insight_hypotheses.evidence_count > 0`; heuristic profile cards are not represented as user-facing insights.

## Phase 3 - Neo4j Boundary Fix

Status: Done

Goal: ensure Neo4j cannot become a second source of truth or sensitive-data sink.

Build order:

1. Disable Mem0 Neo4j graph store for user-derived memory.
2. Add graph payload validators for allowed event types.
3. Replace the active outbox dispatcher so graph events are applied or fail visibly.
4. Quarantine `RiskProfile`, `Assessment`, `MemoryNode`, and user-specific session graph writes for MVP.
5. Add tests proving no raw message, PII, crisis log, clinical score, raw questionnaire answer, or direct disorder assignment reaches Neo4j.

Exit criteria:

- Done: Mem0 no longer configures a Neo4j `graph_store` for user-derived memory.
- Done: session close no longer enqueues user-specific `session.ended`, `trigger.observed`, or `coping.attempted` graph sync events for MVP.
- Done: Mem0 session memory payload is PII-masked before background add.
- Done: unsupported notification outbox events are rejected and retried/failed instead of marked `done`.

## Phase 4 - Agent Read/Write Path Fix

Status: Done

Goal: align agent workflows with the database ownership contract.

Build order:

1. Conversation Agent reads context from PostgreSQL/pgvector only in the normal path.
2. Analyst Agent writes `analyst_signals` and safe `insight_hypotheses` through explicit services.
3. Safety Agent writes safety-critical records synchronously to PostgreSQL backend-only tables.
4. Dashboard reads only safe derived APIs/views.
5. Persona/reward/wallet mutations remain backend-owned.

Exit criteria:

- Done: normal session close persists PostgreSQL profile/memory state and does not enqueue Neo4j graph writes.
- Done: dashboard reads safe derived `insight_hypotheses` cards only when persisted evidence exists.
- Done: safety-critical chat code remains PostgreSQL-owned; Neo4j is not imported on the normal chat router or conversation service path.
- Done: reward and persona mutations remain backend-owned through service-layer routes and SQLAlchemy models.

## Phase 5 - Validation and Regression Tests

Status: Done

Goal: prevent regression after the database boundary is repaired.

Required tests:

| Test | Required behavior |
|---|---|
| No raw message write to Neo4j | Graph payload validators reject transcript content. |
| No PII write to Neo4j | Graph payload validators reject PII-bearing strings. |
| No crisis/risk sync to Neo4j | Crisis and risk tables never produce graph payloads. |
| No direct disorder assignment edge | User-to-disorder and user-to-diagnostic-criterion edges are rejected. |
| Dashboard insight evidence | User-facing insight cards require evidence metadata. |
| Backend-only security | Frontend cannot read backend-only clinical/risk/analyst tables. |
| Reward/persona ownership | Frontend cannot directly mutate wallet, rewards, or persona unlock state. |
| Degradation | Neo4j failure leaves chat functional and outbox retryable. |
| Outbox correctness | Unsupported events fail visibly and are not marked `done`. |

Exit criteria:

- Done: `backend/tests/test_database_boundary_regression.py` validates the repaired database boundary without database access.
- Done: local targeted test run passes (`backend/tests/test_database_boundary_regression.py`, `backend/tests/test_dashboard_reflect.py`).
- Done: real PostgreSQL integration suite passes after migration alignment (`backend/tests/test_db_integration.py`).
- Done: `DATABASE_ARCHITECTURE.md` remains the canonical release reference for database boundary checks.

Validation evidence (latest run):

- `alembic upgrade head` on `backend/alembic.ini` completed through:
  - `0017_admin_audit_align`
  - `0018_outbox_identity`
  - `0019_sync_outbox_worker_columns`
- `python -m pytest backend/tests/test_database_boundary_regression.py backend/tests/test_dashboard_reflect.py backend/tests/test_db_integration.py -q`
  - Result: `41 passed`
- Extended regression suites (safety/reward/persona/memory/voice/chat/contracts):
  - `python -m pytest backend/tests/test_dashboard_reflect.py backend/tests/test_safety_and_sos.py backend/tests/test_safety_regression.py backend/tests/test_reward_store.py backend/tests/test_persona_unlock.py backend/tests/test_memory_cards.py backend/tests/test_proactive_voice.py backend/tests/test_tts_dedup.py -q`
  - Result: `115 passed`
  - `python -m pytest backend/tests/test_chat_router_integration.py backend/tests/test_checkin_router_integration.py backend/tests/test_contract_shapes.py backend/tests/test_api_route_contract.py backend/tests/test_db_integration.py -q`
  - Result: `38 passed` (non-blocking warnings only)
- Full backend test suite:
  - `python -m pytest backend/tests -q`
  - Result: `321 passed, 18 skipped, 1 warning`
  - Skip reason: environment-gated/infra-protective suites (including pool soak handling) skip when required live dependencies or Supabase session-pool capacity are unavailable.
  - Added boundary hardening test: `backend/tests/test_graph_outbox_contract.py` (`3 passed`) verifies outbox payload contract rejects sensitive/non-contract keys.
