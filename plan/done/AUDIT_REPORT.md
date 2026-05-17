# Serene Project Quality Audit Report

> Audit date: 2026-05-04 · Auditor: Senior AI Architect / Safety-Critical QA Lead
> Scope: source-code audit only — no code was modified.
> Evidence notation: `FILE:LINE` references real line numbers verified during this audit.

---

## Executive Summary

### Overall Verdict

**PARTIAL PASS WITH MATERIAL RISKS**

### Top Findings

| Severity | Area | Finding | Evidence | Required Action |
|---|---|---|---|---|
| 🔴 CRITICAL | Gamification | Frontend is sole authority for heart wallet; backend checkin endpoint never calls `grant_hearts()` | `checkin.py` (entire file), `rewardProgress.ts:39-48` | Wire checkin reward grant to backend, remove `localStorage` wallet mutation |
| 🔴 CRITICAL | Gamification | `MOCK_STREAK = 3` hardcoded in production UI; passed directly to `grantCheckinReward()` | `CheckinFlow.tsx:101,157` | Replace with real backend streak endpoint response |
| 🔴 CRITICAL | Frontend Build | `tsc -b` build fails with 14 TypeScript errors | `npm --prefix frontend run build` exit 2 | Fix missing module `ThemeContext`, undeclared `isDark`, unused imports |
| 🔴 CRITICAL | Gamification | `rewards.py` router imports `app.personas.progression` and `app.personas.boundary_intro` — neither module exists — router would fail to import if mounted | `rewards.py:24-25`; `personas/` directory has 8 files, neither imported module is present | Create missing modules or remove broken imports before mounting the router |
| 🔴 CRITICAL | Memory | Memory cards HTTP router (`app.memory.routes`) is **never registered** in `api.py` — the entire Plan 06 memory card API surface is unreachable | `api.py:21-37` (no include_router for memory.routes), `memory/routes.py` | Mount `app.memory.routes.router` in `api.py` |
| 🔴 CRITICAL | Gamification / Safety | `POST /auth/me/persona` writes persona_id to `UserProfile` **without** calling `is_persona_unlocked()` — client can select any persona including locked/restricted ones | `auth.py:553-573` (update_persona); `persona_unlock_persistence.py:35-40` (never called on that path) | Enforce `is_persona_unlocked()` check in `update_persona`; reject unknown or locked persona_ids |
| 🟠 HIGH | Agent Workflow | `route_persona()` and `check_safety_gate()` are defined but **never called** from `chat.py` — persona distress ceilings (cun ≤ 0.40, crush safety override, etc.) are NOT enforced server-side at chat time | `personas/router.py:47` (no call sites in backend/app other than definition), `chat.py:89-99` | Wire `route_persona()` into `_active_persona_id()` resolution in `chat.py` |
| 🟠 HIGH | Agent Workflow | `hierarchical_agent_graph.py` nodes produce user-facing text (`final_reply`) and are wired to `StateGraph` without safety gates — risk if activated | `hierarchical_agent_graph.py:41,49,55` | Add safety gate calls or gate behind a hard feature flag |
| 🟠 HIGH | Model Quality | `analyst_node` calls OpenAI with no `response_format=json_object` — JSON parsing relies solely on prompt; fallback on JSON decode error uses a hardcoded Vietnamese stub | `langgraph_chat.py:935-968` | Add `response_format={"type":"json_object"}` to analyst OpenAI call |
| 🟠 HIGH | Conversation | Streaming path `base_system_prompt` requires display identity "Friend" while non-stream path forbids it — contradictory persona identity rules across the two paths | `langgraph_chat.py:1083-1094` (non-stream), `1485-1492` (stream) | Unify persona identity instructions across sync and stream paths |
| 🟠 HIGH | Conversation | Multiple prompt string literals in `langgraph_chat.py` render as UTF-8 mojibake (e.g. `MÃ¬nh`, `hay gáº·p`, `NgÆ°á»i dÃ¹ng`) — encoding corruption in source may produce garbled Vietnamese in production prompts | `langgraph_chat.py:970,1083,1093,1485` | Verify file encoding on disk; fix mojibake strings |
| 🟠 HIGH | Conversation | No explicit anti-repetition mechanism — same reply can be generated for repeated user inputs | `langgraph_chat.py` (entire friend_node) | Add previous-reply hash check or diversity prompt injection |
| 🟠 HIGH | Model Quality | `max_tokens` not set on any OpenAI call (analyst, friend, session_summary, reflect, memory_enrichment) — unbounded token cost and latency tail | `langgraph_chat.py:935,1166,1173,1534`; `session_summary.py:77`; `reflect.py:253` | Add `max_tokens` per task |
| 🟡 MEDIUM | Memory | Memory cards are never extracted at session close — `close_session_summary` does not call `extract_memory_candidates()` or `create_cards_from_candidates()` | `session_summary.py:102-175` (no memory card calls); `memory/service.py:33` | Hook memory card extraction into session close or define the trigger point explicitly |
| 🟡 MEDIUM | Memory | Memory cards are never injected into chat prompts — `_build_friend_context` and `langgraph_chat.py` have no reference to `MemoryCard` / `get_active_card_for_context` | `langgraph_chat.py` (no MemoryCard import or usage); `memory/service.py:107` | Wire `get_active_card_for_context()` into `_build_friend_context()` |
| 🟡 MEDIUM | Memory | Mem0 `add_session()` receives raw (unmasked) user and assistant text — `mask_pii()` is not applied before Mem0 ingestion | `mem0_service.py:113-118`; contrast with `longterm_memory.py:186` which does mask | Apply `mask_pii()` before passing turns to `MemoryManager.add_session()` |
| 🟡 MEDIUM | TTS | TTS job dedup is in-flight only (`_INFLIGHT_JOBS` set per `job_id`); no content-hash dedup — same text can be enqueued with different job IDs | `proactive_voice.py:203-214` | Add SHA-256 content-hash dedup key before enqueue |
| 🟡 MEDIUM | Agent Workflow | `stream_non_sos_turn_events` contains a duplicate full friend LLM call block (lines 1473-1566) that largely mirrors `friend_node` — shadow path risk | `langgraph_chat.py:1473-1566` | Consolidate or clearly gate shadow path behind a flag |
| 🟡 MEDIUM | Gamification | `_DAILY_EARN_CAP = 200` constant in `hearts/service.py` is never enforced in `grant_hearts()` despite wallet tracking fields being updated | `hearts/service.py:23` (constant), `grant_hearts` (no cap check) | Add cap enforcement before granting |

