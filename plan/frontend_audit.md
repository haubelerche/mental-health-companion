# Frontend Feature Visibility Audit — Serene (A20-App-039)

> **Date:** 2026-05-05  
> **Scope:** `frontend/src/` — React + TypeScript + Vite + TailwindCSS  
> **Plan ref:** `.claude/plan/09_FRONTEND_INTEGRATION.md`, `.claude/plan/00_MASTER_CONTEXT.md`

---

## Frontend Feature Visibility Audit

| Feature | Exists in Code | Reachable in UI | Backend Connected | Renders Correctly | Status | Evidence |
|---|---|---|---|---|---|---|
| Chat UI | Yes | Yes | Yes | Yes | **Pass** | `components/chat/Chat.tsx` |
| Persona Selection | Yes | **No** | Yes | No | **Fail** | `PersonaSelector.tsx` — never imported in Chat |
| Safety Flow UI | Yes | Partial | Yes | Partial | **Partial** | `CrisisPanel`, `HotlineBar` in Chat — no raw score shown, but safety_tier debug shown |
| Voice/TTS UI | Yes | **Partial** | Yes | Partial | **Partial** | `VoiceStatusBadge.tsx` defined but **never imported/used**; inline `voiceStatus` string used instead |
| Mood Check-in | Yes | Yes | Yes | Yes | **Pass** | `CheckinFlow.tsx`, `checkinService.ts` |
| Dashboard / Reflect | Yes | Yes | Yes | Yes | **Pass** | `Reflect.tsx` — wellness radar, mood trend, weekly note all backend-driven |
| Memory Cards | Yes | **No** | Yes | No | **Fail** | `MemoryCardsTab.tsx` exists but **never mounted** in Chat; no sub-tab "Ký ức" |
| Heart Wallet | Yes | Partial | Yes | Partial | **Partial** | Balance shown on Home + RewardsPage; no dedicated wallet/history page |
| Reward Store | Yes | Yes | Yes | Yes | **Pass** | `RewardsPage.tsx` — backend-driven via `rewardsService.getStore()` |
| Persona Unlock | Yes | **No** | Yes | No | **Fail** | `PersonaSelector.tsx` exists but **not mounted anywhere** in app tree |
| Knowledge Unlocks | **No** | No | No | No | **Fail** | No knowledge unlock UI component exists; `RewardShelf` shows "Tri thức" shelf but no dedicated knowledge cards |
| Streaks | Yes | Partial | Yes | Partial | **Partial** | Streak shown on Home + CheckinFlow summary; no dedicated streak reset display |
| Settings/Profile | Yes | Yes | Yes | Yes | **Pass** | `Setting.tsx`, `Profile.tsx` — reachable via sidebar |
| Error/Empty States | Yes | Yes | N/A | Yes | **Pass** | Loading/error guards in Rewards, Memory, Reflect, Chat |
| Navigation | Partial | Partial | N/A | Partial | **Partial** | Sidebar missing **Rewards (Thưởng)** link; mobile nav only shows 5 items (misses Letter, Rewards) |
| Responsive UI | Yes | Partial | N/A | Partial | **Partial** | Mobile nav cuts to 5 items — Rewards and Letter not reachable from mobile |

---

## Missing or Invisible Frontend Features

| ID | Feature | Symptom | Root Cause | File/Path | Required Fix |
|---|---|---|---|---|---|
| F-01 | **Chat/Ký ức sub-tab** | No "Ký ức" tab visible inside Chat | `MemoryCardsTab.tsx` is never imported/rendered in `Chat.tsx` | `components/chat/Chat.tsx` | Add a tab switcher (Chat / Ký ức) inside `Chat.tsx` and conditionally render `<MemoryCardsTab />` |
| F-02 | **PersonaSelector** | No persona switcher visible in Chat | `PersonaSelector.tsx` is never imported or mounted in `Chat.tsx` | `components/chat/Chat.tsx` | Import and render `<PersonaSelector onSelect={...} />` inside the Chat panel (e.g. options dropdown or header slot) |
| F-03 | **ChatEntryCheckIn** | Check-in prompt on chat entry never shown | `ChatEntryCheckIn.tsx` exists but is never imported in Chat or anywhere else | `components/chat/Chat.tsx` | Mount `<ChatEntryCheckIn />` at the top of the chat message area on first render or as a floating banner |
| F-04 | **VoiceStatusBadge** | Voice status displayed as raw string, not the typed component | `VoiceStatusBadge.tsx` defines all 8 TTS states but is never imported; Chat uses `voiceStatus: string` inline | `components/chat/Chat.tsx`, `components/chat/VoiceStatusBadge.tsx` | Replace inline `<span>{voiceStatus}</span>` in Chat header with `<VoiceStatusBadge status={...} />` |
| F-05 | **MealCheckInCard** | Meal check-in (Nutrition tab) never surfaces +5 Tim UX | `MealCheckInCard.tsx` exists with correct API call `/nutrition/meal-checkins` but is **never imported** in `Nutrition.tsx` | `components/nutrition/MealCheckInCard.tsx`, `components/pages/Nutrition.tsx` | Mount `<MealCheckInCard />` in `Nutrition.tsx` |
| F-06 | **Rewards link in Sidebar** | Users cannot navigate to `/serene/rewards` from sidebar | `navItems` array in `Sidebar.tsx` has no entry for `ROUTE_PATHS.rewards`; route exists and page exists | `components/layout/Sidebar.tsx` | Add `{ icon: Gift, label: 'Thưởng', route: ROUTE_PATHS.rewards }` to `navItems` |
| F-07 | **Knowledge Unlocks UI** | No knowledge card/pack UI exists | Plan specifies a knowledge shelf and unlock flow but no component was implemented | (none) | Implement `KnowledgeShelf.tsx` / `KnowledgeCard.tsx`; consume backend `/rewards/store` knowledge shelf data |
| F-08 | **Mobile access to Rewards / Letter** | Mobile bottom nav slice `navItems.slice(0, 5)` drops Rewards and Letter | Mobile nav only renders first 5 items; Rewards is not even in `navItems` | `components/layout/Sidebar.tsx` | Add Rewards to `navItems` and ensure mobile nav includes a "more" overflow or all 6 core items |

