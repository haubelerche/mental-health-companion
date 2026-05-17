# Serene Dashboard Refactor — Implementation Plan Index

> **For agentic workers:** Use `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans`. Steps use `- [ ]` syntax for tracking.

**Goal:** Refactor the Serene dashboard from a misleading score panel into an evidence-aware,
non-clinical insight dashboard with proper data sufficiency, safe backend contracts, and
a shared check-in history modal.

**Architecture:** Backend-owned readiness levels drive all UI states. A new
`backend/app/dashboard/` module (types → sufficiency → service) feeds new endpoints consumed
by a refactored `Reflect.tsx` and `Home.tsx`. No clinical, risk, or analyst-internal fields
reach the frontend.

**Tech Stack:** Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy · Alembic · React 19 · TypeScript · Vite · Recharts

---

## Implementation Phases

| # | File | Goal | Key Deliverables |
|---|---|---|---|
| 1 | `01_BACKEND_CONTRACTS_AND_DB.md` | Safe API surface + DB migration | `time_bucket` column, 3 new endpoints, Pydantic models |
| 2 | `02_INSIGHT_PIPELINE_AND_ANALYST.md` | Readiness levels + safe insight generation | Sufficiency service, dimension cards, weekly note safety |
| 3 | `03_FRONTEND_DASHBOARD_AND_HISTORY.md` | Frontend component refactor | SignCard, WellnessDimensionCards, CheckinHistoryModal |
| 4 | `04_TESTING_AND_ACCEPTANCE.md` | Tests + acceptance gates | Backend pytest, frontend build, privacy regression |

---

## Current State (audited 2026-05-06)

| Item | Current Problem |
|---|---|
| `Peace Score 0%` | Shows `0%` with ring when no data — misleading |
| `clinical_snapshot` in API response | Raw PHQ9/GAD7 scores exposed to frontend |
| `wellness_score` formula | Uses PHQ9/GAD7 directly in `reflect.py` |
| Radar always visible | Shown even with 0 data |
| Radar values | Frontend-derived math from clinical scores |
| Mood chart empty state | Generic, no minimum data guidance |
| `Chuỗi tuần này` | Static text — not clickable |
| Progress calendar | Clicks open a day-detail sheet, not full history |
| Multiple check-ins per day | DB unique constraint blocks it |
| Insight cards | Do not exist — no safe summary layer |
| Sufficiency policy | Does not exist on backend |

---

## Data Flow (target)

```
mood_checkins
conversations + messages
session_summaries (profile JSONB)
analyst_signals (internal, profile JSONB)
    │
    ▼
backend/app/dashboard/sufficiency.py   → DashboardDataSufficiency
backend/app/dashboard/service.py       → insight cards, dimension cards, mood series
    │
    ▼
GET /dashboard/reflect-summary         (safe, gated by readiness)
GET /dashboard/checkin-history         (grouped by date, supports multi-bucket)
GET /dashboard/safe-insights           (insight cards only)
    │
    ▼
frontend/src/services/dashboardService.ts
SignCard · WellnessDimensionCards · CheckinHistoryModal · Reflect.tsx · Home.tsx
```

---

## Architecture Invariants (must not be violated)

1. PostgreSQL = source of truth. Neo4j = derived only. Never breaks dashboard.
2. Frontend **never** owns: safety logic, risk scoring, reward math, persona unlock, analyst reasoning.
3. Internal Analyst Agent output → profile JSONB only → safe aggregation → safe endpoint.
4. No raw fields exposed: `clinical_note_internal`, `risk_indicators`, `phq9_score`, `gad7_score`,
   `crisis_level`, `crisis_logs`, `admin_audit_log`.
5. No diagnosis copy. No disorder probability. No raw distress score.
6. `SafetyGate` must remain upstream of all LLM calls — this refactor does not touch it.

---

## Definition of Done

- [ ] `Peace Score 0%` removed from all frontend surfaces
- [ ] Dashboard exposes 5 readiness levels with correct thresholds
- [ ] No raw clinical/risk field in any API response consumed by frontend
- [ ] `Chuỗi tuần này` (Home) and progress calendar (Reflect) open same `CheckinHistoryModal`
- [ ] Multiple check-ins per day supported in DB and API
- [ ] Radar hidden when `readiness_level` is `no_data` or `first_signals`
- [ ] Backend tests pass: `pytest backend/tests -q`
- [ ] Frontend build passes: `npm --prefix frontend run build`
- [ ] `CHANGELOG.md` updated
