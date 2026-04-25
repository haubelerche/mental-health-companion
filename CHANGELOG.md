# Changelog — Serene

> Format: [Keep a Changelog](https://keepachangelog.com) | Vingroup Engineering

---

## [Unreleased]

### Added
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
- `test_build_friend_context_includes_long_term_memory` updated to reflect tiered context semantics (split into 2 tests: tier2 and tier3)
- Chặn prompt-injection pattern trong retrieval context trước khi đưa vào prompt LLM
- Bổ sung review path cho trường hợp distress cao nhưng chưa chạm SOS hard gate

---

*No previous releases — initial changelog setup.*
