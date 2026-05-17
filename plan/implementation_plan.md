# Serene Internal Analyst Pipeline Implementation

This plan outlines the integration of the Serene Internal Analyst Pipeline. It bridges the gap between the existing inference capabilities and structured insight storage, creating a closed-loop insight architecture.

## User Review Required

> [!IMPORTANT]
> The addition of the `AnalystSignal` table requires a database migration. I will modify `models.py` but we must ensure alembic migrations are run if you are managing the schema that way, or let SQLAlchemy create the table automatically on next boot (if `metadata.create_all` is enabled). Let me know if you want me to write an Alembic script or if SQLAlchemy will handle it.

## Open Questions

> [!WARNING]
> In `backend/app/main.py`, the threaded `_outbox_loop` imports `run_outbox_worker_loop` from `app.services.outbox_worker`. There is also a full `app.core.outbox_worker`. Should I point `main.py` to use the async `app.core.outbox_worker` logic directly to ensure Neo4j sync occurs, or just update `app.services.outbox_worker` to be functionally complete? I will assume we want to use `app.core.outbox_worker.run_worker`.

## Proposed Changes

---

### Database Models
Introduce a new structured table for Analyst Agent outputs.

#### [MODIFY] [models.py](file:///c:/Users/Admin/Desktop/A20-App-039/backend/app/services/db/models.py)
Add the `AnalystSignal` model to persistently store the `AnalystBundle` emitted during each chat turn.

---

### LangGraph Chat Core
Pass Analyst outputs out to the pipeline and query Neo4j graph.

#### [MODIFY] [langgraph_chat.py](file:///c:/Users/Admin/Desktop/A20-App-039/backend/app/services/langgraph_chat.py)
- Modify `ChatGraphState` to accept `user_id` so we can query Neo4j.
- In `analyst_node`, add a Cypher query (using `get_neo4j_driver`) to fetch top triggers/emotions directly from the Neo4j knowledge graph and append them to the analyst's context.
- Update `run_non_sos_turn` to return the `analyst_bundle` in its output dictionary.

---

### Chat Router API
Save the analyst bundle into the new database schema.

#### [MODIFY] [chat.py](file:///c:/Users/Admin/Desktop/A20-App-039/backend/app/api/v1/routers/chat.py)
- Pass `current_user.user_id` when invoking the graph.
- Extract the `analyst_bundle` from the graph results.
- Insert a new `AnalystSignal` record into the database right after the turn is processed, making it permanently queryable.

---

### Dashboard API
Read from the structured table instead of legacy JSON blobs.

#### [MODIFY] [dashboard.py](file:///c:/Users/Admin/Desktop/A20-App-039/backend/app/api/v1/routers/dashboard.py)
- Rewrite `_build_dashboard_insights` to query the `AnalystSignal` table ordered by `created_at DESC` instead of parsing the generic `UserProfile` blob.

---

### Outbox Worker Initialization
Ensure the production-grade async graph synchronizer is actually running.

#### [MODIFY] [main.py](file:///c:/Users/Admin/Desktop/A20-App-039/backend/app/main.py)
- Refactor the threaded `_outbox_loop` to launch the async `run_worker` from `app.core.outbox_worker`, providing the required Neo4j credentials from settings.

---

### Frontend Dashboard Module
Expose these insights to the user interface.

#### [MODIFY] [dashboardService.ts](file:///c:/Users/Admin/Desktop/A20-App-039/frontend/src/services/dashboardService.ts)
- Add the `analyst_insights` field to the Dashboard payload type and update API response parsing.

#### [MODIFY] [Home.tsx](file:///c:/Users/Admin/Desktop/A20-App-039/frontend/src/components/pages/Home.tsx)
- Add a new "Insight Card" or panel on the dashboard view that consumes and renders the `analyst_insights` data (emotional theme, clinical note) gracefully.

## Verification Plan

### Automated Tests
- No new unit tests directly required, but existing tests for `analyst_node` and `dashboard` will be evaluated to ensure they still pass.

### Manual Verification
1. I will send a chat message using the browser.
2. I will verify that `AnalystSignal` records are created in PostgreSQL.
3. I will open the Dashboard UI and check if the newly persisted "Emotional Theme" and insights show up dynamically.
4. I will verify the background logs to ensure `app.core.outbox_worker` is syncing to Neo4j.