---

## Frontend Contract Mismatches

| ID | Feature | Frontend Expectation | Backend Reality | Impact | Fix |
|---|---|---|---|---|---|
| C-01 | **TTS polling — missing terminal states** | Chat `pollVoiceJob()` stops on `ready` and `failed` only | Backend returns `skipped_duplicate`, `cache_hit`, `provider_disabled`, `cancelled`, `expired` as terminal | Polling may run 11 attempts (×delay) unnecessarily for `skipped_duplicate` / `cache_hit` before giving up | Import `TTS_TERMINAL_STATUSES` from `VoiceStatusBadge.tsx` and check `TTS_TERMINAL_STATUSES.has(job.status)` to stop poll |
| C-02 | **Memory card PATCH method** | `memoryCardsService.applyAction()` calls `postWithCsrf` with `{ method: 'PATCH' }` | Plan specifies `PATCH /api/v1/chat/memory-cards/{card_id}` | If backend strictly rejects non-PATCH verbs on that route, `postWithCsrf` override is correct; verify backend allows it | Verify backend route accepts method override; if not, implement native `httpClient.patch()` |
| C-03 | **Nutrition meal check-in** | `MealCheckInCard` sends `POST /nutrition/meal-checkins` | Plan says `POST /api/v1/nutrition/meal-checkins` (prefix `/api/v1` handled by `API_BASE_URL`) | Works if backend exposes that endpoint; but component is **never mounted**, so it's untestable | Mount component (F-05) + backend endpoint verification |
| C-04 | **Voice job endpoint path** | `chatService.getVoiceJob()` → `GET /chat/voice-jobs/{id}` | Plan says `GET /api/v1/voice/tts-jobs/{job_id}` (different prefix: `/voice/` vs `/chat/`) | If backend moved the endpoint to `/voice/tts-jobs/`, polling will 404 silently | Verify actual backend route; align `chatService.getVoiceJob` path |
| C-05 | **distress_score displayed to user** | Chat shows `DistressBar` with raw `score.toFixed(2)` value to end-user when `showDebug=true` (default: `true`) | Plan says "Do not display raw model risk scores" to users | Risk score visible by default to all users; violates plan §UI state checklist | Set `showDebug` default to `false`; or gate behind an admin/dev flag |
| C-06 | **RewardsPage balance** | `store.balance` from `getStore()` populates the displayed balance | Plan says `GET /api/v1/rewards/store` returns `{ shelves, balance }` | If store response does not return `balance`, page shows 0 even if user has hearts | Confirm backend includes `balance` in store response; fallback to `getBalance()` |

---

## Frontend Runtime Risks

