# Phase 3 — Frontend Dashboard and Check-in History

> **For agentic workers:** Use `superpowers:subagent-driven-development`. Steps use `- [ ]` syntax.

---

## 1. Files to Create / Modify

| Action | Path |
|---|---|
| Modify | `frontend/src/services/dashboardService.ts` |
| Create | `frontend/src/components/dashboard/SignCard.tsx` |
| Create | `frontend/src/components/dashboard/WellnessDimensionCards.tsx` |
| Create | `frontend/src/components/dashboard/CheckinHistoryModal.tsx` |
| Modify | `frontend/src/components/wellness/MoodCalendar.tsx` |
| Modify | `frontend/src/components/pages/Reflect.tsx` |
| Modify | `frontend/src/components/pages/Home.tsx` |

---

## 2. Frontend Service Layer — `dashboardService.ts`

- [ ] Replace current minimal file with typed calls:

```typescript
import { httpClient } from '../api/httpClient'

export type DashboardReadinessLevel =
    'no_data' | 'first_signals' | 'early_insight' | 'weekly_trend' | 'stable_pattern'

export type DashboardSufficiency = {
    readiness_level: DashboardReadinessLevel
    active_days: number
    mood_checkin_count: number
    total_session_count: number
    deep_session_count: number
    evidence_window_start: string | null
    evidence_window_end: string | null
    message: string
    next_data_needed: string[]
}

export type InsightCard = {
    insight_id: string
    title: string
    user_safe_summary: string
    evidence_count: number
    evidence_sources: string[]
    confidence: 'low' | 'medium' | 'high'
    severity_band: 'neutral' | 'watch' | 'supportive_attention'
    suggested_action: string | null
    updated_at: string
}

export type WellnessDimension = {
    dimension: 'emotion' | 'sleep' | 'mindfulness' | 'connection' | 'body' | 'growth'
    label: string
    status: 'unknown' | 'limited_data' | 'steady' | 'needs_attention' | 'improving'
    score: number | null
    explanation: string
    evidence_count: number
    suggested_action: string | null
}

export type CheckinHistoryItem = {
    checkin_id: string
    logged_at: string
    date: string
    time_bucket: 'morning' | 'afternoon' | 'evening' | 'other'
    mood_label: string | null
    mood_score: number | null
    emotions: string[]
    triggers: string[]
    note: string | null
}

export type CheckinHistoryDay = {
    date: string
    completed: boolean
    checkins: CheckinHistoryItem[]
}

export type DashboardReflectSummary = {
    sufficiency: DashboardSufficiency
    top_insights: InsightCard[]
    wellness_dimensions: WellnessDimension[]
    mood_series: Array<{ date: string; mood_score: number; mood_score_pct: number;
                         label: string; checkin_count: number }>
    checkin_history_preview: CheckinHistoryDay[]
    radar_available: boolean
}

export const dashboardService = {
    getNutritionDailyTip: () =>
        httpClient.get<NutritionDailyTip>('/dashboard/nutrition-daily'),
    getReflectSummary: () =>
        httpClient.get<DashboardReflectSummary>('/dashboard/reflect-summary'),
    getCheckinHistory: (range: '30d' | '90d' | 'all' = '30d') =>
        httpClient.get<{ history: CheckinHistoryDay[] }>(
            `/dashboard/checkin-history?range=${range}`),
}

export type NutritionDailyTip = {
    day_index: number; dish: string; benefit: string; tip: string; timezone: string
}
```

---

## 3. `SignCard.tsx` — Replace Peace Score

- [ ] Create `frontend/src/components/dashboard/SignCard.tsx`

Behavior by `readiness_level`:

| Level | Title | Body | CTA |
|---|---|---|---|
| `no_data` | Chưa đủ dữ liệu | "Serene cần thêm vài check-in hoặc một vài phiên trò chuyện để nhận ra xu hướng đáng tin hơn." | Button: "Check-in cảm xúc" |
| `first_signals` | Đã có tín hiệu đầu tiên | Từ `sufficiency.message` | Evidence chips: checkin count + session count |
| `early_insight` | Tín hiệu ban đầu | First insight card `user_safe_summary` | Confidence badge + evidence chip |
| `weekly_trend` | Xu hướng tuần | First insight card summary | Evidence window + confidence |
| `stable_pattern` | Xu hướng ổn định | First insight summary | Confidence badge "Xu hướng khá rõ" |

Rules:
- **No percentage ring.** No `%` score. No `Peace Score` label anywhere.
- Evidence chips use format: `4 check-in`, `2 phiên trò chuyện`, `7 ngày gần đây`.
- Confidence labels: `"Dữ liệu còn ít"` / `"Độ rõ vừa phải"` / `"Xu hướng khá rõ"`.
- `next_data_needed` bullets shown as a small list under `no_data` / `first_signals`.

---

## 4. `WellnessDimensionCards.tsx` — Replace Primary Radar Explanation