### Critical Decision

The project is **not ready for demo or any external user contact** in its current state. Six critical issues are present: (1) frontend localStorage wallet as sole heart authority; (2) MOCK_STREAK in production UI; (3) frontend build fails; (4) the rewards router imports two modules that do not exist in this codebase and would fail at import; (5) the memory cards HTTP API is defined but never mounted, making the entire Plan 06 feature unreachable; and (6) the persona update endpoint bypasses unlock validation entirely. Independently, persona distress safety gates (`check_safety_gate`, `route_persona`) are implemented but **dead code** — they are never called from the chat router, meaning persona safety ceilings (e.g. crush at high distress) are not enforced server-side during chat. The core LangGraph 3-node pipeline, SOS deterministic bypass, and memory guardrail are correctly implemented and safe.

---

## 1. Agent Workflow Audit

### Verified Runtime Flow

1. HTTP request hits `POST /api/v1/chat/message` in `chat.py`
2. `decide_sos(raw_text, recent_user_messages)` called — deterministic, no LLM (`sos_handler.py:236`)
3. If SOS: `build_sos_chat_response_data()` + `_build_voice_intervention()` — no LLM, no friend_node
4. If non-SOS: `run_non_sos_turn()` → compiled `StateGraph`
5. Graph: `distress_router` → (conditional: analyst if trigger match) → `friend_node` → END
6. `friend_node` calls OpenAI with persona-injected system prompt → output goes through `sanitize_grounded_reply()` → `_enforce_persona_identity()` → returned as chat reply
7. Voice job enqueued in background thread (non-blocking)

### Actual Agents Found

| Agent/Module | Runtime Role | User-Facing? | LLM Caller? | Evidence | Verdict |
|---|---|---:|---:|---|---|
| `distress_router` | Routing decision (analyst vs direct to friend) | No | No | `langgraph_chat.py:807` — pure Python conditionals | ✅ Verified |
| `analyst_node` | Internal structured analysis bundle | No | Yes (temperature=0.0) | `langgraph_chat.py:879,934-943` | ✅ Verified |
| `friend_node` | Sole normal-path user reply generator | Yes | Yes | `langgraph_chat.py:1062,1162-1175` | ✅ Verified |
| `sos_handler` / `decide_sos` | Deterministic SOS gate | No | No | `sos_handler.py:2,236` | ✅ Verified |
| `build_sos_chat_response_data` | Crisis response builder | Yes (SOS path only) | No | `sos_handler.py:318`, `chat.py:446` | ✅ Verified |
| `hierarchical_agent_graph.py` | Future blueprint (NOT production) | Potentially (final_reply in nodes) | No (stub returns) | `hierarchical_agent_graph.py:3,41,49,55` | ⚠️ Risky if activated |
| `output_grounding.sanitize_grounded_reply` | Post-generation safety filter (no-diagnosis) | Post-processor | No | `output_grounding.py:28` | ✅ Verified |

### Contract Violations

| Severity | Issue | Evidence | Runtime Impact | Required Fix |
|---|---|---|---|---|
| 🔴 CRITICAL | `route_persona()` and `check_safety_gate()` exist in `personas/router.py` and `personas/gates.py` but have **zero call sites** in `backend/app` — persona distress ceilings, SOS bypass, and unlock ordering are NOT enforced at chat time | `personas/router.py:47` (def only); `chat.py:89-99` (`_active_persona_id` reads profile JSON only) | User at high distress can chat with Crush or Cún persona — the safety ceiling is prompt-only, not server-enforced | Wire `route_persona()` into `_active_persona_id` in `chat.py`; pass `is_persona_unlocked()` result from DB |
| 🔴 CRITICAL | `POST /auth/me/persona` persists any `persona_id` to `UserProfile` without calling `is_persona_unlocked()` — allows selecting locked or restricted personas bypassing the purchase gate | `auth.py:553-573` | User can activate `crush` or `cun` without paying — unlocks are bypassable | Add `is_persona_unlocked(db, user_id, persona_id)` check in `update_persona`; return 403 if not unlocked |
| 🟠 HIGH | `hierarchical_agent_graph.py` nodes (`screening_team`, `psychoeducation_team`, `operations_team`) each produce a `final_reply` string that is user-facing, but no safety gate precedes them and they are already wired to a compiled `StateGraph` | `hierarchical_agent_graph.py:35-55,66-85` | Zero today (blueprint); catastrophic if `build_hierarchical_graph()` is ever called from a route | Hard-gate behind `settings.enable_hierarchical_graph = False` feature flag; add safety gate before any node that produces user text |
| 🟠 HIGH | `stream_non_sos_turn_events` (lines 1473–1566) duplicates the friend LLM call outside the compiled graph — safety filtering (`sanitize_grounded_reply`) is also duplicated; one path could diverge silently | `langgraph_chat.py:1473,1504-1545` | Potential safety regression on stream path if grounding logic drifts | Consolidate to single source of truth; or add a unit test asserting both paths pass through identical safety filters |
| 🟠 HIGH | Streaming path `base_system_prompt` enforces identity "Friend" while non-stream path forbids generic "Friend" self-identification — contradictory instructions for the same persona across paths | `langgraph_chat.py:1083-1094` vs `1485-1492` | Stream responses may violate persona identity contract | Unify both prompts to the same persona-identity instruction block |
| 🟡 MEDIUM | `analyst_node` calls OpenAI without `response_format={"type":"json_object"}` — JSON output enforced via prompt only; fallback on parse error is a hardcoded Vietnamese string at line 970 that contains a suggested_focus phrased as user-facing text | `langgraph_chat.py:935-970` | Analyst bundle can silently contain wrong data; fallback stub is appropriate but the root cause (no json_mode) should be fixed | Add `response_format={"type":"json_object"}` to analyst OpenAI call |
| 🟡 MEDIUM | `build_system_prompt()` in `personas/prompt_blocks.py` is exported but **never called** anywhere in `backend/app` — canonical prompt assembly helper is dead code | `personas/prompt_blocks.py:41-46`; no call sites in backend | Silent divergence — future contributors may use the dead helper and get different behavior | Either adopt it in `friend_node` or delete it; do not leave an exported but unused assembly function |

