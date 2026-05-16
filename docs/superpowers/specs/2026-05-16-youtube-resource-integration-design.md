# YouTube Resource Integration — Design Spec

**Date:** 2026-05-16  
**Author:** haubelerche  
**Status:** Approved  
**Branch:** feat/greetings-screening-results

---

## Problem Statement

The Resource page already shows videos crawled manually by admins via `youtube_agent.py`. Two gaps remain:

1. Content goes stale unless admin triggers a crawl manually.
2. FriendNode never suggests videos in chat, even when user clearly needs them.

## Goals

1. Auto-refresh YouTube content per category on a weekly schedule (no admin action needed).
2. Show a personalized "Dành cho bạn hôm nay" section on the Resource page based on user mood/emotion.
3. FriendNode proactively suggests relevant videos in chat using natural language + attachment card.

## Non-Goals

- Real-time YouTube search during chat (quota cost, latency).
- Removing or bypassing SafetyGate (architecture invariant — stays as-is).
- Frontend-owned safety, reward, or wallet logic.

---

## Architecture Overview

Three independent layers, each with a clear boundary:

```
Layer 1: Content Refresh (Cron)
  APScheduler → run_youtube_crawl_agent per category
  → Resource DB (existing)

Layer 2: Resource Page Personalization
  GET /api/v1/resources/for-you
  → query mood + AnalystBundle dominant_emotions
  → map to categories → fetch top-N from DB

Layer 3: FriendNode Video Hints (Chat)
  distress_score ≥ 0.35 → resource_candidates_provider pulls from DB
  → ContextPack.resource_candidates → FriendNode LLM decides
  → used_resource_ids → AttachmentCard (existing)
  fallback: YouTube API search if DB empty for category
```

Architecture invariants preserved:
- SafetyGate runs before FriendNode (unchanged).
- FriendNode is the only normal-turn LLM caller.
- Resource logic is a Service, not an agent.
- PostgreSQL is source of truth; no Neo4j writes.

---

## Layer 1: Cron Job Content Refresh

### Scheduler

- **Library:** `APScheduler` (add to `backend/requirements.txt`).
- **Lifecycle:** Start/stop inside FastAPI lifespan context (`app/main.py`).
- **Schedule:** Each of the 6 categories runs once per week, staggered 1 hour apart to avoid quota bursts.
- **Guard:** Skip category if DB already has `≥ YOUTUBE_MIN_VIDEOS_PER_CATEGORY` active videos. Only crawl when below threshold.

### New Config (backend/app/core/config.py + .env.example)

```
YOUTUBE_CRON_ENABLED=true          # bool, default true
YOUTUBE_MIN_VIDEOS_PER_CATEGORY=10 # int, default 10
```

### Quota Estimate

6 categories × 3 keywords × 5 results + 1 details call ≈ 18 search units + 6 detail units = ~24 units/week. Well within 10,000/day default.

### Error Handling

- Log failures per category, continue to next category.
- Do not raise to FastAPI request context (background task).
- Retry logic: none (will retry next scheduled run).

---

## Layer 2: Resource Page Personalization

### Backend

**New endpoint:** `GET /api/v1/resources/for-you`  
**Auth:** Required (JWT, same as other resource endpoints).  
**Response:**

```json
{
  "items": [ResourceItem, ...],   // max 5
  "reason": "Dựa trên tâm trạng gần đây của bạn"
}
```

**Logic:**

1. Fetch user's latest mood entry (past 24h) from DB.
2. Fetch `dominant_emotions` from latest `AnalystBundle` snapshot (if available).
3. Map emotion/mood → category using deterministic table (no LLM):

| Mood/Emotion signal | Category |
|---|---|
| buồn, thất vọng, khóc | meditate, wisdom |
| lo, overthinking, bất an | meditate, wisdom |
| mệt, kiệt sức, burnout | sleep, movement |
| tức, bực | movement, music |
| mất ngủ | sleep |
| cô đơn | music, wisdom |
| default (no data) | meditate |

4. Query `Resource` table: `category IN [mapped_categories] AND is_active=true`, order by `RANDOM()`, limit 5.
5. Fallback: if no results → return top 5 `meditate` resources.

**New router file:** `backend/app/api/v1/routers/resource_personalization.py`  
**New service function:** `backend/app/services/resource_service.py::get_for_you(user_id, db)`

### Frontend

- New section in `Resources.tsx` above category tabs: `ForYouSection` component.
- Fetch on mount via `resourceService.getForYou()`.
- Renders max 3 cards horizontally (same `ResourceGrid` card style).
- If fetch errors or returns empty → render nothing (no empty state UI).
- Uses existing `YouTubeEmbed` modal when card clicked.