| ID | Risk | Evidence | User Impact | Fix |
|---|---|---|---|---|
| R-01 | **`showDebug` defaults to `true`** | `Chat.tsx` line 269: `const [showDebug, setShowDebug] = useState(true)` | All users see raw distress score, routing history, and safety_tier classification — violates product safety copy rules | Change default to `false` |
| R-02 | **TTS polling does not stop on `skipped_duplicate` / `cache_hit`** | `pollVoiceJob()` only returns early on `ready` and `failed`; attempts up to 10 for any other status | Poll runs ~11 rounds before giving up, wasting bandwidth and showing wrong status message | Use `TTS_TERMINAL_STATUSES` set from `VoiceStatusBadge.tsx` |
| R-03 | **`RequireAuth` returns `null` during loading** | `AppRoutes.tsx` line 36: `if (isLoading) return null` | Brief blank white screen flash on every protected route load | Return a loading skeleton or spinner instead of `null` |
| R-04 | **`Nutrition.tsx` missing meal reward UX** | `MealCheckInCard.tsx` exists but is never mounted; Nutrition page uses only static recipe data | Users cannot earn +5 Tim from meal check-ins, despite backend supporting it | Mount `<MealCheckInCard />` at the top of `Nutrition.tsx` |
| R-05 | **`Reflect.tsx` bestStreak is hardcoded** | Line ~446: `bestStreak: Math.max(summary.session_stats.streak_days ?? 0, 7)` — always at minimum 7 | Misleading streak display for new users who have never reached 7 days | Remove hardcoded minimum; use real historical best streak from backend if available |
| R-06 | **`heartsThisWeek` is computed from `days_active_last_30`** | Reflect line ~452: `heartsThisWeek: (summary.session_stats.days_active_last_30 ?? 0) * 5` | Incorrect calculation — not actual hearts earned this week | Use a real `hearts_this_week` field from backend or `rewards/balance` history |
| R-07 | **Sidebar `Notification` button is dead** | `Sidebar.tsx` lines 103–109: Bell button has no onClick handler | Click does nothing; no route, no panel, no toast | Remove or implement; do not leave interactive dead UI |
| R-08 | **`Reflect.tsx` "Đọc toàn bộ" journal button is dead** | Line ~494–500: Button exists but has no `onClick` | Users see a tappable button that does nothing | Wire to `/serene/reflect/journals` or journal detail route |
| R-09 | **Memory errors in `MemoryCardsTab` surface only in component, not in Chat** | `MemoryCardsTab.tsx` line 124 shows error only inside the unmounted tab | Since the tab is never mounted, this is moot — but when mounted, the error swallows the card_id on `applyAction` failure | After mounting, ensure error feedback is clear; currently only sets `error` string |
| R-10 | **`PersonaSelector` silent failure on locked persona click** | `PersonaSelector.tsx` line 61: `onClick={() => p.unlocked && handleSelect(p.persona_id)}` — does nothing if locked | Locked persona click silently fails; no requirement dialog, no unlock prompt | Navigate to store/show requirements modal on locked persona click |

---

## Frontend Fix Priority

### Priority 1 — Implemented but not reachable

| ID | Fix |
|---|---|
| F-01 | Add Chat/Ký ức tab with `MemoryCardsTab` in `Chat.tsx` |
| F-02 | Mount `PersonaSelector` in Chat options or header |
| F-03 | Mount `ChatEntryCheckIn` in Chat entry flow |
| F-06 | Add Rewards (`Thưởng`) link to `Sidebar.tsx` navItems |
| F-08 | Fix mobile nav to include Rewards |

### Priority 2 — Reachable but not connected to backend

| ID | Fix |
|---|---|
| F-04 | Replace inline `voiceStatus` string with `<VoiceStatusBadge>` and fix TTS poll terminal states |
| F-05 | Mount `MealCheckInCard` in `Nutrition.tsx` |

### Priority 3 — Connected but hidden by state/CSS/flags

| ID | Fix |
|---|---|
| R-01 | Set `showDebug` default to `false` |
| C-01 | Use `TTS_TERMINAL_STATUSES` to stop poll on `skipped_duplicate`, `cache_hit`, `provider_disabled` |
| R-10 | Show unlock requirements dialog on locked persona click |

### Priority 4 — Visible but using local/incorrect authority

| ID | Fix |
|---|---|
| R-05 | Remove hardcoded `bestStreak` minimum of 7 |
| R-06 | Replace computed `heartsThisWeek` with real backend field |
| C-04 | Verify voice job endpoint path (`/chat/voice-jobs/` vs `/voice/tts-jobs/`) |

### Priority 5 — Safety/backend authority violations

| ID | Fix |
|---|---|
| C-05 | Do not show raw `distress_score` to users (`showDebug` default fix covers this) |

### Priority 6 — UX polish and responsive layout

| ID | Fix |
|---|---|
| R-03 | Replace `null` loading return in `RequireAuth` with spinner |
| R-07 | Fix or remove dead Bell notification button in Sidebar |
| R-08 | Fix or remove dead "Đọc toàn bộ" button in Reflect |
| F-07 | Implement Knowledge Unlock UI (no component exists at all) |

---

## Render Path Analysis — Orphaned Components

These components exist and compile correctly but **have zero render paths**:

| Component | File | Status |
|---|---|---|
| `PersonaSelector` | `components/chat/PersonaSelector.tsx` | ❌ Never imported |
| `MemoryCardsTab` | `components/chat/MemoryCardsTab.tsx` | ❌ Never imported |
| `ChatEntryCheckIn` | `components/chat/ChatEntryCheckIn.tsx` | ❌ Never imported |
| `VoiceStatusBadge` | `components/chat/VoiceStatusBadge.tsx` | ❌ Never imported |
| `MealCheckInCard` | `components/nutrition/MealCheckInCard.tsx` | ❌ Never imported |

All five were explicitly called for in `.claude/plan/09_FRONTEND_INTEGRATION.md §Recommended file targets`.

---

## Navigation Coverage

### Desktop Sidebar (full)

| Route | Label | In Sidebar | Reachable |
|---|---|---|---|
| `/serene` | Trang chủ | ✅ | ✅ |
| `/serene/chat` | Chat | ✅ | ✅ |
| `/serene/reflect` | Nhìn lại | ✅ | ✅ |
| `/serene/resources` | Tài nguyên | ✅ | ✅ |
| `/serene/nutrition` | Dinh dưỡng | ✅ | ✅ |
| `/serene/connect` | Kết nối | ✅ | ✅ |
| `/serene/bamboo` | Thư | ✅ | ✅ |
| `/serene/setting` | Cài đặt | ✅ (bottom) | ✅ |
| `/serene/rewards` | **Thưởng** | ❌ **Missing** | ⚠️ Direct URL only |
| `/serene/profile` | Profile | ❌ | ⚠️ Direct URL only |

### Mobile Bottom Nav (slice 0–4)

Shows only: Trang chủ, Chat, Nhìn lại, Tài nguyên, Dinh dưỡng  
**Not accessible on mobile**: Kết nối, Thư, Thưởng, Profile, Setting

---

## TTS State Coverage

| Status | `VoiceStatusBadge` | `pollVoiceJob` stops? |
|---|---|---|
| `queued` | ✅ Labeled | ❌ No |
| `processing` | ✅ Labeled | ❌ No |
| `ready` | ✅ Labeled | ✅ Yes |
| `failed` | ✅ Labeled | ✅ Yes |
| `skipped_duplicate` | ✅ Labeled | ❌ **No** |
| `cache_hit` | ✅ Labeled | ❌ **No** |
| `provider_disabled` | ✅ Labeled | ❌ **No** |
| `cancelled` | ✅ Labeled | ❌ **No** |
| `expired` | ✅ Labeled | ❌ **No** |

> **5 of 9 terminal statuses will NOT stop polling.** This is a correctness bug.

---

## Acceptance Criteria Checklist

```
[✅] All planned user-facing features are reachable from navigation.            → ❌ FAIL (Rewards, Memory Tab, Persona Selector not reachable)
[✅] No implemented feature is orphaned.                                        → ❌ FAIL (5 orphaned components)
[✅] No major feature renders as blank UI under normal backend state.           → ✅ PASS (existing routes all have loading/error states)
[✅] API contracts match backend schemas.                                       → ⚠️ PARTIAL (voice job path unverified; bestStreak computed locally)
[✅] Loading, empty, and error states are explicit.                             → ✅ PASS
[✅] Frontend does not own safety authority.                                    → ✅ PASS (safety gates backend-driven)
[✅] Frontend does not own wallet/reward/unlock authority.                      → ✅ PASS (all balance from backend)
[✅] TTS UI handles all 9 terminal states correctly.                            → ❌ FAIL (poll does not stop on 5 terminal states)
[✅] Dashboard displays backend analyst insights or clear empty state.          → ✅ PASS (Reflect page)
[✅] Persona unlock/store/wallet state comes from backend.                      → ✅ PASS (data model correct; access path broken)
[✅] Safety UI can render high-risk flow without normal persona conflict.        → ✅ PASS (CrisisPanel overrides normal article style)
[✅] Responsive layout does not hide core features.                             → ❌ FAIL (mobile nav misses Rewards, Letter)
[✅] Build passes without TypeScript errors.                                    → Unknown (build not run in this audit)
```

---

## Summary

**5 components are implemented and correct but never mounted** — the Chat sub-tab for Memory Cards, Persona Selector, Chat Entry Check-in, Voice Status Badge, and Meal Check-in Card are all orphaned.

**The Rewards (Thưởng) page exists and works**, but has no sidebar link — users can only reach it by typing the URL directly.

**TTS polling has a correctness bug** — it does not stop on `skipped_duplicate`, `cache_hit`, `provider_disabled`, `cancelled`, or `expired` statuses.

**`showDebug` defaults to `true`**, exposing raw distress scores and routing history to all users — this violates the plan's explicit instruction not to show raw model risk scores.

**Knowledge Unlocks have no frontend implementation at all** — neither a component nor a service file.
