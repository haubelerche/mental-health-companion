# Admin Dashboard Metrics Fix + System Trace Viewer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the admin dashboard showing 0 everywhere (root cause: AdminLogin.tsx never sets the real backend JWT cookie), then add a minimal system trace panel so admins can observe per-turn latency, route decisions, and flow transitions for all users.

**Architecture:** 
- Task 1 wires `AdminLogin.tsx` to call the real backend `POST /admin/auth/login` (which issues the `admin_access_token` cookie). All admin API calls already depend on this cookie via `get_admin_claims`.
- Tasks 2–4 add a Redis-backed turn trace store: `run_non_sos_turn()` writes a compact summary record (node latencies, distress score, route) into a Redis capped list after each turn; a new admin endpoint reads it; a new frontend page renders it.
- Task 5 wires navigation + routing for the new page.

**Tech Stack:** FastAPI, SQLAlchemy, Redis (`redis-py`), LangGraph, React 19 / TypeScript, Vite, Recharts, framer-motion.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/admin/AdminLogin.tsx` | Modify | Add TOTP field; call real `adminService.login()`; set `admin_authenticated` on success |
| `backend/app/services/turn_trace_store.py` | Create | Redis ring-buffer for last 200 turn traces; `record_trace()` / `get_recent_traces()` |
| `backend/app/services/langgraph_chat.py` | Modify | Call `record_trace()` at end of `run_non_sos_turn()` |
| `backend/app/api/v1/routers/admin/dashboard.py` | Modify | Add `GET /admin/traces/recent` endpoint |
| `frontend/src/services/adminService.ts` | Modify | Add `AdminTraceRecord` type + `getRecentTraces()` |
| `frontend/src/components/admin/AdminSystemTrace.tsx` | Create | Trace list + expandable span detail view |
| `frontend/src/components/admin/AdminSystemTrace.css` | Create | Minimal scoped styles |
| `frontend/src/routes/paths.ts` | Modify | Add `adminSystemTrace` route path |
| `frontend/src/routes/AppRoutes.tsx` | Modify | Register `<AdminSystemTrace />` under `/admin/system-trace` |
| `frontend/src/components/admin/layout/AdminSidebar.tsx` | Modify | Add "Luồng hệ thống" nav link |

---

## Task 1: Fix AdminLogin — call real backend

**Root cause:** `AdminLogin.tsx` does a local credential check (hardcoded) and only sets `sessionStorage`. No `admin_access_token` cookie is ever issued → all admin API calls return 401 silently → dashboard shows 0.

**Fix:** Add a TOTP field and call `adminService.login()` which calls `POST /v1/admin/auth/login`. On success the backend sets `admin_access_token` cookie.

**Files:**
- Modify: `frontend/src/components/admin/AdminLogin.tsx`

- [ ] **Step 1: Replace the local-only credential check with a real backend call**

Open `frontend/src/components/admin/AdminLogin.tsx`. Replace the entire `handleSubmit` function body with:

```tsx
const handleSubmit: FormSubmitHandler = async (event) => {
  event.preventDefault()
  setErrorMessage('')
  setIsSubmitting(true)

  try {
    await adminService.login({ email: email.trim(), password, totp_code: totpCode.trim() })
    sessionStorage.setItem('admin_authenticated', '1')
    toast.success('Đăng nhập admin thành công')
    navigate(ROUTE_PATHS.adminDashboard)
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : 'Email, mật khẩu hoặc mã TOTP không đúng.'
    setErrorMessage(message)
    toast.error(message)
  } finally {
    setIsSubmitting(false)
  }
}
```

Add the `totpCode` state at the top of the component alongside the other `useState` calls:
```tsx
const [totpCode, setTotpCode] = useState('')
```

Add the `adminService` import at the top of the file:
```tsx
import { adminService } from '../../services/adminService'
```

Remove the two hardcoded constant lines:
```tsx
// DELETE these two lines:
const ADMIN_EMAIL = 'admin@gmail.com'
const ADMIN_PASSWORD = 'MatKhauAdmin@2026'
```

- [ ] **Step 2: Add TOTP input field to the form UI**

In the `<form>` JSX, after the existing password `<input>`, add:

```tsx
{/* TOTP */}
<div>
  <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">
    Mã TOTP (6 số)
  </label>
  <div className="relative">
    <Key className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
    <input
      type="text"
      inputMode="numeric"
      pattern="[0-9]{6}"
      maxLength={6}
      value={totpCode}
      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
      placeholder="123456"
      required
      className="w-full pl-11 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500/50 focus:bg-white/[0.07] transition-all text-sm font-medium tracking-widest"
    />
  </div>