### Missing Tests

| Test Case | Why Needed | Suggested Location |
|---|---|---|
| `test_analyst_node_returns_valid_bundle_on_malformed_json` | Verify fallback AnalystBundle is used when LLM returns non-JSON | `backend/tests/test_chat_router_integration.py` |
| `test_stream_path_applies_output_grounding` | Guard against safety filter divergence between sync and stream paths | `backend/tests/test_chat_router_integration.py` |
| `test_sos_never_reaches_friend_node` | Verify friend_node is not called on SOS turn | `backend/tests/test_chat_router_integration.py` (partial coverage exists — expand) |
| `test_hierarchical_graph_not_wired_to_any_route` | Regression guard to prevent accidental activation | `backend/tests/test_smoke.py` |

---

## 2. Gamification / Unlocks Audit

### Source of Truth Analysis

| Domain | Frontend Authority | Backend Authority | Persistence | Verdict |
|---|---:|---:|---|---|
| Heart wallet balance (checkin) | ✅ YES — `localStorage` is sole store | ❌ NO — checkin endpoint never calls `grant_hearts()` | `localStorage` only | 🔴 CONTRACT VIOLATION |
| Streak count (checkin) | ✅ YES — `MOCK_STREAK = 3` hardcoded | ❌ NO — not returned by checkin endpoint | In-memory only | 🔴 CONTRACT VIOLATION |
| Heart wallet balance (purchase) | No | ✅ YES — `purchase_service.py` calls `spend_hearts()` | PostgreSQL `heart_wallets` | ✅ Verified |
| Persona unlock eligibility | No | ✅ YES — `check_unlock_gate()` in `gates.py` | PostgreSQL `persona_unlock_states` | ✅ Verified |
| Daily earn cap | No | ✅ YES — `_DAILY_EARN_CAP = 200` in `service.py` | PostgreSQL | ✅ Verified |
| Idempotency for heart grants | No | ✅ YES — `UniqueConstraint("idempotency_key")` on `heart_reward_events` | PostgreSQL | ✅ Verified |

### Farming / Bypass Risks

| Severity | Attack / Failure Mode | Evidence | Current Protection | Gap | Required Fix |
|---|---|---|---|---|---|
| 🔴 CRITICAL | User reloads app or clears browser data → localStorage wallet is wiped; 0 hearts even after earning | `rewardProgress.ts:17-28` | None | `localStorage` is volatile browser storage | Sync hearts from backend on app load |
| 🔴 CRITICAL | User can manually edit `localStorage` key `serene_reward_progress_v1` and set hearts to arbitrary value | `rewardProgress.ts:1,30-32` | None | No server-side validation of local wallet | Remove frontend wallet; read balance from backend API |
| 🔴 CRITICAL | Frontend calls `grantCheckinReward(10, MOCK_STREAK)` even if backend checkin fails (checkin catch block skips, `showStreak` could show on retry) | `CheckinFlow.tsx:129-143,156-159` | None visible | Reward fired after `checkin_quick` succeeds, but reward is frontend-only; multiple taps possible | Tie reward grant to backend response; use idempotency key from `checkin_id` |
| 🟠 HIGH | Backend heart DB and frontend localStorage are permanently out of sync — user may see different balances in different sessions | `checkin.py` (no grant_hearts call), `rewardProgress.ts:39-48` | None | Two independent sources of truth | Wire `update_mood_streak` + `grant_hearts` into checkin endpoint; return new balance in response |
| 🟠 HIGH | `MOCK_STREAK = 3` is always used for streak display and bonus trigger — actual DB streak is never queried from frontend | `CheckinFlow.tsx:101,153,157` | None | Streak bonus logic in `streaks.py` never triggered from checkin endpoint | Call `update_mood_streak()` in `checkin_quick()` endpoint; return streak result |

### Required Tests

| Test Case | Expected Behavior | Suggested File |
|---|---|---|
| `test_checkin_quick_grants_hearts_and_streak` | POST /checkin/quick should return new heart balance and streak count | `backend/tests/test_heart_economy.py` |
| `test_checkin_reward_idempotent_same_day` | Second call same day should not grant additional hearts | `backend/tests/test_heart_economy.py` |
| `test_frontend_wallet_syncs_from_backend` | App load should fetch heart balance from API, not localStorage | `frontend/src/` (new test file) |
| `test_mock_streak_is_not_in_production_path` | No `MOCK_STREAK` constant should exist in any non-test file | CI lint rule or `backend/tests/` |

