# Changelog — Serene

> Format: [Keep a Changelog](https://keepachangelog.com) | Vingroup Engineering

---

## [Unreleased] — Sprint 2 · 2026-04-25

### Added
- **Docker + Cloud Run deployment** — `backend/Dockerfile`, `frontend/Dockerfile`, `nginx.conf.template`, `docker-entrypoint.sh`, `cloudbuild.yaml`, `deploy.sh`, `setup_cloudrun.sh`, `.env.cloudrun.example` for full containerised GCP deploy.
- **Alembic migration 0002** — `memory_columns`: adds `mem0_user_id`, `long_term_summary` to user profile table.
- **Alembic migration 0003** — `counseling_knowledge`: vector-enabled knowledge table for hybrid RAG.
- **Alembic migration 0004** — `checkin_emotions`: adds `emotions` (JSON) + `triggers` (JSON) columns to `mood_checkins`.
- **`langfuse_tracing.py`** — `ChatTurnTracer` (ContextVar-based), wraps each turn in a Langfuse trace; fully no-ops when keys absent.
- **`confidence_router.py`** — routes high-distress non-SOS turns to human-review queue.
- **`output_grounding.py`** — post-flight grounding check blocks unsourced clinical claims before response is returned.
- **`counseling_retriever.py`** — hybrid vector + lexical retrieval with RRF fusion and rerank top-k; sanitizes chunks against indirect injection.
- **`mental_chat_retriever.py`** — sanitizes MentalChat retrieved chunks to block indirect prompt injection.
- **`mem0_service.py` + `memory_enrichment.py`** — Mem0 persistent user memory integration.
- **`cold_start_screener.py`** — PHQ-9/GAD-7 cold-start scoring for new users.
- **`chat_cost_metrics.py`** — token/cost telemetry; `GET /v1/admin/cost-dashboard` endpoint.
- **`outbox_worker.py`** — background worker that dispatches `SyncOutbox` events; started with `main.py`.
- **`hierarchical_agent_graph.py`** — scaffold for VinMec domain multi-agent split.
- **`exercise_catalog.py`** + `GET /v1/resources/exercises` — shared backend exercise contract for chat attachments.
- **`exerciseService.ts`** — frontend exercise catalog client with local offline fallback.
- **`CheckinFlow.tsx`** — Samsung Health-style 4-step mood check-in (Mood → Emotions → Triggers + Journal → Summary).
- **`ExercisesPage.tsx`** — breathing-pattern hub (box/equal/4-7-8/custom) + underwater exercise player with animated progress ring.
- **`Resources.tsx`** + `resourceService.ts` — sanctuary-style resource library with category pills, sleep stories, soundscapes, and agent deep-link support.
- **`Connect.tsx`** + `connectService.ts` — *You Are Not Alone* support UI with hotlines, clinic cards, and searchable Google Maps embed.
- **`PolicyWizard.tsx`** — 5-screen animated policy acknowledgment wizard shown post-signup.
- 9 new test files: `test_ragas_eval`, `test_redteam`, `test_voice_escalation`, `test_counseling_retriever`, `test_exercise_catalog`, `test_chat_context_token_guard`, `test_chat_memory_continuity`, updated `test_langgraph_chat`, `test_proactive_voice`.
- `DELETE /v1/auth/me/data` — cross-store user data deletion (DB + Mem0 + Redis).
- `PATCH /v1/admin/crisis-logs/{id}/review` — manual crisis log review endpoint.

### Changed
- `langgraph_chat.py`: 3-tier context builder reduces tokens ~40% at distress < 0.65; adds `_estimate_tokens_fast`, `_log_token_budget`, `correlation_id` tracing, grounding + cost observations.
- `CheckinFlow.tsx`: complete redesign — white frosted-glass shell, colour-coded emotion chips, journal step, summary step.
- `Chat.tsx`: renders `the_dinh_kem` attachments as clickable resource/exercise/clinic cards; normalises object-shaped quick replies; adds session history side-panel.
- `Reflect.tsx`: milestone chips row after Peace Score grid; journal prompts section (`GET /reflect/journal-prompts`).
- `Home.tsx`: removes safety gate from CTAs; connects POST /mood/checkin + GET /home/feed.
- `Sidebar.tsx` + `HeaderMain.tsx`: settings shortcut → profile shortcut; gear → down-chevron account menu.
- `Setting.tsx`: theme preview applies realtime via `APP_SETTINGS_UPDATED_EVENT`.
- `auth.py`: signup redirect goes to `/onboarding/policy` (PolicyWizard); handles `verification_required` 202.
- `chat.py`: high-risk non-SOS turn writes `CrisisLog` with `pending_review = true`.
- `main.py`: starts outbox worker thread alongside idle-session worker on startup.

### Fixed
- `chat.py` + `langgraph_chat.py`: load memory context once per turn, include memory for recall questions even at low distress, and skip cold-start profiling on short low-risk turns to reduce latency.
- `counseling_retriever.py`: indentation error in `try` block — `rows = db.execute(...)` was unindented.
- `outbox_worker.py`: marks dispatched events as `done` (was using invalid `processed` status).
- `Reflect.tsx`: no-data placeholder instead of empty Recharts container; removed unsafe `return` from `finally`.
- `HomeToday.tsx`: completed mood card contract (`apiMood`, `desc`) to fix TypeScript build.
- `Chat.tsx`: removed global toast container overlaying chat input.
- Proactive voice escalation uses final `SafetySnapshot.distress_score` — prevents missed Blaze TTS jobs.

### Removed
- `API_SET_UP_PROMPT.txt`, `BRANCHES_RULES.md` — superseded by updated CLAUDE.md + AGENTS.md.
- `docs/AI_TEST_COVERAGE_AND_GAP_REPORT.md`, `docs/BACKEND_PLAN.md` — replaced by live test suite + CHANGELOG.

---

### Added
- **Langfuse LLM observability** — `backend/app/services/langfuse_tracing.py`: optional `ChatTurnTracer` (ContextVar-based) that wraps each chat turn in a Langfuse trace with supervisor span, analyst/friend generations (model, token counts), distress score metric, and routing history. Completely no-ops when `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are absent.
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` added to `config.py` and `.env.example`.
- `langfuse>=2.0.0` added to `backend/requirements.txt`.
- `run_non_sos_turn()` and `stream_non_sos_turn_events()` now accept optional `user_id` / `session_id` for Langfuse user/session attribution; chat router passes them through.
- `backend/alembic/versions/0004_checkin_emotions.py` migration + `MoodCheckin` JSON columns (`emotions`, `triggers`) để lưu đầy đủ check-in cảm xúc/tác nhân.
- `CheckinQuickRequest` mở rộng `emotions` và `triggers` để nhận dữ liệu từ flow Mood check-in mới.
- Breathing catalog mở rộng với `box_breath`, `equal_breath`, `custom_breath` cho hub 2×2 trong trang bài thở.
- `exercise_catalog.py` + `GET /v1/resources/exercises` — shared backend exercise contract for browser-run exercises and chat attachments.
- `exerciseService.ts` — frontend exercise catalog client with local fallback for demo-safe browser exercise sessions.
- `Resources.tsx` — sanctuary-style resource library UI with local fallback cards, category pills, featured session, sleep stories, soundscapes, and clickable play actions.
- `Connect.tsx` — "You are not alone" support UI with hotline CTAs, clinic/referral cards, and map-style support panel.
- `Reflect.tsx`: milestone chips row (streak, breathing sessions, wellness, total sessions) rendered after Peace Score / mood chart grid; only shown when at least one milestone is earned
- `Reflect.tsx`: journal prompts section ("Gợi ý ghi chép hôm nay") fetched from `GET /reflect/journal-prompts`, rendered near page bottom, sliced to 3 prompts; fetch errors silently suppressed in production
- `ScreeningFlow` component (`frontend/src/components/pages/ScreeningFlow.tsx`) — PHQ-9 / GAD-7 instrument selection + question-by-question flow with animated progress bar; submits via `screeningService.submit()` and navigates to `/serene/results` with result state; falls back to static instrument list when catalog API unavailable
- Route `/serene/screening` added to `AppRoutes.tsx` under `RequireAuth`
- `PolicyWizard` component (`frontend/src/components/policy/PolicyWizard.tsx`) — 5-screen animated policy acknowledgment wizard shown post-signup; calls `policyService.acknowledge()` on final step and navigates to `/serene`
- Public route `/onboarding/policy` added to `AppRoutes.tsx` (outside `RequireAuth`)
- `Register.tsx`: redirect after successful signup now goes to `/onboarding/policy` (both verification-required and direct-login paths)
- `_estimate_tokens_fast()` — fast char-based token estimator (~2.5 chars/token for Vietnamese) in `langgraph_chat.py`
- `_log_token_budget(stage, *texts)` — debug-level token telemetry at `analyst_in`, `analyst_out`, `friend_in`, `friend_out`, `stream_friend_in` stages
- Tiered context builder: `_build_friend_context(state, distress_score)` now builds 3 tiers to reduce tokens sent to Friend model
- `output_grounding.py` — hậu kiểm grounding cho phản hồi để chặn claim lâm sàng không có nguồn
- `confidence_router.py` — confidence routing cho high-distress non-SOS và queue human review
- `chat_cost_metrics.py` + `GET /v1/admin/cost-dashboard` — theo dõi token/cost cho chat pipeline
- `outbox_worker.py` — worker loop xử lý `SyncOutbox` events nền
- `test_ragas_eval.py` — regression gate theo phong cách RAGAS
- `test_redteam.py` — bộ test red-team prompt injection/jailbreak/slang self-harm
- `hierarchical_agent_graph.py` — scaffold kiến trúc hierarchical multi-agent cho VinMec domain split
- Frontend services mới: `homeService.ts`, `resourceService.ts`, `connectService.ts`

### Changed
- `Sidebar.tsx` + `HeaderMain.tsx`: replace the left-bottom settings shortcut with a profile shortcut and change the top-right gear into a down-chevron account menu limited to login, password reset, and logout actions.
- `CheckinFlow.tsx`: redesign hoàn chỉnh theo mẫu Samsung Health (Mood → Emotions → Triggers + Journal → Summary), đổi shell/card sang nền trắng đục glass đồng bộ web app, chips bo tròn có màu chọn theo nhóm cảm xúc, lưu dữ liệu vào `/checkin/quick`.
- `ExercisesPage.tsx`: thêm hub chọn bài thở trước khi vào player và hỗ trợ pattern có pha giữ thứ hai (`4-4-4-4`).
- `checkin.py`: persist `emotions` và `triggers` lên `mood_checkins` khi tạo/cập nhật quick check-in.
- `Setting.tsx`: chọn theme áp dụng preview realtime qua `APP_SETTINGS_UPDATED_EVENT`, hủy thay đổi sẽ trả lại theme đã lưu.
- `Home.tsx`: bỏ safety gate cho các CTA chính, nối trực tiếp tới route mục tiêu và wire đầy đủ quick cards/forest CTA.
- `ExercisesPage.tsx`: replaces static step cards with a working underwater exercise player, timer, progress bar, phase animation, and URL-driven exercise selection.
- `Chat.tsx`: renders agent attachments as clickable resource/exercise cards using `action`/`route` from backend payloads.
- `langgraph_chat.py`: standardizes `the_dinh_kem` attachment payloads and adds sanitized agent suggestions for clinic maps plus sleep/meditation resources.
- `Connect.tsx`: replaces the static map illustration with a searchable Google Maps embed that accepts agent-provided address/query routes.
- `Resources.tsx` + `resourceService.ts`: support agent deep links into resource categories/search, including a fallback sleep meditation video card.
- `Sidebar.tsx`: aligns navigation labels and bottom actions with the visual references.
- `AuthContext`: splits context value into `authContextValue.ts` so frontend lint/Fast Refresh rules pass.
- Frontend page labels now use `Nhìn Lại`, `Thư Viện`, and `Kết Nối` across sidebar navigation, page headings, onboarding copy, and related result CTAs.
- `_build_friend_context`: refactored from flat full-context to 3 tiers based on distress level
  - Tier 2 (0.42 ≤ distress < 0.65): 3-turn transcript + mood + tone + analyst note (~40% fewer tokens vs old flat context)
  - Tier 3 (distress ≥ 0.65): full context unchanged (6 turns + mem0 + long-term + profile + trajectory)
  - Tier 1 (distress < 0.42, short msg): unchanged — `_build_personality_hint` via caller
- `friend_node`, `stream_non_sos_turn_events`: pass `distress_score` explicitly to `_build_friend_context`
- `langgraph_chat.py`: thêm `correlation_id`, structured tracing span-level, grounding integration, usage-cost observation
- `counseling_retriever.py`: nâng lên hybrid vector + lexical retrieval, RRF fusion, rerank top-k, sanitize retrieved chunks
- `mental_chat_retriever.py`: sanitize retrieved chunks chống indirect injection
- `chat.py`: high-risk non-SOS flow sẽ ghi `CrisisLog` pending review và trả cờ `pending_human_review`
- `admin.py`: thêm `PATCH /v1/admin/crisis-logs/{log_id}/review`
- `main.py`: khởi chạy outbox worker thread cùng idle session worker
- `auth.py`: thêm `DELETE /v1/auth/me/data` (xóa user data cross-store + Mem0/Redis)
- `seed_counseling_knowledge.py`: idempotency theo content hash, quarantine log cho low-quality rows, freshness source tag
- Frontend:
  - `Home.tsx` nối `POST /mood/checkin` và `GET /home/feed`
  - `Resources.tsx` nối categories/list APIs
  - `Connect.tsx` nối hotlines/clinics APIs
  - `Chat.tsx` thêm history panel + load sessions/messages
  - `Register.tsx` xử lý signup `verification_required` (202) thay vì luôn navigate vào app
  - `chatService.ts` mở rộng sessions/messages/delete APIs
  - `authService.ts` mở rộng type cho flow email verification

### Fixed
- Local DB 500s on `/v1/home/feed` and `/v1/reflect/*` resolved by applying `0004_checkin_emotions` so `mood_checkins.emotions` and `mood_checkins.triggers` exist.
- `outbox_worker.py`: mark dispatched events as `done` instead of invalid `processed` status, matching the `sync_outbox` DB constraint.
- `Reflect.tsx`: render a no-data placeholder instead of mounting Recharts with an empty/invalid container, preventing width/height warnings.
- `HomeToday.tsx`: complete the mood card contract (`apiMood`, `desc`) so TypeScript build passes.
- `App.tsx`: remove the global toast container so bottom notification bars no longer overlay the chat input.
- `HeaderMain.tsx`: bỏ mục `Cài đặt` trùng trong dropdown của icon settings.
- `Sidebar.tsx`: bỏ nút standalone `Journal Now` vì journal đã tích hợp trực tiếp trong check-in flow.
- `Setting.tsx`: removes leftover debug logging from settings save flow.
- `Chat.tsx`: normalize object-shaped quick replies before rendering, preventing React from crashing on `{type, reason, message}` payloads.
- `Reflect.tsx`: remove unsafe `return` from `finally` in the data-loading effect.
- Proactive voice escalation now uses the final `SafetySnapshot.distress_score` after graph/cold-start scoring, preventing missed Blaze TTS jobs when distress is raised during non-SOS processing.
- `test_build_friend_context_includes_long_term_memory` updated to reflect tiered context semantics (split into 2 tests: tier2 and tier3)
- Chặn prompt-injection pattern trong retrieval context trước khi đưa vào prompt LLM
- Bổ sung review path cho trường hợp distress cao nhưng chưa chạm SOS hard gate

---

*No previous releases — initial changelog setup.*