</div>
```

(`Key` is already imported in the existing file.)

- [ ] **Step 3: Verify the form now calls the backend**

Run: `npm --prefix frontend run lint`
Expected: exits 0 (no new TS errors)

Run: `npm --prefix frontend run build`
Expected: exits 0

- [ ] **Step 4: Manual smoke test**

Run: `npm --prefix frontend run dev`
Open `http://localhost:5173/admin/login`
Enter real admin credentials + TOTP → dashboard should load with real numbers.
Check browser DevTools → Application → Cookies: `admin_access_token` cookie should be present.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/admin/AdminLogin.tsx
git commit -m "fix: wire AdminLogin to real backend login endpoint with TOTP"
```

---

## Task 2: Backend — turn trace store (Redis ring-buffer)

**Files:**
- Create: `backend/app/services/turn_trace_store.py`

- [ ] **Step 1: Create the store module**

Create `backend/app/services/turn_trace_store.py`:

```python
"""Ring-buffer for recent chat turn traces stored in Redis.

Records are kept for admin observability only. No PII or raw user text.
The list is capped at _MAX_TRACES entries; each record expires via list-level TTL.
"""
from __future__ import annotations

import json
import logging
import time

from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

_REDIS_KEY = "admin:turn_traces"
_MAX_TRACES = 200
_TTL_SECONDS = 86_400  # 24 h


def record_trace(record: dict) -> None:
    """Push one turn trace record into the Redis ring-buffer. Fail silently."""
    r = get_redis()
    if not r:
        return
    try:
        serialized = json.dumps(record, default=str)
        r.lpush(_REDIS_KEY, serialized)
        r.ltrim(_REDIS_KEY, 0, _MAX_TRACES - 1)
        r.expire(_REDIS_KEY, _TTL_SECONDS)
    except Exception:
        logger.debug("turn_trace_store: redis write failed", exc_info=True)


def get_recent_traces(limit: int = 50) -> list[dict]:
    """Return the most recent `limit` traces (newest first). Returns [] if Redis unavailable."""
    r = get_redis()
    if not r:
        return []
    try:
        raw_list = r.lrange(_REDIS_KEY, 0, limit - 1)
    except Exception:
        logger.debug("turn_trace_store: redis read failed", exc_info=True)
        return []
    result = []
    for raw in raw_list:
        try:
            result.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return result
```

- [ ] **Step 2: Run backend tests to ensure nothing is broken**

Run: `pytest backend/tests -q`
Expected: all previously passing tests still pass (new file has no import side-effects)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/turn_trace_store.py
git commit -m "feat: add Redis ring-buffer turn_trace_store for admin observability"
```

---

## Task 3: Backend — instrument run_non_sos_turn + add traces endpoint

**Files:**
- Modify: `backend/app/services/langgraph_chat.py` (line ~1684, just before `_tracer.flush()`)
- Modify: `backend/app/api/v1/routers/admin/dashboard.py`

- [ ] **Step 1: Import turn_trace_store in langgraph_chat.py**

At the top of `backend/app/services/langgraph_chat.py`, alongside other service imports, add:

```python
from app.services.turn_trace_store import record_trace as _record_trace
```

- [ ] **Step 2: Hook record_trace into run_non_sos_turn**