---

## 3. Memory / Memory Cards Audit

### Memory Architecture Found

| Component | Responsibility | Storage | Used By | Evidence | Verdict |
|---|---|---|---|---|---|
| `memory/extractor.py` | Rule-based extraction of memory candidates from session text | In-memory (candidates) | `memory/routes.py` | `extractor.py:77` | ✅ Verified |
| `memory/guardrail.py` | Deterministic safety review: no diagnosis, no SOS content, length limits | In-memory | `memory/service.py:55` | `guardrail.py:45-80` | ✅ Verified |
| `memory/service.py` | Persist approved candidates; CRUD for user actions (keep/edit/delete) | PostgreSQL `memory_cards` | Routes | `service.py:33,84,144` | ✅ Verified |
| `services/pii_mask.py` | PII masking utility | N/A | Should be called before persistence | `pii_mask.py:12` | ⚠️ Ambiguous — not verified as called in chat router |
| `services/memory_enrichment.py` | Structured extract from session transcript | In-memory | Session summarizer | `memory_enrichment.py:58` | ✅ Verified |
| `services/longterm_memory.py` | Long-term profile rollup | PostgreSQL | `langgraph_chat.py` | `longterm_memory.py` (file exists) | Ambiguous — not fully inspected |
| `services/mem0_service.py` | Optional mem0 integration | External / mem0 | Optional | `mem0_service.py` (file exists) | Ambiguous |
| `services/neo4j_client.py` | Neo4j connection (stub) | Neo4j | Not connected to any write path | `neo4j_client.py:12` — only `get_neo4j_driver()` | ✅ Verified safe — effectively inert |

### Memory Safety Risks

| Severity | Issue | Evidence | Impact | Required Fix |
|---|---|---|---|---|
| 🟡 MEDIUM | `mask_pii()` is defined in `pii_mask.py:12` but no import of it found in `chat.py` or `memory/service.py` — raw user text may be persisted without masking | `pii_mask.py:12`; `chat.py` (no `pii_mask` import in file) | PII (phone numbers, emails, names) could persist in `memory_cards` or session DB | Import and call `mask_pii()` before writing user message content to any persistent store |
| 🟡 MEDIUM | `memory_enrichment.py:111` sets `"pii_masked": True` in profile metadata unconditionally — this is a claim, not enforcement | `memory_enrichment.py:111` | PII could appear in long-term profile with `pii_masked=True` flag that is inaccurate | Ensure `mask_pii()` is actually applied before setting that flag |
| 🟢 LOW | Duplicate memory card prevention: `service.py` does not have an explicit UPSERT or unique constraint check per `(user_id, memory_type, title)` — duplicates possible if extraction runs twice on same session | `memory/service.py:33-65` | Visual clutter; minor data quality issue | Add `UNIQUE(user_id, memory_type, title_hash)` DB constraint or dedup check before insert |

### Required Tests

| Test Case | Expected Behavior | Suggested File |
|---|---|---|
| `test_pii_not_stored_in_memory_card` | Phone/email in user message should not appear in persisted memory card content | `backend/tests/test_memory_cards.py` |
| `test_duplicate_memory_card_not_created` | Extracting twice from same session should not create duplicate cards | `backend/tests/test_memory_cards.py` |
| `test_guardrail_blocks_crisis_memory` | Content containing suicide keywords is rejected by guardrail | **Already exists**: `TestGuardrail::test_rejects_sos_content` ✅ |

---

## 4. Conversation Quality Audit

### Prompt Stack Found

| Layer | Source File | Purpose | Runtime Order | Risk |
|---|---|---|---|---|
| Persona block | `langgraph_chat.py:121-136` (`_build_persona_block`) | Injects persona style, pronouns, boundaries, distress ceiling note | 1st in system prompt | Medium — large personas inflate token cost |
| Analyst bundle | `langgraph_chat.py:1122-1130` | `suggested_focus`, `emotional_theme`, `clinical_note` appended to system prompt | After persona block | Low — structured injection, no user text |
| Memory context | `langgraph_chat.py` (`_build_friend_context`) | Long-term profile + memory cards | Before user message | Medium — PII risk if not masked |
| Recent transcript hint | `langgraph_chat.py` (`_recent_transcript_hint`) | Last N turns for continuity | Prepended to messages | Low |
| Safety grounding post-filter | `output_grounding.py:28` | Strips diagnosis/prescribe language from reply | After LLM response | Low — deterministic |
| Persona identity enforcement | `langgraph_chat.py:1037` (`_enforce_persona_identity`) | Ensures persona doesn't claim to be real or AI by mistake | After grounding | Low |

### Persona Consistency

| Persona | Implemented As | Affects Text? | Affects Voice? | Safety-Compatible? | Evidence |
|---|---|---:|---:|---:|---|
| `ban_than` (default) | Prompt block in `_build_persona_block` | Yes | Yes (via TTS) | Yes | `registry.py:11` |
| `nguoi_thay` | Prompt block; distress ceiling 0.70 | Yes | Yes | Yes | `registry.py:59`, `gates.py:56` |
| `cun` | Prompt block; unlockable; distress ceiling 0.40 | Yes | Yes | Yes — auto-deactivates at high distress | `registry.py:106`, `gates.py:50` |
| `meo` | Prompt block; unlockable; distress ceiling 0.55 | Yes | Yes | Yes | `registry.py:153`, `gates.py:53` |
| `crush` | Prompt block; safety-restricted; always requires unlock; any distress ≥ threshold → blocked | Yes | Yes | Yes — `"crush_distress_override"` | `registry.py:201`, `gates.py:59-61` |

All 5 personas are **style-mode injections into `friend_node`** — NOT separate graph agents. Contract verified.

