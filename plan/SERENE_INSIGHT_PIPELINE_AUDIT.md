# SERENE INSIGHT PIPELINE — FORMAL PRODUCTION AUDIT

**Report Version:** 1.0  
**Audit Date:** 2026-05-05  
**Auditor Role:** Senior AI Architect / Mental Health AI Systems Auditor  
**Codebase:** `A20-App-039` (Serene — AI Companion for Mental Health)  
**Scope:** Internal Analyst Agent · Insight Pipeline · Neo4j Graph Integration · Dashboard/Reflect UI · Safety

---

## EXECUTIVE SUMMARY

After a full multi-layer inspection of source code, data flow paths, service wiring, and runtime startup, the Serene Insight Pipeline is classified as:

> **`PARTIAL_BACKEND_REAL — FRONTEND_PARTIALLY_CONNECTED`**

The system is **not a pure mock or stub.** Core AI inference, structured data extraction, and PostgreSQL persistence are all genuinely operational. However, the pipeline contains architectural gaps that prevent it from being classified as a fully wired production system:

1. The Analyst Agent runs live per-conversation but **does not persist its output** anywhere retrievable by the dashboard.
2. The Dashboard `analyst_insights` field reads from a **JSONB blob** in `UserProfile` — not from a dedicated insight table.
3. The Neo4j graph is written via an **outbox worker** (async) but is **never read back** during insight generation or dashboard rendering.
4. The Reflect page (`/reflect`) is **correctly wired** to real backend endpoints and is the most production-ready surface.

---

## COMPONENT AUDIT

### 1. Analyst Agent (`analyst_node` in `langgraph_chat.py`)

| Attribute | Finding |
|---|---|
| **Existence** | ✅ Real. LangGraph node at lines 866–985 |
| **Trigger** | ✅ Activated when `distress_score ≥ 0.55` OR explicit analysis keywords detected |
| **LLM Call** | ✅ Calls OpenAI with structured JSON schema: `clinical_note`, `emotional_theme`, `suggested_focus`, `risk_indicators` |
| **Output type** | `AnalystBundle` dataclass |
| **Persistence** | ❌ **NOT PERSISTED.** Bundle lives only in `ChatGraphState` for the duration of one turn; passed to `friend_node` as a system prompt context block and then discarded |
| **Dashboard access** | ❌ Dashboard has no mechanism to read `AnalystBundle` data |
| **Safety guardrails** | ✅ Instructed never to diagnose, no PII, no clinical labels as final verdict |

**Verdict:** The Analyst Agent is a **real LLM-powered node** that runs correctly during high-distress conversations. However, it functions purely as an **in-memory routing enhancer** for the current Friend reply. It is architecturally invisible to the insight pipeline and dashboard.

---

### 2. Session Summarization (`session_summary.py` + `longterm_memory.py`)

| Attribute | Finding |
|---|---|
| **Session summary trigger** | ✅ `close_session_summary()` called at `/chat/end`; `persist_turn_memory()` called after every turn |
| **Extraction method** | ✅ `memory_enrichment.py` — LLM + regex fallback extracts triggers, emotions, coping attempts |
| **Persistence target** | ⚠️ Written to `UserProfile.profile` (PostgreSQL JSONB) — not a relational or typed schema |
| **Outbox event emitted** | ✅ `session.ended`, `trigger.observed`, `memory.created`, `coping.attempted` events queued in `sync_outbox` |
| **Structured schema** | ❌ No `InsightHypothesis` or `AnalystSignal` table exists in `models.py` |
| **Memory type** | JSONB blob with keys: `session_summaries[]`, `trigger_tags{}`, `coping_history[]`, `traits{}`, `goals[]`, `stats{}` |

**Verdict:** Turn-level and session-level memory extraction is **genuinely operational**. Data is real and persistent. The structural weakness is that all insight data is collapsed into a single untyped JSONB blob, making longitudinal queries, advanced pattern matching, and scoped API responses difficult.

---

### 3. Neo4j Graph Integration

| Attribute | Finding |
|---|---|
| **Schema exists** | ✅ `neo4j_bootstrap_v3.cypher` defines a rich knowledge graph: `Symptom`, `Disorder`, `Trigger`, `Emotion`, `CopingAction`, `Resource`, `Instrument` (PHQ-9, GAD-7), `CognitiveDistortion` |
| **Outbox worker** | ✅ `app/core/outbox_worker.py` — fully implemented async worker with `Neo4jApplier` class, MERGE handlers for 5 event types, retry/backoff, dead-letter, Prometheus metrics |
| **Runtime startup** | ⚠️ `main.py` starts `app.services.outbox_worker.run_outbox_worker_loop` — different module from `app.core.outbox_worker`; Neo4j wiring unconfirmed |
| **User-anchored writes** | ✅ `(User)-[:EXPERIENCED]->(Trigger)`, `(User)-[:FELT]->(Emotion)`, `(User)-[:USED_COPING]->(CopingAction)`, `(User)-[:HAS_SESSION]->(Session)` |
| **Mem0 graph store** | ✅ Conditionally wired to Neo4j when `NEO4J_URI` + `NEO4J_PASSWORD` are set |
| **Read-back for insights** | ❌ **ZERO Cypher queries are executed during dashboard rendering** |
| **Read-back for Analyst** | ❌ `analyst_node` does **not query Neo4j** for support patterns, co-occurring symptoms, or resource recommendations |
| **Integration tests** | ✅ `test_neo4j_schema.py` — 15 comprehensive tests covering Sub-graph A completeness and Sub-graph B user patterns |