In `run_non_sos_turn()`, the function already computes `started = time.perf_counter()` at line ~1594 and calls `_tracer.flush()` at line ~1684. Add the `record_trace` call **right before** `_tracer.flush()`:

```python
    # --- trace record for admin dashboard ----------------------------------
    _record_trace({
        "turn_id": correlation_id,
        "ts": time.time(),
        "user_id_hash": _user_hash(user_id or ""),
        "session_id": session_id or "",
        "distress_score": round(distress_score, 3),
        "route_decision": out.get("route_decision", "friend"),
        "routing_history": out.get("routing_history", []),
        "total_ms": round((time.perf_counter() - started) * 1000, 1),
        "reply_len": len(str(out.get("reply") or "")),
    })
    # -----------------------------------------------------------------------
    _tracer.flush()
```

(`_user_hash` is already defined in the file; `time` is already imported.)

- [ ] **Step 3: Add /admin/traces/recent endpoint**

In `backend/app/api/v1/routers/admin/dashboard.py`, after the existing imports, add:

```python
from app.services.turn_trace_store import get_recent_traces
```

Then append the new route handler at the bottom of the file:

```python
@router.get("/traces/recent")
def admin_traces_recent(
    request: Request,
    limit: int = 50,
    claims: dict = Depends(get_admin_claims),
):
    enforce_admin_ip(request)
    limit = max(1, min(limit, 200))
    traces = get_recent_traces(limit=limit)
    return ok({"traces": traces, "count": len(traces)})
```

- [ ] **Step 4: Run backend tests**

Run: `pytest backend/tests -q`
Expected: exits 0

- [ ] **Step 5: Smoke test endpoint manually**

Start the backend:
```
cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Send a chat turn (any conversation in the app), then:
```
curl -s -b "admin_access_token=<YOUR_TOKEN>" http://127.0.0.1:8000/v1/admin/traces/recent | python -m json.tool
```
Expected: `{"success": true, "data": {"traces": [...], "count": N}}`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/langgraph_chat.py \
        backend/app/api/v1/routers/admin/dashboard.py
git commit -m "feat: instrument run_non_sos_turn + expose /admin/traces/recent"
```

---

## Task 4: Frontend — AdminSystemTrace component

**Files:**
- Modify: `frontend/src/services/adminService.ts`
- Create: `frontend/src/components/admin/AdminSystemTrace.tsx`
- Create: `frontend/src/components/admin/AdminSystemTrace.css`

- [ ] **Step 1: Add type + service method to adminService.ts**

In `frontend/src/services/adminService.ts`, after the existing `AdminCostDashboardResponse` type block, add:

```ts
export type AdminTraceSpan = {
  node: string
  duration_ms: number
  status?: string
  route_reason?: string
}

export type AdminTraceRecord = {
  turn_id: string
  ts: number
  user_id_hash: string
  session_id: string
  distress_score: number
  route_decision: string
  routing_history: AdminTraceSpan[]
  total_ms: number
  reply_len: number
}

export type AdminRecentTracesResponse = {
  traces: AdminTraceRecord[]
  count: number
}
```

In the `adminService` object, add:

```ts
getRecentTraces: (limit: number = 50) =>
    httpClient.get<AdminRecentTracesResponse>(`/admin/traces/recent?limit=${limit}`),
```

- [ ] **Step 2: Create AdminSystemTrace.css**

Create `frontend/src/components/admin/AdminSystemTrace.css`:

```css
.trace-root {
    padding: 2.5rem;
    min-height: 100vh;
    background: transparent;
}

.trace-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 2.5rem;
}

.trace-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 0.5rem;
}

.trace-table th {
    text-align: left;
    font-size: 9px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: rgb(100 116 139);
    padding: 0 1rem 0.5rem 1rem;
}

.trace-row {
    background: rgba(255 255 255 / 0.03);
    border: 1px solid rgba(255 255 255 / 0.06);
    border-radius: 1rem;
    cursor: pointer;
    transition: background 0.15s;
}

.trace-row:hover {
    background: rgba(99 102 241 / 0.08);
    border-color: rgba(99 102 241 / 0.2);
}

.trace-row td {
    padding: 0.9rem 1rem;
    font-size: 11px;
    color: rgb(203 213 225);
    font-weight: 600;
    vertical-align: middle;
}

.trace-row td:first-child {
    border-radius: 1rem 0 0 1rem;
}

.trace-row td:last-child {
    border-radius: 0 1rem 1rem 0;
}

.trace-detail {
    background: rgba(15 23 42 / 0.8);
    border: 1px solid rgba(255 255 255 / 0.06);
    border-top: none;
    border-radius: 0 0 1rem 1rem;
    padding: 1.25rem 1.5rem;
}

.span-bar-track {
    height: 6px;
    background: rgba(255 255 255 / 0.05);
    border-radius: 999px;
    overflow: hidden;
    flex: 1;
}

.span-bar-fill {
    height: 100%;
    border-radius: 999px;
}

.distress-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 9px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
```

- [ ] **Step 3: Create AdminSystemTrace.tsx**

Create `frontend/src/components/admin/AdminSystemTrace.tsx`:

```tsx
import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, RefreshCw, ChevronDown, ChevronRight, Cpu } from 'lucide-react'
import { adminService, type AdminTraceRecord } from '../../services/adminService'
import './AdminSystemTrace.css'
import './AdminCommon.css'

const NODE_COLORS: Record<string, string> = {
    safety_gate: '#10b981',
    distress_router: '#f59e0b',
    analyst: '#8b5cf6',
    friend: '#6366f1',
    friend_stream: '#6366f1',
    run_non_sos_turn_total: '#64748b',
}

function distressBadge(score: number) {
    if (score >= 0.82) return { label: 'Cao', bg: '#ef4444', text: '#fff' }
    if (score >= 0.55) return { label: 'Vừa', bg: '#f59e0b', text: '#000' }
    return { label: 'Thấp', bg: '#10b981', text: '#fff' }
}

function formatTs(ts: number) {
    return new Date(ts * 1000).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function SpanRow({ span, maxMs }: { span: { node: string; duration_ms: number; status?: string; route_reason?: string }; maxMs: number }) {
    const color = NODE_COLORS[span.node] || '#64748b'
    const pct = Math.min(100, (span.duration_ms / (maxMs || 1)) * 100)
    return (
        <div className="flex items-center gap-4 py-2">
            <span className="text-[10px] font-black text-slate-400 uppercase w-44 truncate" style={{ color }}>{span.node}</span>
            <div className="span-bar-track">
                <div className="span-bar-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
            </div>
            <span className="text-[10px] font-black text-slate-300 w-16 text-right">{span.duration_ms.toFixed(0)} ms</span>
            {span.route_reason && (
                <span className="text-[9px] text-slate-500 font-medium italic">{span.route_reason}</span>
            )}
        </div>
    )
}

function TraceRow({ trace }: { trace: AdminTraceRecord }) {
    const [open, setOpen] = useState(false)
    const badge = distressBadge(trace.distress_score)
    const spans = trace.routing_history || []
    const maxMs = Math.max(...spans.map(s => s.duration_ms), 1)

    const routeColor = trace.route_decision === 'analyst' ? '#8b5cf6'
        : trace.route_decision === 'friend' ? '#6366f1' : '#64748b'

    return (
        <>
            <tr className="trace-row" onClick={() => setOpen(o => !o)}>
                <td className="font-mono text-slate-500 text-[10px]">{formatTs(trace.ts)}</td>
                <td>
                    <span className="font-mono text-[10px] text-slate-400">{trace.user_id_hash}</span>
                </td>
                <td>
                    <span
                        className="distress-badge"
                        style={{ backgroundColor: `${badge.bg}20`, color: badge.bg, border: `1px solid ${badge.bg}40` }}
                    >
                        {trace.distress_score.toFixed(2)} · {badge.label}
                    </span>
                </td>
                <td>
                    <span className="text-[10px] font-black uppercase" style={{ color: routeColor }}>
                        {trace.route_decision}
                    </span>
                </td>
                <td>
                    <span className={`text-[11px] font-black ${trace.total_ms > 3000 ? 'text-rose-400' : trace.total_ms > 1500 ? 'text-amber-400' : 'text-emerald-400'}`}>
                        {trace.total_ms.toFixed(0)} ms
                    </span>
                </td>
                <td>
                    {open ? <ChevronDown size={14} className="text-indigo-400" /> : <ChevronRight size={14} className="text-slate-500" />}
                </td>
            </tr>
            {open && (
                <tr>
                    <td colSpan={6} className="!p-0">
                        <AnimatePresence>
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="trace-detail"
                            >
                                {spans.length === 0 ? (
                                    <p className="text-[10px] text-slate-500 italic">Không có span chi tiết cho lượt này.</p>
                                ) : (
                                    <div>
                                        <p className="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-3">
                                            Node Spans — {spans.length} bước
                                        </p>
                                        {spans.map((s, i) => (
                                            <SpanRow key={i} span={s} maxMs={maxMs} />
                                        ))}
                                    </div>
                                )}
                                <div className="mt-3 pt-3 border-t border-white/5 flex gap-8 text-[9px] text-slate-500 font-black uppercase tracking-widest">
                                    <span>Session: <span className="text-slate-300 font-mono">{trace.session_id.slice(0, 16)}…</span></span>
                                    <span>Reply len: <span className="text-slate-300">{trace.reply_len} chars</span></span>
                                </div>
                            </motion.div>
                        </AnimatePresence>
                    </td>
                </tr>
            )}
        </>
    )
}

export default function AdminSystemTrace() {
    const [traces, setTraces] = useState<AdminTraceRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const loadTraces = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await adminService.getRecentTraces(100)
            setTraces(res.traces)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Không tải được traces.')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        loadTraces()
    }, [loadTraces])

    return (
        <div className="trace-root">
            <div className="trace-header">
                <div>
                    <h1 className="text-4xl font-black text-white tracking-tighter uppercase mb-1 flex items-center gap-3">
                        <Cpu className="text-indigo-400" size={32} />
                        Luồng hệ thống
                    </h1>
                    <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.3em]">
                        {traces.length} lượt gần nhất · Latency per node · Route decisions
                    </p>
                </div>
                <button
                    onClick={loadTraces}
                    disabled={loading}
                    className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-2xl text-[10px] font-black text-white uppercase hover:bg-white/10 transition-all tracking-widest"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    Làm mới
                </button>
            </div>

            {error && (
                <div className="mb-6 px-6 py-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-sm font-black uppercase">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="space-y-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="admin-skeleton h-14 w-full rounded-2xl" />
                    ))}
                </div>
            ) : traces.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-32 text-slate-600">
                    <Activity size={40} className="mb-4 opacity-20" />
                    <p className="text-[11px] font-black uppercase tracking-widest">Chưa có trace nào được ghi nhận</p>
                    <p className="text-[10px] text-slate-700 mt-2">Traces sẽ xuất hiện sau khi có cuộc hội thoại đầu tiên.</p>
                </div>
            ) : (
                <table className="trace-table">
                    <thead>
                        <tr>
                            <th>Thời gian</th>
                            <th>User hash</th>
                            <th>Distress</th>
                            <th>Route</th>
                            <th>Tổng độ trễ</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>
                        {traces.map(trace => (
                            <TraceRow key={trace.turn_id} trace={trace} />
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    )
}
```

- [ ] **Step 4: Lint + build check**

Run: `npm --prefix frontend run lint`
Expected: exits 0

Run: `npm --prefix frontend run build`
Expected: exits 0

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/adminService.ts \
        frontend/src/components/admin/AdminSystemTrace.tsx \
        frontend/src/components/admin/AdminSystemTrace.css