### Repetition / Hardcoded Response Risks

| Severity | Issue | Evidence | User Impact | Required Fix |
|---|---|---|---|---|
| 🟠 HIGH | No anti-repetition mechanism — if user sends the same message twice in the same session, friend_node can return an identical reply (chat_response_cache only deduplicates at request level, not response diversity) | `langgraph_chat.py` (no repeat-detection), `chat_response_cache.py:22` (hash is for same-turn dedup, not variety) | User perceives the bot as robotic | Add recent-reply hash to system prompt; or use logit_bias/frequency_penalty to discourage repetition |
| 🟡 MEDIUM | SOS fallback replies in `_persona_fallback_reply` are short hardcoded strings per persona (e.g., `"Tìm kiếm hỗ trợ ngay nhé."`) — could fire on API timeout and sound generic/abrupt | `langgraph_chat.py:140-155` | Jarring if user is not in crisis but LLM times out | Add more variety to fallback strings per persona; log fallback events |
| 🟡 MEDIUM | `_build_voice_intervention` comment (chat.py:244): "TTS is the same text as the assistant/Friend reply" for non-crisis — but for SOS path, `voice_script=script` is set separately. Non-SOS voice may duplicate visible text word-for-word | `chat.py:244,252,276` | Acceptable for non-SOS; verified separate for SOS | Document explicitly; add test asserting SOS voice_script ≠ visible_text |

### Vietnamese Naturalness Assessment

| Dimension | Verdict | Evidence | Improvement |
|---|---|---|---|
| Pronouns and address terms | ✅ Correct | Personas use `mình/bạn` (ban_than), `thầy/em` (nguoi_thay), `cún/bạn` (cun), `mèo/bạn` (meo), `mình/bạn` (crush) per registry system_prompt | None needed |
| Error messages (toast) | ✅ Vietnamese | `CheckinFlow.tsx:140`: `"Không thể lưu check-in. Thử lại nhé."` | None needed |
| Analyst fallback stub | ⚠️ Encoding issue | `langgraph_chat.py:970`: fallback JSON contains UTF-8 mojibake in source (`NgÆ°á»i dÃ¹ng`) — display depends on editor encoding, but runtime Python string is correct unicode | Validate that runtime Python strings are correct by adding a test |
| SOS hotlines | ✅ Vietnamese | `vn_hotlines.py` exists with Vietnamese context | None needed |
| Persona greeting stubs in `router.py` | ✅ Vietnamese (Teencode) | `personas/router.py:23-26` — appropriate informal Vietnamese | None needed |
| Golden/eval tests for Vietnamese quality | ❌ Missing | `test_ai_golden_eval.py` and `test_ragas_eval.py` exist but were not run to completion | Add ≥5 golden conversation pairs covering each persona |

---

## 5. Model Quality / Reliability Audit

### Model Usage Map

| Task | Model | Parameters | Schema Validation | Fallback | Evidence | Verdict |
|---|---|---|---|---|---|---|
| `analyst_node` | `gpt-4o-mini` (configurable `OPENAI_MODEL_ANALYST`) | `temperature=0.0`, `timeout=min(llm_timeout,2.5)s` | JSON via `json.loads()` with try/except | Hardcoded AnalystBundle stub | `langgraph_chat.py:934-988` | ⚠️ No `response_format=json_object` |
| `friend_node` (sync) | `gpt-4o-mini` (configurable `OPENAI_MODEL_FRIEND`) | `temperature` = base + persona delta, `timeout=min(llm_timeout,3.5)s` | N/A (free text) | `_persona_fallback_reply()` | `langgraph_chat.py:1162-1194` | ⚠️ No `max_tokens` |
| `friend_node` (fast path) | `gpt-4o-mini` (configurable `OPENAI_MODEL_FRIEND_FAST`) | Same as above | N/A | Falls back to non-fast model | `langgraph_chat.py:1172-1175` | ✅ Fallback exists |
| `stream_non_sos_turn_events` | Same as friend_node | `timeout=min(llm_timeout,15.0)s` | N/A | `run_non_sos_turn` sync fallback + `_persona_fallback_reply` | `langgraph_chat.py:1533-1569` | ✅ Fallback exists |
| Memory enrichment (cold start) | `gpt-4o-mini` | Likely default | Regex-based post-process | `_fallback_extract()` | `memory_enrichment.py:37,58` | Ambiguous — not fully inspected |

### Evaluation Coverage

| Area | Existing Tests/Evals | Missing Coverage | Risk |
|---|---|---|---|
| Agent routing (SOS/non-SOS) | `test_chat_router_integration.py` — 5 tests | Stream path safety filter parity | Medium |
| Voice escalation | `test_voice_escalation.py` — 16 tests (parametrized) | TTS content-hash dedup | Medium |
| Heart economy | `test_heart_economy.py` — 8 tests | Checkin endpoint does NOT call grant_hearts — no test catches this gap | High |
| Memory guardrail | `test_memory_cards.py` — 17 tests | PII masking before persistence | Medium |
| Chat memory continuity | `test_chat_memory_continuity.py` — 7 tests | Long-term memory retrieval injection | Low |
| Counseling retriever | `test_counseling_retriever.py` — 11 tests | SOS path guardrail | Low |
| Golden quality eval | `test_ai_golden_eval.py` (exists) | Not run to completion; no Vietnamese persona cases verified | High |
| RAGAS eval | `test_ragas_eval.py` (exists) | Not run to completion | High |
| Frontend unit tests | None found | Entire frontend is untested | High |

**Total tests collected: 178** across 20 test files.

### Reliability Risks