**Verdict:** Neo4j is a **write-only pipeline** at runtime. Data flows in (via the outbox worker) but is never read back into the intelligence layer. The schema is sophisticated and the write path is production-grade; the read path for insight generation is entirely missing.

---

### 4. Dashboard API (`/api/v1/dashboard/overview`)

| Attribute | Finding |
|---|---|
| **Endpoint** | `/dashboard/overview` — real FastAPI route |
| **`analyst_insights` field** | ⚠️ Populated by `_build_dashboard_insights()` — reads `UserProfile.profile` JSONB blob |
| **Data source** | PostgreSQL `user_profile.profile` JSON blob |
| **Is data real?** | ✅ Yes — data comes from actual session summaries written by `persist_turn_memory()` |
| **Is it the Analyst output?** | ❌ No — it is a post-hoc aggregation of raw extracted signals; no `AnalystBundle` data is included |
| **Nutrition endpoint** | ❌ `/dashboard/nutrition-daily` returns **hardcoded static data** cycled by weekday |
| **Mood trend** | ✅ Real SQL query from `MoodCheckin` table |
| **Session history** | ✅ Real SQL query from `Conversation` table |

**Verdict:** The `analyst_insights` label is **misleading** — it contains real user data but not the output of the Analyst LLM node. The endpoint is functional but architecturally misnamed.

---

### 5. Reflect API (`/api/v1/reflect/*`)

| Attribute | Finding |
|---|---|
| **`/reflect/mental-health-summary`** | ✅ Real — aggregates mood trend + coping stats + clinical profile from DB |
| **`/reflect/mood-trend`** | ✅ Real — SQL query on `MoodCheckin` with 1–90 day window |
| **`/reflect/weekly-note`** | ✅ Real — LLM-generated, cached in `UserProfile.profile.meta.weekly_note_content` |
| **`/reflect/journals`** | ✅ Real — CRUD on `JournalEntry` table |
| **Wellness Score** | ⚠️ Derived formula from mood avg + PHQ-9/GAD-7 + engagement rate — not a direct clinical measurement |
| **Neo4j read** | ❌ None |
| **`has_enough_data` gate** | ✅ Correctly signals when `session_summaries.length < 2` |

**Verdict:** The Reflect surface is the **most production-complete** component. All endpoints query real data. The weekly note generation via LLM is a genuine insight product.

---

### 6. Frontend Dashboard & Reflect (`Home.tsx`, `Reflect.tsx`)

| Surface | Status |
|---|---|
| `Home.tsx` → `/dashboard/nutrition-daily` | ✅ Wired, renders real data (content is static, not personalized) |
| `Home.tsx` → `/reflect/mental-health-summary` | ✅ Wired — wellness radar, streak, peace score all rendered |
| `Reflect.tsx` → all 4 reflect endpoints | ✅ Fully wired with loading states and error boundaries |
| Dashboard `analyst_insights` | ❌ Frontend never fetches `/dashboard/overview` to render `analyst_insights` |
| No `InsightHypothesis` UI component | ❌ No dedicated insight card rendering Analyst output |

**Verdict:** The frontend is **correctly wired to the Reflect module**. The `analyst_insights` backend field has no corresponding frontend consumer — it is an unused API surface.

---

## GAP MATRIX

| Gap | Severity | Component |
|---|---|---|
| `AnalystBundle` not persisted after each turn | 🔴 Critical | `analyst_node` / DB |
| No dedicated `insight_hypotheses` table | 🔴 Critical | `models.py` |
| Neo4j never queried during insight generation | 🔴 Critical | `neo4j_client.py` / `analyst_node` |
| `analyst_insights` in dashboard is not Analyst output | 🟠 High | `dashboard.py` |
| Nutrition endpoint returns static hardcoded data | 🟡 Medium | `dashboard.py` |
| No frontend consumer of `analyst_insights` | 🟡 Medium | Frontend |
| Wellness score derived, not direct clinical assessment | 🟡 Medium | `reflect.py` |
| `app.services.outbox_worker` vs `app.core.outbox_worker` discrepancy | 🟡 Medium | `main.py` |

---

## CRITICAL FINDING: OUTBOX WORKER STARTUP GAP

`main.py` calls `_outbox_loop()` via `run_outbox_worker_loop(poll_seconds=10)` from `app.services.outbox_worker` — this is a **different file** from `app.core.outbox_worker`.

```python
# main.py line 52
from app.services.outbox_worker import run_outbox_worker_loop
```

The production-grade `Neo4jApplier` with retry/backoff lives in `app.core.outbox_worker`. The service that is actually started must be verified to confirm it connects to Neo4j or whether it is a simplified polling stub.