---

## Layer 3: FriendNode Video Hints in Chat

### resource_candidates_provider

Currently returns `[]`. Implement in `chat_orchestrator.py`:

1. Read `distress_score` from `SafetyPolicyDecision` (already in `ContextPack.safety_policy`).
2. If `distress_score ≥ 0.35`:
   a. Determine candidate category from current turn topic (simple keyword map, same as Layer 2 table).
   b. Query DB: top-3 active videos in that category, ordered by `RANDOM()`.
   c. If DB returns 0 results for that category → call YouTube API search (3 results, not saved to DB).
3. Return list of `{"resource_id", "title", "url", "thumbnail_key", "why_candidates": "..."}` dicts.
4. If `distress_score < 0.35` → return `[]` (no candidates, FriendNode never sees them).

### FriendNode Prompt Addition

Add to system prompt block (in `friend_agent.py`):

```
Nếu resource_candidates có video phù hợp với tình huống hiện tại của người dùng,
hãy đề cập tự nhiên trong final_text (ví dụ: "Mình thấy video này có thể giúp..."),
và đặt resource_id tương ứng vào used_resource_ids.
Không bắt buộc phải gợi ý — chỉ gợi ý khi thực sự phù hợp.
```

FriendNode retains full autonomy — the LLM decides whether to suggest or not.

### Chat Response → AttachmentCard

- Existing `_attachments_from_context_pack` in `chat_orchestrator.py` already converts `used_resource_ids` → `resource_suggestions` in API response.
- Frontend `AttachmentCard` already renders these.
- **One addition:** FriendNode's `final_text` already contains the natural language mention. The card appears below as the visual anchor. No new frontend component needed.

### Fallback YouTube API Call

- Use existing `httpx` client (no new dependency).
- Search query: `{category_context} tiếng Việt sức khỏe tâm thần` (same pattern as `youtube_agent.py`).
- Results are returned directly as candidates, **not saved to DB** (unmoderated, for chat only).
- If YouTube API call fails → return `[]`, FriendNode proceeds without candidates (graceful degradation).

---

## Data Flow Summary

```
User message
  → SafetyGate (distress_score computed)
  → context_pack_builder.build()
      → resource_candidates_provider(distress_score, topic)
          → DB query OR YouTube API fallback
  → FriendNode(ContextPack)
      → LLM writes final_text + used_resource_ids
  → chat_orchestrator._attachments_from_context_pack()
      → resource_suggestions in API response
  → Frontend: text bubble + AttachmentCard
```

---

## Files Changed

| File | Change |
|---|---|
| `backend/requirements.txt` | Add `APScheduler` |
| `backend/app/core/config.py` | Add `YOUTUBE_CRON_ENABLED`, `YOUTUBE_MIN_VIDEOS_PER_CATEGORY` |
| `backend/.env.example` | Add new env vars |
| `backend/app/main.py` | Wire APScheduler lifespan |
| `backend/app/services/youtube_scheduler.py` | **New** — cron job logic |
| `backend/app/services/resource_service.py` | Add `get_for_you()` function |
| `backend/app/api/v1/routers/resource_personalization.py` | **New** — `/resources/for-you` endpoint |
| `backend/app/api/v1/router.py` | Register new router |
| `backend/app/services/chat_orchestrator.py` | Implement `resource_candidates_provider` |
| `backend/app/services/friend_agent.py` | Add video hint instruction to system prompt |
| `frontend/src/services/resourceService.ts` | Add `getForYou()` method |
| `frontend/src/components/pages/resource/ForYouSection.tsx` | **New** — personalized section component |
| `frontend/src/components/pages/resource/Resources.tsx` | Mount `ForYouSection` above tabs |

---

## Testing

| Test | Command |
|---|---|
| Backend unit tests | `pytest backend/tests -q` |
| Frontend lint | `npm --prefix frontend run lint` |
| Frontend build (tsc) | `npm --prefix frontend run build` |
| Manual smoke | `npm --prefix frontend run dev` → Resource page → verify ForYouSection |

New backend tests needed:
- `test_resource_personalization.py`: happy path (mood data exists), no-mood fallback, empty-DB fallback.
- `test_youtube_scheduler.py`: skip-if-enough, crawl-if-below-threshold.
- `test_resource_candidates_provider.py`: distress ≥ 0.35 returns candidates, distress < 0.35 returns [].