| Severity | Issue | Evidence | Runtime Impact | Required Fix |
|---|---|---|---|---|
| 🟠 HIGH | `max_tokens` never set on any OpenAI call — runaway generation possible; costs unbounded | `langgraph_chat.py:935,1166,1173,1534` (no `max_tokens` parameter) | Latency spike; excessive token spend | Add `max_tokens=512` (analyst), `max_tokens=800` (friend) as starting points |
| 🟠 HIGH | No retry decorator on LLM calls — a single transient 500 from OpenAI produces a fallback reply with no retry | `langgraph_chat.py` (no `backoff`, `tenacity`, or retry loop) | User sees generic fallback on any transient OpenAI error | Add `tenacity.retry` with 2 retries and 0.5s backoff on OpenAI calls |
| 🟡 MEDIUM | `analyst_node` uses synchronous `OpenAI()` client inside an async FastAPI route — blocks the event loop for up to 2.5s | `langgraph_chat.py:932,934` — `from openai import OpenAI` (sync client) | Reduced throughput under concurrent load | Migrate analyst and friend nodes to `AsyncOpenAI` |
| 🟡 MEDIUM | Chat response cache (`chat_response_cache.py`) is in-process dict — lost on restart, no TTL enforcement at module level | `chat_response_cache.py:12-62` | Cache miss storm on restart | Move to Redis if caching is intended to survive restart |
| 🟢 LOW | Langfuse tracing is optional (client init skipped silently) — observability has zero guarantee in production | `langfuse_tracing.py:52` `logger.debug("Langfuse init skipped")` | No trace if `LANGFUSE_SECRET_KEY` unset | Add startup check: warn (not crash) if Langfuse key absent |

### Validation Commands

| Command | Result | Notes |
|---|---|---|
| `pytest backend/tests -q` | **Timed out at 120s** — only `[ 40%]` completed before timeout | Tests are slow; likely due to integration tests with DB setup. Collect-only shows 178 tests. Individual unit tests pass quickly. |
| `npm --prefix frontend run build` | **Exit code 2 — FAILED** | 14 TypeScript errors: missing `ThemeContext` module, undeclared `isDark` in AppHeader/Profile/Setting, unused imports in 6 files |
| `python -m pytest backend/tests --collect-only -q` | **Exit 0 — 178 tests collected in 1.58s** | All test files parse correctly |

---

## Cross-System Contract Matrix

| Contract | Expected | Actual | Verdict | Evidence |
|---|---|---|---|---|
| Backend owns reward authority | Backend validates, grants, persists all rewards | Checkin rewards granted by frontend `grantCheckinReward()` in `localStorage` only; backend checkin endpoint never calls `grant_hearts()` | 🔴 VIOLATED | `checkin.py` (full file), `rewardProgress.ts:39-48` |
| Frontend does not mutate wallet directly | Frontend reads balance from backend API | `rewardProgress.ts:30-32`: `localStorage.setItem(REWARD_STORAGE_KEY, ...)` is the only write path | 🔴 VIOLATED | `rewardProgress.ts:30-32` |
| Persona is style mode, not separate runtime agent | All personas injected as prompt block into friend_node | All 5 personas are `_build_persona_block()` injections — VERIFIED | ✅ PASS | `langgraph_chat.py:121-136`, `registry.py` |
| Analyst agent does not produce user-facing text | analyst_node output is AnalystBundle only | `analyst_node` returns `{"analyst_bundle": _bundle, ...}` — never a `reply` key | ✅ PASS | `langgraph_chat.py:879,997` |
| Friend/conversation agent is sole normal-path user-facing response generator | `friend_node` is only LLM call that produces chat reply | VERIFIED for graph path; ⚠️ `stream_non_sos_turn_events` has a shadow LLM call outside the graph | ✅ PASS (with caveat) | `langgraph_chat.py:1062,1473` |
| Safety gate cannot be bypassed by frontend state | SOS detection is deterministic backend rule | `decide_sos()` runs on raw text before any frontend state is consulted | ✅ PASS | `sos_handler.py:236`, `chat.py:407` |
| Memory write is controlled and validated | Guardrail runs before any memory card is persisted | `review_memory_candidate()` called for every candidate in `create_cards_from_candidates` | ✅ PASS | `memory/service.py:44-55`, `guardrail.py:45` |
| Unlock eligibility is backend-validated | `check_unlock_gate()` is called server-side | `personas/gates.py:23-34` is called from `route_persona()` which is called from API layer | ✅ PASS | `personas/gates.py:23`, `personas/router.py:115` |
| TTS jobs are deduplicated | Same text not enqueued twice | In-flight dedup via `_INFLIGHT_JOBS` set (per job_id, not content hash) — content-hash dedup absent | ⚠️ PARTIAL | `proactive_voice.py:203-214` |
| Crisis response is safe but not endlessly repetitive | Deterministic SOS scripts; no LLM; no loop | SOS scripts are deterministic (`sos_handler.py`); voice escalation tiers also deterministic; no loop found | ✅ PASS | `sos_handler.py:256-316`, `voice_escalation` tests |

---

## Risk Register