- [ ] Create `frontend/src/components/dashboard/WellnessDimensionCards.tsx`
- [ ] Grid of 6 cards (2-col mobile, 3-col tablet, 6-col desktop).
- [ ] Each card: dimension icon, label, status badge, explanation text (from backend), evidence count chip, optional suggested_action text.
- [ ] Status badge colors: `steady` → green, `improving` → teal, `needs_attention` → amber, `limited_data` → gray, `unknown` → gray.
- [ ] No computed scores from frontend — pass `score` (int | null) from backend directly.
- [ ] If `score !== null`, show a small progress-bar segment (0-100). If null, show "–".

---

## 5. `CheckinHistoryModal.tsx` — Shared Modal

- [ ] Create `frontend/src/components/dashboard/CheckinHistoryModal.tsx`
- [ ] Renders as a bottom sheet on mobile, centered modal on desktop.
- [ ] Props: `open: boolean`, `onClose: () => void`.
- [ ] Fetches `dashboardService.getCheckinHistory('90d')` on first open (lazy).
- [ ] Top section: compact 4-week calendar grid.
  - Green cell = `completed: true` (any check-in that day).
  - Empty cell = no check-in.
  - Uses brand green (`bg-primary` / `text-white`), not mood color gradient.
- [ ] Below calendar: scrollable list grouped by date (newest first).
  - Day header: `dd/MM` + completed badge.
  - Under each day: one card per `checkin` item in `day.checkins`.
  - Card shows: time_bucket label (Sáng/Chiều/Tối/Khác), mood emoji + label, emotion chips, trigger chips, note (if any).
- [ ] Time-bucket display names: `morning→Sáng`, `afternoon→Chiều`, `evening→Tối`, `other→Khác`.
- [ ] Do NOT compute reward/streak state in this component — backend handles it.

---

## 6. `MoodCalendar.tsx` — Add Completion Mode

- [ ] Add optional prop `mode?: 'score' | 'completion'` (default `'score'`).
- [ ] In `completion` mode: cell is green (`bg-primary/80`) if the date is in a provided `completedDates: Set<string>` prop; otherwise empty.
- [ ] Keep existing `score` mode unchanged for the Reflect mood calendar section.

---

## 7. `Reflect.tsx` Refactor

- [ ] Replace fetch of `/reflect/mental-health-summary` with `dashboardService.getReflectSummary()`.
- [ ] Remove `peaceScore` ring section entirely.
- [ ] Add `<SignCard sufficiency={summary.sufficiency} insights={summary.top_insights} />` at top.
- [ ] Add `<WellnessDimensionCards dimensions={summary.wellness_dimensions} />` section below mood chart.
- [ ] Gate `<WellnessRadar>` on `summary.radar_available === true` only.
- [ ] Mood chart: use `summary.mood_series` (already daily-averaged). Update empty state copy:
  ```
  "Chưa đủ dữ liệu để vẽ xu hướng.
   Cần ít nhất 3 ngày có check-in hoặc 5 check-in để Serene vẽ mood trend đáng tin hơn."
  ```
- [ ] Calendar section: pass `completedDates` from `checkin_history_preview` to `<MoodCalendar mode="completion">`.
- [ ] Add `[CheckinHistoryModal open={historyOpen} onClose=...]` state.
- [ ] Calendar click → open `CheckinHistoryModal` (not day-detail sheet).
- [ ] Keep `DayDetailSheet` for backward compat but make primary entry point the modal.
- [ ] Remove direct use of `clinical_snapshot`, `wellness_score`, `deriveWellnessScores()`.

---

## 8. `Home.tsx` Update

- [ ] Import `CheckinHistoryModal`.
- [ ] Add `const [historyOpen, setHistoryOpen] = useState(false)`.
- [ ] Wrap `Chuỗi tuần này` label in a `<button onClick={() => setHistoryOpen(true)}>`:
  ```tsx
  <button onClick={() => setHistoryOpen(true)}
          className="text-xs uppercase tracking-[0.22em] text-theme-text-secondary
                     underline-offset-2 hover:underline">
      Chuỗi tuần này
  </button>
  ```
- [ ] Render `<CheckinHistoryModal open={historyOpen} onClose={() => setHistoryOpen(false)} />`.

---

## 9. Empty / Loading / Error States

- [ ] Loading: skeleton cards for SignCard, WellnessDimensionCards (3 x pulse divs).
- [ ] Error: single amber banner with "Không tải được dữ liệu. Vui lòng thử lại sau."
- [ ] No-data: SignCard shows helpful copy + CTA — no `0%`, no empty rings.

---

## 10. UI/UX Rules (non-negotiable)

- Never render any field from: `clinical_note_internal`, `risk_indicators`, `phq9_score`, `gad7_score`, `crisis_level`.
- Never show raw numeric wellness/risk/distress score.
- Never compute insight or readiness level in frontend — consume backend strings only.
- Copy must be Vietnamese, warm, non-clinical. Refer to [00_INDEX §Architecture Invariants].