> [!CAUTION]
> If `app.services.outbox_worker` does not wire Neo4j, then graph writes are **never executed at runtime** despite the outbox table being populated.

---

## SAFETY ASSESSMENT

| Safety Item | Status |
|---|---|
| Analyst instructed not to diagnose | ✅ Enforced in prompt: "không chẩn đoán", "không dùng 'trầm cảm/rối loạn' như chẩn đoán" |
| Crisis/SOS bypass path | ✅ `decide_sos()` runs before Analyst; SOS path bypasses LangGraph entirely |
| PII masking before storage | ✅ `mask_pii()` applied before every `Message` write and outbox event |
| Analyst output shown to user | ✅ Never — `analyst_ctx` is injected as a system message only |
| Clinical claims in weekly note | ⚠️ LLM instructed "không chẩn đoán" but output not passed through a safety validator |
| Neo4j user data | ✅ Only behavioral signals stored (trigger labels, emotion labels) — no raw text |

**Overall Safety Verdict:** The safety architecture is **adequate for the current partial pipeline**. The distress router and SOS gate are production-grade.

---

## MINIMAL ACTIONABLE FIX PLAN

### Priority 1 — Persist Analyst Output (1–2 days)

Create a lightweight `analyst_signals` table and write `AnalystBundle` to it after each analyst turn.

```python
# models.py — new table
class AnalystSignal(Base):
    __tablename__ = "analyst_signals"
    signal_id: str          # PK
    user_id: str            # FK → users
    session_id: str         # FK → conversations
    created_at: datetime
    emotional_theme: str
    clinical_note: str
    suggested_focus: str | None
    risk_indicators: list   # JSONB array
    distress_score: float
```

In `chat.py`, after `run_non_sos_turn()`, extract `analyst_bundle` from the graph state and write to `analyst_signals`.

---

### Priority 2 — Wire Dashboard to Real Analyst Data (1 day)

Replace `_build_dashboard_insights()` in `dashboard.py` with a query against `analyst_signals`:

```python
# dashboard.py — replace _build_dashboard_insights
def _fetch_analyst_insights(db: Session, user_id: str) -> dict:
    recent = db.scalars(
        select(AnalystSignal)
        .where(AnalystSignal.user_id == user_id)
        .order_by(AnalystSignal.created_at.desc())
        .limit(5)
    ).all()
    # aggregate emotional_theme frequencies, top risk_indicators
    ...
```

---

### Priority 3 — Add Neo4j Read to Analyst Node (2–3 days)

Add a `query_neo4j_context()` helper that runs before `analyst_node` (or inside it) to fetch:
- Resources that `HELPS_WITH` the user's top trigger symptoms
- `CO_OCCURS_WITH` symptoms for pattern matching
- User's historical `USED_COPING` effectiveness from Neo4j

```cypher
-- Resource recommendation for a detected emotional theme
MATCH (r:Resource)-[h:HELPS_WITH]->(s:Symptom)
WHERE s.slug IN $detected_symptoms
RETURN r.resource_id, r.title_vi, h.strength
ORDER BY h.strength DESC LIMIT 3
```

This transforms the Analyst from a pure LLM call into a **graph-grounded inference engine**.

---

### Priority 4 — Verify Outbox Worker Neo4j Wiring (0.5 days)

Inspect `app/services/outbox_worker.py` and confirm whether it actually connects to Neo4j. If it is a stub, update `main.py`:

```python
# main.py — use the real Neo4j-wired worker
from app.core.outbox_worker import run_worker
```

And ensure `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` are set in `.env`.

---

### Priority 5 — Frontend Insight Card (1 day)

Add a service call and UI component to render `analyst_insights` from `/dashboard/overview`:

```typescript
// dashboardService.ts
export async function getAnalystInsights(): Promise<AnalystInsights> {
  const data = await httpClient.get<OverviewPayload>('/dashboard/overview')
  return data.analyst_insights
}
```

Render in `Home.tsx` as an "Insight của tuần" card with emotional theme + top triggers.

---

## PRODUCTION READINESS VERDICT

| Dimension | Score | Notes |
|---|---|---|
| Data genuineness | 8/10 | Real PostgreSQL data, real LLM calls |
| End-to-end connectivity | 4/10 | Missing persist → read loop for Analyst |
| Neo4j integration | 3/10 | Write path wired; read path absent |
| Safety | 8/10 | Distress gating and PII masking solid |
| Frontend wiring (Reflect) | 9/10 | Fully connected |
| Frontend wiring (Dashboard insights) | 2/10 | `analyst_insights` has no consumer |
| Longitudinal pattern matching | 2/10 | No Cypher queries at insight generation time |
| **Overall** | **5/10** | **PARTIAL_BACKEND_REAL — not production-complete** |

---

*Report generated from source inspection of: `langgraph_chat.py`, `session_summary.py`, `longterm_memory.py`, `memory_enrichment.py`, `neo4j_client.py`, `outbox_worker.py` (core + services), `dashboard.py`, `reflect.py`, `models.py`, `mem0_service.py`, `main.py`, `chat.py`, `Home.tsx`, `Reflect.tsx`, `dashboardService.ts`, `test_neo4j_schema.py`.*