| Risk ID | Severity | Probability | Impact | Area | Description | Mitigation |
|---|---|---|---|---|---|---|
| R-01 | 🔴 CRITICAL | High | Product integrity | Gamification | Frontend localStorage wallet is the live reward state — data is volatile, forgeable, and diverges from backend DB | Remove localStorage wallet; expose `/hearts/balance` endpoint; read-only frontend |
| R-02 | 🔴 CRITICAL | High | Demo failure | Build | Frontend TypeScript build fails — no production bundle can be produced | Fix 14 TS errors (15 min effort: remove unused imports, fix ThemeContext export) |
| R-03 | 🔴 CRITICAL | High | Data inconsistency | Gamification | `MOCK_STREAK = 3` in production UI; real streak data in backend is never surfaced to user | Wire checkin endpoint to return streak; frontend reads from response |
| R-04 | 🔴 CRITICAL | High | Revenue bypass | Gamification | `update_persona` writes persona_id without unlock validation; persona purchase gate bypassable via API | Enforce `is_persona_unlocked()` in the endpoint |
| R-05 | 🔴 CRITICAL | Medium | Feature dead | Memory | Memory cards API not mounted; Plan 06 feature does not exist at runtime | Mount router in `api.py` |
| R-06 | 🔴 CRITICAL | Medium | Runtime crash risk | Gamification | `rewards.py` imports two non-existent modules; would NameError/ImportError if mounted | Create missing modules or remove broken imports |
| R-07 | 🟠 HIGH | High | Safety gap | Agent Workflow | Persona safety gates (`route_persona`, `check_safety_gate`) are dead code — not called from chat; distress ceilings unenforced server-side | Wire `route_persona()` into chat router |
| R-08 | 🟠 HIGH | Medium | Safety regression | Agent Workflow | `hierarchical_agent_graph.py` is a compiled StateGraph with user-facing text nodes and no safety gate | Feature-flag the module; add safety gate |
| R-09 | 🟠 HIGH | Medium | Persona trust | Conversation | Streaming + non-stream paths have contradictory persona identity instructions ("Friend" identity) | Unify prompt across paths |
| R-10 | 🟠 HIGH | Medium | Product quality | Conversation | Mojibake encoding in prompt literals in `langgraph_chat.py` — garbled Vietnamese possible in production | Fix file encoding; add encoding test |
| R-11 | 🟠 HIGH | High | Cost / latency | Model Quality | No `max_tokens` on any OpenAI call; analyst and friend use synchronous client inside async handler | Add `max_tokens`; migrate to `AsyncOpenAI` |
| R-12 | 🟠 HIGH | High | UX quality | Conversation | No anti-repetition — identical prompt → identical reply under same session context | Add frequency penalty or previous-reply injection |
| R-13 | 🟡 MEDIUM | Medium | Privacy | Memory | Mem0 `add_session()` receives raw unmasked user text; `mask_pii()` not applied before Mem0 ingestion | Apply `mask_pii()` before Mem0 |
| R-14 | 🟡 MEDIUM | Low | TTS quality | Conversation/TTS | Content-hash TTS dedup absent; same voice script can be enqueued multiple times | Add SHA-256 content-hash dedup key |
| R-15 | 🟡 MEDIUM | Medium | Reliability | Model Quality | No retry on LLM calls; single transient error → fallback reply | Add tenacity retry with 2 attempts |
| R-16 | 🟢 LOW | Low | Observability | Model Quality | Langfuse tracing silently disabled if keys absent; no startup warning | Add startup log warning |

---

## Fix Roadmap

### Phase 0 — Stop-Ship Fixes

Issues that break safety, backend authority, data integrity, or core architecture.

| Task | File/Module | Reason | Acceptance Criteria |
|---|---|---|---|
| Remove `grantCheckinReward` localStorage mutation; read/display hearts from backend API | `frontend/src/utils/rewardProgress.ts`, `CheckinFlow.tsx` | Frontend is sole wallet authority — violates backend state ownership contract | No localStorage wallet write; balance read from `/hearts/balance` endpoint |
| Wire `grant_hearts()` + `update_mood_streak()` into `/checkin/quick` endpoint | `backend/app/api/v1/routers/checkin.py`, `hearts/service.py`, `hearts/streaks.py` | Backend heart wallet is never updated from checkin | Checkin response includes `hearts_earned`, `new_balance`, `streak_current`; idempotency prevents double-grant |
| Replace `MOCK_STREAK = 3` with real backend streak data | `frontend/src/components/pages/CheckinFlow.tsx` | Hardcoded mock in production UI | `streakDays` sourced from checkin API response; no `MOCK_*` constant in non-test code |
| Fix frontend TypeScript build failures (14 errors) | `frontend/src/components/common/MoodWordChips.tsx`, `StreakBar.tsx`, `ThemeToggle.tsx`, `AppHeader.tsx`, `Sidebar.tsx`, `Profile.tsx`, `ResourceGrid.tsx`, `Setting.tsx` | Build fails — no production bundle | `npm --prefix frontend run build` exits 0 |
| Fix or remove broken imports in `rewards.py` (`app.personas.progression`, `app.personas.boundary_intro`) | `backend/app/api/v1/routers/rewards.py:24-25` | Missing modules cause import error if router is mounted | Either create the two missing modules or remove broken imports; `python -c "from app.api.v1.routers import rewards"` succeeds |
| Register memory cards router in `api.py` | `backend/app/api/v1/api.py`, `backend/app/memory/routes.py` | Entire Plan 06 memory card HTTP surface is unreachable | `GET /api/v1/chat/memory-cards` returns 200; tests cover list/patch/extract |
| Enforce `is_persona_unlocked()` in `update_persona` endpoint | `backend/app/api/v1/routers/auth.py:553-573` | Any persona_id can be persisted without purchasing — purchase gate is bypassable | `PATCH /auth/me/persona` returns 403 for locked persona_id; test confirms Crush cannot be set without unlock |
| Wire `route_persona()` into `_active_persona_id()` in chat router | `backend/app/api/v1/routers/chat.py:89-99`, `backend/app/personas/router.py:47` | Persona distress/safety ceilings are dead code — not enforced at chat time | `route_persona()` called on each turn; Crush + high distress → forced `ban_than`; test asserts this |

### Phase 1 — Correctness and Test Coverage