git commit -m "feat: add AdminSystemTrace page with per-turn latency and route view"
```

---

## Task 5: Wire navigation + routing

**Files:**
- Modify: `frontend/src/routes/paths.ts`
- Modify: `frontend/src/routes/AppRoutes.tsx`
- Modify: `frontend/src/components/admin/layout/AdminSidebar.tsx`

- [ ] **Step 1: Add route path**

In `frontend/src/routes/paths.ts`, in the `//admin` block, add:

```ts
adminSystemTrace: '/admin/system-trace',
```

- [ ] **Step 2: Register route in AppRoutes.tsx**

In `frontend/src/routes/AppRoutes.tsx`, add the import at the top:

```tsx
import AdminSystemTrace from '../components/admin/AdminSystemTrace'
```

Inside the admin `<Route path={ROUTE_PATHS.admin} ...>` block, after the existing `automation` route, add:

```tsx
<Route path="system-trace" element={<AdminSystemTrace />} />
```

- [ ] **Step 3: Add sidebar link**

In `frontend/src/components/admin/layout/AdminSidebar.tsx`, add `GitBranch` to the lucide import:

```ts
import { Activity, AlertTriangle, BarChart3, Bell, Cpu, GitBranch, LayoutDashboard, LogOut, Mail, Package, Shield, Users } from 'lucide-react'
```

Add to the `links` array (after `automation`):

```ts
{ to: ROUTE_PATHS.adminSystemTrace, label: 'Luồng hệ thống', icon: GitBranch },
```

Add the ROUTE_PATHS import if the new constant isn't auto-resolved (it should already be imported via `import { ROUTE_PATHS } from '../../../routes/paths'`).

- [ ] **Step 4: Lint + build**

Run: `npm --prefix frontend run lint`
Expected: exits 0

Run: `npm --prefix frontend run build`
Expected: exits 0

- [ ] **Step 5: Full smoke test**

Run: `npm --prefix frontend run dev`
1. Navigate to `http://localhost:5173/admin/login` → log in with real credentials + TOTP
2. Dashboard shows real KPI numbers (non-zero when data exists)
3. Sidebar shows "Luồng hệ thống"
4. Click it → trace table loads (empty until a chat turn happens, then refresh)
5. Click a trace row → span bar chart expands showing node latencies

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/paths.ts \
        frontend/src/routes/AppRoutes.tsx \
        frontend/src/components/admin/layout/AdminSidebar.tsx
git commit -m "feat: add system-trace route + sidebar nav"
```

---

## Self-Review

**Spec coverage:**
1. Dashboard shows 0 → fixed by Task 1 (real backend login with JWT cookie) ✓
2. System trace with latency per node → Task 2+3 (Redis store + endpoint) ✓
3. System trace viewer in admin → Task 4+5 (component + routing) ✓
4. All users' turns observable → `_user_hash` anonymises but admin sees all traces ✓
5. No PII in traces → only hashed user_id, session_id, distress_score (numeric), route decision, lengths ✓

**Placeholder scan:** No TBDs. All code blocks are complete.

**Type consistency:**
- `AdminTraceSpan.node` is `string` → matches `routing_history` entries in graph state ✓
- `AdminTraceRecord.routing_history` is `AdminTraceSpan[]` → matches backend `out.get("routing_history", [])` ✓
- `adminService.getRecentTraces()` returns `AdminRecentTracesResponse` with `traces: AdminTraceRecord[]` ✓
- Backend `record_trace` writes `routing_history` as the same list the graph already populates ✓

**Edge cases:**
- Redis unavailable → `record_trace()` and `get_recent_traces()` both fail silently; endpoint returns `{"traces": [], "count": 0}` ✓
- No turns yet → frontend renders empty state "Chưa có trace nào" ✓
- Turn with no routing_history spans → detail panel shows fallback message ✓