| Task | File/Module | Reason | Acceptance Criteria |
|---|---|---|---|
| Add `response_format={"type":"json_object"}` to analyst OpenAI call | `langgraph_chat.py:935` | JSON output enforced by prompt only; silent parse failures | Analyst call uses json_mode; malformed-JSON test passes |
| Add `max_tokens` to all OpenAI calls | `langgraph_chat.py:935,1166,1173,1534` | Unbounded generation — cost and latency risk | All LLM calls have explicit `max_tokens` limit |
| Verify and enforce `mask_pii()` before writing user text to DB | `chat.py` (message persistence), `memory/service.py` | PII may persist unmasked | `mask_pii()` called at persistence boundary; test confirms phone/email stripped from memory cards |
| Add content-hash TTS dedup to `enqueue_voice_job` | `proactive_voice.py:124` | Same text can be enqueued multiple times | SHA-256 hash of text + voice_id checked against recent-job cache before enqueue |
| Consolidate or gate stream LLM call in `stream_non_sos_turn_events` | `langgraph_chat.py:1473-1566` | Shadow path can diverge from graph path safety filters | Stream path uses same `sanitize_grounded_reply` + `_enforce_persona_identity` as graph path; unit test asserts parity |
| Add `test_checkin_quick_grants_hearts_and_streak` | `backend/tests/test_heart_economy.py` | No test covers the end-to-end checkin→reward flow | Test passes after Phase 0 fix |
| Add `test_analyst_node_json_fallback` | `backend/tests/test_chat_router_integration.py` | Malformed JSON from analyst not explicitly tested | Mock LLM returns non-JSON; assert fallback AnalystBundle used |

### Phase 2 — Product Quality Improvements

| Task | File/Module | Reason | Acceptance Criteria |
|---|---|---|---|
| Implement anti-repetition: inject last N assistant replies into system prompt or add `frequency_penalty=0.6` | `langgraph_chat.py:friend_node` | Same input → same output; UX regression | Parametric test: same user message sent 3 times yields ≥2 distinct replies |
| Migrate analyst and friend to `AsyncOpenAI` | `langgraph_chat.py:932,1162` | Sync client blocks async event loop | All OpenAI calls use `await`; no sync `.create()` in async context |
| Add retry with `tenacity` (2 retries, 0.5s wait) to LLM calls | `langgraph_chat.py` | Single transient failure → immediate fallback | Retry test: mock first call raises `openai.APIError`, second succeeds |
| Feature-flag `hierarchical_agent_graph.py` | `hierarchical_agent_graph.py`, `backend/app/core/config.py` | Unsafed user-facing text nodes in compiled graph | `settings.enable_hierarchical_graph = False`; graph not built unless flag is True and safety gate added |
| Add 5+ Vietnamese golden conversation pairs per persona | `backend/tests/test_ai_golden_eval.py` | No regression guard on persona Vietnamese quality | Golden eval runs in CI; prompt/response pairs cover cun, meo, crush, nguoi_thay, ban_than |
| Add startup observability warning when Langfuse keys absent | `backend/app/main.py` | Silent observability gap | `logger.warning("Langfuse disabled — set LANGFUSE_SECRET_KEY for tracing")` on startup |

---

## Final Recommendation

1. **Must fix before any further feature work (in priority order):**
   - **Wire `route_persona()` into the chat router** — persona safety ceilings are currently dead code; a user at high distress can remain in Crush or Cún mode with no server-side enforcement.
   - **Enforce `is_persona_unlocked()` in `update_persona`** — the entire unlock purchase flow is bypassable via a direct API call.
   - **Fix broken imports in `rewards.py`** — `app.personas.progression` and `app.personas.boundary_intro` do not exist; the rewards router cannot be safely mounted.
   - **Mount the memory cards router** (`memory/routes.py`) in `api.py` — Plan 06 is entirely unreachable.
   - **Wire checkin → `grant_hearts()` + `update_mood_streak()`** and remove the `localStorage` wallet.
   - **Fix the frontend TypeScript build** (14 errors).

2. **Can wait for next sprint:**
   - `max_tokens` limits, retry logic, `AsyncOpenAI` migration, content-hash TTS dedup, anti-repetition, and Vietnamese golden-eval tests are important but do not break safety, unlock integrity, or data correctness.
   - Unifying sync/stream persona identity prompts is a conversation quality fix, not a safety-critical one.

3. **Should be deleted or deprecated:**
   - `hierarchical_agent_graph.py` — delete or hard feature-flag it. It is a speculative blueprint with no tests, no safety gate, and user-facing text in every node.
   - `personas/prompt_blocks.py:build_system_prompt` — dead export; either adopt it in `friend_node` or remove it to prevent future divergence.
   - The `REWARD_STORAGE_KEY` `localStorage` wallet logic in `rewardProgress.ts` — remove entirely once backend balance is wired.

4. **Must be tested before the next merge:**
   - `test_route_persona_enforces_distress_ceiling_in_chat` (new) — proves `route_persona()` is wired to chat
   - `test_update_persona_rejects_locked_persona` (new) — proves unlock gate in auth endpoint
   - `test_rewards_router_imports_cleanly` (new) — `python -c "from app.api.v1.routers import rewards"` exits 0
   - `test_memory_cards_api_mounted` (new) — GET `/chat/memory-cards` is routable
   - `test_checkin_quick_grants_hearts_and_streak` (new) — end-to-end checkin reward
   - `test_frontend_build_passes` (CI gate — `npm --prefix frontend run build` must exit 0)

5. **Architecture should remain 3-agent:**
   - The current 3-node LangGraph pipeline (`distress_router → analyst → friend`) is correctly implemented, safe, and matches the PRD contract. It should not be expanded. The `hierarchical_agent_graph.py` blueprint represents a future VinMec expansion path that requires a separate safety review before activation. Do not merge any code that calls `build_hierarchical_graph()` from a production route.
