# Changelog — Serene

> Format: [Keep a Changelog](https://keepachangelog.com) | Vingroup Engineering

---

## [Unreleased] — Analyst Neo4j Graph Context · 2026-05-08

### Added
- `backend/app/services/neo4j_client.py` — `get_user_patterns_async(user_id, limit)` async function; wraps sync Neo4j driver via `asyncio.to_thread()` to avoid blocking the event loop; returns `{triggers, emotions, coping, available}` dict; fail-safe — returns `available=False` with empty lists on any error (no driver, query failure, or timeout)
- `backend/tests/test_db_integration.py` — two new `@pytest.mark.asyncio` unit tests: `test_get_user_patterns_async_no_driver` (driver=None → available=False) and `test_get_user_patterns_async_filters_none_names` (None-name rows are filtered before return)

---

## [Unreleased] — Database Audit Remediation · 2026-05-08

### Added
- `backend/app/services/risk_writer.py` — synchronous `RiskInferenceLog` and `SessionRiskSnapshot` writers; called from `_record_sos_side_effects` (score=1.0, source=sos_override) and `_queue_human_review` (score=distress_score, source=supervisor) in `chat.py`
- `backend/app/services/analyst_writer.py` — analyst signal + insight hypothesis pipeline (`record_analyst_signal`, `upsert_insight_hypothesis`); wired into `close_session_summary` after profile rollup; SOS sessions are skipped
- `backend/alembic/versions/0021_screening_answers_table.py` — migration adding `app.screening_answers` (backend-only raw questionnaire answer store with instrument check constraint and composite index)
- `backend/app/services/db/models.py` — `ScreeningAnswer` ORM model (`answer_id`, `user_id`, `instrument_id`, `raw_score`, `answers`, `submitted_at`)

### Changed
- `backend/app/api/v1/routers/screening.py` — `POST /screenings/submit` now stores only coverage boolean metadata in `clinical_profiles.phq9_coverage`/`gad7_coverage`; raw answers go to `ScreeningAnswer` table — closes audit High severity finding §3
- `backend/app/services/session_summary.py` — `close_session_summary` calls `record_analyst_signal` + `upsert_insight_hypothesis` after profile rollup; failures are caught and logged without blocking the summary commit
- `backend/app/dashboard/service.py` — removed dead `_profile_insights()` and `_build_insight_cards()` heuristic card functions; `build_safe_insight_cards` signature drops unused `profile_data` parameter; all three callers updated
- `backend/app/api/v1/routers/chat.py` — imports `record_risk_inference` and `record_session_risk_snapshot` from `risk_writer`; SOS and high-distress paths now write safety audit rows synchronously before commit
- `DATABASE_DESIGN_AUDIT_REPORT.md` and `DATABASE_REFACTOR_PHASE_PLAN.md` — added deployment handoff notes confirming all remaining audit findings are closed, documenting the `build_safe_insight_cards` breaking change, and calling out required production migration `0021_screening_answers_table`

### Fixed
- Safety audit trail gap: `risk_inference_log` and `session_risk_snapshots` now receive writes on SOS and high-distress turns (previously models existed but had no writers)
- Analyst pipeline gap: `analyst_signals` and `insight_hypotheses` now receive writes at session close (previously models existed but had no writers)
- Heuristic insight cards no longer appear in `build_safe_insight_cards` output; only evidence-backed `InsightHypothesis` rows with `evidence_count > 0` are served to the dashboard

---

## [Unreleased] — Sprint A Phase 5 · 2026-05-07

### Fixed
- **Cursor agent token-waste guardrail**: Added an always-applied workspace rule at `.cursor/rules/no-auto-python-execution.mdc` to prevent automatic Python interpreter discovery and Python command execution (`python`, `py`, `pytest`, `alembic`) unless the user explicitly requests it.
- **ORM column names aligned to SQL schema**: Renamed `tone_cam_xuc` → `assistant_tone` (with updated `CheckConstraint` accepting `supportive|validating|cheerful|calming|mentor|neutral`) and `muc_do` → `severity_level` (with `CheckConstraint` accepting `low|moderate|high|imminent|unknown`) in `backend/app/services/db/models.py`. Propagated the rename across all reference sites: `chat.py`, `admin.py`, `langgraph_chat.py` (TypedDict field, dict keys, LLM prompt, `build_normal_envelope` parameter), and `session_summarizer.py` (dataclass field, raw SQL query, attribute accesses).
- **Chat stream 500 — `mood_checkins.time_bucket` undefined**: Local DB was stamped at `0005_letters_schema` while the model expected `0011_mood_checkin_time_bucket`; running `alembic upgrade head` failed at `0006_reports_enhancement` because the optional `reports` table never existed (no `Report` model is created by `init_db`). Made `0006_reports_enhancement` idempotent: it now no-ops when `reports` is absent, and column / index additions are guarded so re-runs are safe. Re-running `alembic upgrade head` now applies `0007 → 0011`, restoring the `time_bucket` column and unblocking `POST /v1/chat/message/stream`.

## [Unreleased] — Sprint A Phase 5 · 2026-04-30

### Removed
- Dropped `COMMIT_PLAYBOOK.MD` from version control; added `.gitignore` rules so local AI-agent commit playbooks (e.g. Claude Code / Cursor) are not pushed to GitHub.
- Dropped `tham-khao/` (local reference GIFs) from version control and ignored the folder so it is not committed again.

### Docs
- Added `docs/GLOSSARY_RUNTIME.md` as the canonical runtime naming map between product role names, orchestration identifiers, graph keys, routing tokens, and trace spans.
- Linked runtime naming guidance from `docs/PRD.md`, `docs/SEQUENCE_DIAGRAMS.md`, `docs/API_SPEC.md`, and `CLAUDE.md` to keep terminology synchronized across specs and execution plans.
- Normalized ambiguous `.claude/plan/00_MASTER_CONTEXT.md` wording (for example "Agent friend") to the PRD naming convention: Serene Conversation Agent (`FriendNode`).
- Aligned `docs/PRD.md` and `docs/SEQUENCE_DIAGRAMS.md` terminology: product agent names (**Serene Conversation Agent**, **Internal Analyst Agent**, **Safety Agent**) with orchestration ids (`FriendNode`, `AnalystNode`, `SafetyFinalizer`); removed ambiguous “LLM node” phrasing for agents; clarified Neo4j graph “node” vs agent.
- Renamed all `docs/sequence/*.png` assets to lowercase kebab-case (no spaces) and updated `docs/SEQUENCE_DIAGRAMS.md` image paths so Markdown preview resolves diagrams reliably.
- Restructured `docs/BACKEND_PLAN.md` for agent-driven execution: added Claude Code usage guide, executive summary, stable-anchor table of contents, and six **Part** sections (I–VI) mapping tasks to §0–§17.
- Completed a context-bloat refactor for `.claude/skills`: reduced `context-engineering`, `project-documentation`, and `security-compliance` to lean router-style `SKILL.md` files and moved deep guidance to on-demand references.
- Updated `.claude/skills/skill-registry.json` and `.claude/skills/README.md` to remove eager-load semantics ("always load"), register Serene-specific skills, and classify `project-bootstrap` as a cold-path skill with archive note.

### Changed
- Updated backend runtime docstrings/comments in `backend/app/services/langgraph_chat.py` and `backend/app/services/sos_handler.py` to remove deprecated `BACKEND_PLAN` references and point to `docs/PRD.md` + `docs/GLOSSARY_RUNTIME.md`.

### Fixed
- **Backend copy encoding**: corrected mojibake Vietnamese strings in `_build_friend_context` / `_build_mentalchat_examples` (`langgraph_chat.py`); added `supervisor_node` compatibility shim for golden eval; pointed `letter` router imports at `app.services.db` / `app.services.schemas`.
- **Test suite after DB/TTS refactor**: pytest imports now use `app.services.db.session`; removed obsolete Blaze `_render_blaze_audio` tests; updated chat router integration `FakeDB` (scalar + outbox id on flush); adjusted voice intervention tests for `_build_voice_intervention` signature.
- **Voice audio delivery (autoplay policy)**: `playAudioUrl` now decodes and plays base64 audio via the persistent, user-gesture-unlocked `AudioContext` instead of `HTMLAudioElement`. This is the root cause of "Voice: queued then silently disappears" — `HTMLAudioElement.play()` called from a `setTimeout` poll callback is unconditionally blocked by Chrome/Firefox autoplay policy, even when a prior user gesture triggered the send action. `AudioContext` (already unlocked by `unlockAudioContext()` inside `handleSend`) is not subject to this restriction.
- Added `audioCtxRef` to store the single shared `AudioContext` created at first send; `unlockAudioContext` now assigns it to `audioCtxRef.current` so `playAudioUrl` and the "Nghe Serene" fallback button both reuse the same unlocked context.
- `ModuleNotFoundError` when `elevenlabs` package is absent now raises `PermanentTtsError("elevenlabs_package_missing")` instead of being caught as a transient error and retried 3 times uselessly; also added to `_PROVIDER_LEVEL_BLOCK_CODES` so subsequent jobs don't enqueue at all.
- Added diagnostic console logs (`[voice]` prefix) to `pollVoiceJob` (poll result, error_code, audio_data_uri presence) and `applyIntervention` (tts_job_id, audio_url, voice_status from SSE) to expose silent failures in DevTools.
- Added warning log in `backend/app/services/tts_renderer.py` when `elevenlabs_route_not_allowed` fires, logging `safety_tier` and `distress_score` to aid root-cause analysis.
- **Voice worker silent-death fix**: `get_session_factory()` / `factory()` in `_process_job` were outside the `try` block — if either threw, the daemon thread died with no log, `_INFLIGHT_JOBS` was never cleaned, and the job stayed `queued` forever. Both are now inside the try; `db = None` is initialized before try so the `finally` guard (`if db is not None: db.close()`) always executes correctly.
- **Voice worker row-miss silent return**: `_process_job` previously returned silently (no log) when `db.get(SyncOutbox, job_id)` returned `None`. Added `logger.warning("voice_job_row_missing ...")` with `row_found` and `event_type` fields so this failure is visible in backend logs.
- **Voice worker thread-start observability**: Added `logger.info("voice_job_thread_start ...")` at the very beginning of `_process_job` (before any DB access) so backend logs confirm whether the daemon thread is actually executing.

## [Unreleased] — Sprint A Phase 5 · 2026-04-29

### Added
- Persona selection flow for Friend: new authenticated API `POST /auth/me/persona` persists selected persona in `UserProfile.profile.persona` and returns selection timestamp.
- First-time persona picker popup in chat UI for newly registered users with no persona selected; users can choose among 7 personas from `BUILDING-PLAN-PERSONAS.md`.
- Persona settings entry inside the 3-dot options menu in chat, allowing users to reopen the picker and switch persona later.

### Changed
- `GET /auth/me` now returns `persona_id` and `persona_selected_at` so frontend can detect first-use persona setup and render current selection in settings.
- Friend prompt assembly now injects a persona block (`voice/tone/xung ho`) based on the active persona id passed from chat router, while preserving existing safety constraints.
- Removed legacy naming bleed-through (`Mây`) across Friend prompt, safety voice hint copy, and chat pending placeholder; agent display name is now consistently `Friend`.
- Strengthened persona prompt block with persona-specific behavior constraints (especially `nguoi_yeu`) to reduce machine-like generic replies and increase personality consistency.
- Persona enforcement hardening: persona block is now sent as a dedicated high-priority system instruction (separate from base prompt), and friend generation temperature now applies persona-specific `temperature_delta` (including `nguoi_yeu`).
- Frontend typing placeholder changed to `Đang nhập tin nhắn...` only when backend enters model generation stage, reducing robotic feel and avoiding conflict with error fallback messages.
- Persona-aware error fallback copy in chat UI now keeps tone consistency (e.g. `nguoi_yeu`) when stream/node failures happen.
- Persona configs are normalized back to spec pronouns/style (e.g. `nguoi_yeu`: `mình/bạn`) and no longer use non-spec colloquialisms that broke tone consistency.
- Added per-turn persona safety resolver in Friend flow: auto-fallback to `ban_than` for `nguoi_yeu` at distress `>=0.6`, `cun/meo/nguoi_la` at distress `>=0.72`, and `nguoi_yeu` max 20 user turns.
- Added unit tests for persona block pronouns, temperature delta behavior, and distress-based override rules (`backend/tests/test_persona_enforcement.py`).
- Persona identity enforcement in `friend_node`/postprocess: removed generic "Friend" self-introduction rule, require intro by active persona `label`, and normalize openings like `Friend ...` or `Tôi là Friend ...` into persona-specific form using configured `self_pronoun` + `user_pronoun`.
- Removed always-on default attachment card (`breath_478`) from both sync and stream Friend flows; `the_dinh_kem` now appears only when explicitly requested by user intent or matched by attachment trigger rules.
- Voice TTS queue hardening: auto-process worker now immediately re-dispatches transiently failed jobs (until retry cap) instead of leaving them in `queued/pending` forever.
- ElevenLabs eligibility/config failures now surface as permanent errors so proactive voice returns `failed` instead of hanging at `queued` when provider requirements are not met.
- Stream requests now emit the same unauthorized event on `401` as non-stream HTTP calls, preventing stale "logged-in" UI state after session expiry.
- Removed Blaze provider from runtime TTS codepaths; proactive voice now runs in ElevenLabs-only mode (with `auto` aliased to ElevenLabs), and backend defaults/config templates are updated accordingly.
- Database engine defaults were tightened for Supabase session pooler usage (`DB_POOL_SIZE=4`, `DB_MAX_OVERFLOW=2`) and runtime pool creation now auto-caps `pool_size + max_overflow` to 10 on `*.pooler.supabase.com:5432` to reduce `EMAXCONNSESSION` failures under local polling/stream load.
- ElevenLabs budget guard now falls back to an in-process daily counter when Redis is unavailable, so proactive voice can still synthesize in local/dev instead of failing with `elevenlabs_budget_unavailable`.
- Proactive voice provider lock no longer blocks all future jobs for per-request eligibility failures (`elevenlabs_route_not_allowed`, `elevenlabs_budget_unavailable`); global block now applies only to true provider-level configuration failures (feature disabled / credentials missing).
- Voice worker now persists `failed` state with `tts_worker_exception` when unexpected exceptions happen, preventing silent `queued/processing` hangs during voice-job polling.
- Voice job state machine now self-heals from stuck `queued`: polling endpoint auto-kicks worker for pending jobs and fails jobs with explicit `voice_job_timeout` after queue-time threshold, preventing infinite client polling loops.
- Added voice pipeline observability logs for enqueue, self-heal kick, retry scheduling, timeout failure, and permanent provider failures with distress/risk snapshot context.
- Session-level TTS dedupe now actively re-kicks worker when reusing an existing queued `tts_job_id`, and stale in-memory inflight locks are reclaimed automatically to prevent ghost queued jobs after thread hangs/crashes.
- Voice execution lifecycle now uses unique job identity per enqueue (no session-level `tts_job_id` reuse), eliminating ambiguous execution guarantees and reducing ghost-queued regressions.
- Voice worker control plane moved to backend startup lifecycle: FastAPI now launches a dedicated `voice_tts_worker` loop so queued jobs are progressed even without client polling.
- Inflight lock now tracks ownership token per job; stale lock reclaim drops stale owner before takeover to reduce double-processing race risk.
- Fixed stale JSON payload persistence for voice jobs: nested `payload.voice.status` updates now call SQLAlchemy `flag_modified`, preventing rows from reaching `status=done` while API still reports `voice.status=queued`.
- Voice job status endpoint now repairs legacy inconsistent rows (`status=done` + `payload.voice.status=queued`) by rebuilding `audio_url`/`audio_data_uri` from the generated audio file or failing explicitly if audio is missing.
- Chat UI now renders completed proactive TTS as an inline voice message card with Play/Replay controls instead of auto-playing audio; crisis hotline/resource text remains below the voice card.

### Removed
- **`_quick_non_sos_turn()`** (`langgraph_chat.py`) — divergent canned-reply fast path for short greetings/thanks (distress < 0.38) is deleted. All turns now flow through `graph.invoke()`. Low-distress short messages continue to get the fast GPT-4o-mini model via the existing `use_fast_friend_model` flag in `distress_router` (distress < 0.55, len ≤ 120 chars).
- **`_QUICK_THANKS_RE`, `_QUICK_GREETING_ONLY_RE`, `_DISTRESS_HINT_RE`** — regex constants only used by `_quick_non_sos_turn`; removed together with the function. `_GREETING_RE` and `_ANALYST_TRIGGER_RE` are retained (used by other code).
- **`quick_turn` early-return blocks** — removed from both `run_non_sos_turn` and `stream_non_sos_turn_events`; `graph.invoke` / LangGraph streaming is now the single entry point for every non-SOS turn.

### Added
- **`[FastPath]` metrics log** (`distress_router`) — emits `[FastPath] corr=… distress=… msg_len=… model=fast` when `use_fast_friend_model=True`, providing observability for fast-model routing without the removed bypass path.
- **`backend/tests/test_fastpath_removal_phase5.py`** — 15 tests confirming: `_quick_non_sos_turn` / `_DISTRESS_HINT_RE` / `_QUICK_THANKS_RE` / `_QUICK_GREETING_ONLY_RE` are gone; greeting and thanks turns call `graph.invoke`; `routing_history` no longer contains `friend_fastpath`; `[FastPath]` log emitted/suppressed correctly at boundary conditions.

### Changed
- **`test_analyst_bundle_phase2.py`** — removed two `patch("..._quick_non_sos_turn", return_value=None)` patches from `test_cold_start_screening_note_seeded_as_analyst_bundle` and `test_no_screening_note_seeds_null_bundle`; those tests no longer need the patch since the function is gone.

---

## [Unreleased] — Sprint A Phase 4 · 2026-04-29

### Added
- **`_maybe_enqueue_voice()`** (`chat.py`) — single authority for proactive voice trigger decisions on non-SOS turns. Evaluates `compute_escalation_signal` + `proactive_voice_auto_distress_threshold`, returns `None` when voice should not fire, a cooldown placeholder dict when cooldown is active, or a full intervention dict by delegating to `_build_voice_intervention`. Replaces ~30 lines of duplicated inline logic in both `send_message` and `send_message_stream`.
- **`backend/tests/test_distress_voice_phase4.py`** — 18 tests covering: `_apply_cold_start_profile` distress immutability (delta ignored, traits/note preserved), `_maybe_enqueue_voice` threshold boundary (at/below/above), escalation-signal path, cooldown path, empty-reply guard, trigger_reason selection, and importability checks.

### Changed
- **`_apply_cold_start_profile`** (`langgraph_chat.py`) — stopped applying `profile.distress_delta` to `distress_score`. `warmed_traits` and `screening_note` are still returned and used; only the score mutation is removed. Fixes Flaw 2 (distress mutation point inside `run_non_sos_turn`).
- **`send_message` sync path** (`chat.py`) — removed `distress += 0.08` mood adjustment; `distress = distress0` (frozen from `decide_sos()`). Fixes Flaw 2 (mutation point in middleware). Mood remains available to LangGraph via `mood_today` state field.
- **`send_message_stream` stream path** (`chat.py`) — same mood-adjustment removal.
- **`send_message` + `send_message_stream` voice trigger blocks** — replaced ~30-line duplicated `compute_escalation_signal` / `if voice_trigger …` blocks with a single `_maybe_enqueue_voice(...)` call each. Fixes Flaw 8 (scattered voice enqueue). SOS path retains direct `_build_voice_intervention` call (unconditional — no threshold change for crisis safety).

---

## [Unreleased] — Sprint A Phase 3 · 2026-04-29

### Added
- **`_postprocess_friend_reply(raw_reply, user_text, distress_score, mentalchat_block, correlation_id)`** (`langgraph_chat.py`) — single authority for all post-LLM reply processing: `_enforce_reply_quality` → `_sanitize_assistant_reply` → `sanitize_grounded_reply` → distress follow-up append. Emits a `[FriendPostProcess]` audit log entry on every call with `correlation_id`, `grounded` flag, and `quality_changed` flag.
- **`backend/tests/test_postprocess_phase3.py`** — 12 tests covering return types, empty-reply fallback, high/low distress append behavior, forbidden-token sanitization, audit log emission, `friend_node` integration, and pipeline consistency between direct call and `friend_node` output.

### Changed
- **`friend_node`** — replaced 5-line inline post-processing block with a single `_postprocess_friend_reply(...)` call; no behavior change.
- **`stream_non_sos_turn_events` stream path** — replaced identical 5-line inline post-processing with `_postprocess_friend_reply(...)`; eliminates divergence risk between the two paths.

---

## [Unreleased] — Sprint A Phase 2 · 2026-04-29

### Added
- **`analyst_node` typed `AnalystBundle` output** (`langgraph_chat.py`) — migrated from raw `analyst_instruction: str` to a structured `AnalystBundle` dataclass. LLM output is now parsed from 4-key JSON (`clinical_note`, `emotional_theme`, `suggested_focus`, `risk_indicators`); parse errors fall back to an empty bundle so `friend_node` continues without enrichment.
- **`friend_node` second system message injection** — `analyst_bundle` is consumed as a dedicated `{"role": "system", "content": analyst_ctx}` message inserted between the base system prompt and user payload, per BUILDING-PLAN-AGENT-SPECS.md §FriendNode prompt assembly order. Analyst context is no longer appended to the base system string.
- **`[ShadowCompare-RuleBasedReply]` logging** — `friend_node` and stream path both log when `_rule_based_reply()` fires, enabling parity audit vs `decide_sos()` before the fallback is removed. `_rule_based_reply()` is preserved until parity gate passes.
- **Cold-start bundle seeding** — `run_non_sos_turn` / `stream_non_sos_turn_events` now seed `analyst_bundle` with a minimal `AnalystBundle(emotional_theme="cold_start_screen")` when `_apply_cold_start_profile()` returns a non-empty `screening_note`; `analyst_node` overwrites it with a richer bundle when routed to analyst.
- **`backend/tests/test_analyst_bundle_phase2.py`** — 18 tests covering JSON parsing (valid/invalid/truncation), timeout cap, routing_history, second-system-message injection, no-bundle path, analyst_ctx isolation, cold-start seeding, and shadow logging.

### Changed
- **`analyst_node` context window** — reduced from 8 turns to **6 turns** (matches `friend_node`; eliminates Analyst/Friend asymmetry per BUILDING-PLAN.md Flaw #3).
- **`analyst_node` system prompt** — updated to 4-key JSON schema (`clinical_note`, `emotional_theme`, `suggested_focus`, `risk_indicators`) with explicit forbidden-output rules; removed legacy `suggested_probe` key.
- **`analyst_node` LLM timeout** — reduced from `min(llm_timeout, 2.8)` to `min(llm_timeout, 2.5)` per spec (Analyst is simpler than Friend).
- **`analyst_node` return** — now returns `{"analyst_bundle": AnalystBundle, ...}` instead of `{"analyst_instruction": str, ...}`.
- **`run_non_sos_turn` / `stream_non_sos_turn_events` state init** — replaced `"analyst_instruction": screening_note` with `"analyst_bundle": AnalystBundle(...)` or `None`.
- **Tracer `input_messages`** (`friend_node` + stream path) — updated to use `friend_messages` / `stream_messages` list (includes analyst system message when present), so Langfuse traces accurately reflect the prompt sent to OpenAI.

---

## [Unreleased] — Sprint A Phase 1 · 2026-04-29

### Added
- **`AnalystBundle` frozen dataclass** (`langgraph_chat.py`) — typed, immutable output contract for `analyst_node`; defined now, fully wired in Phase 2.
- **`distress_router` LangGraph node** — replaces `supervisor_node` with 3 priority-ordered rules: (1) `crisis_route_finalized` override, (2) `distress_score >= 0.72`, (3) `_ANALYST_TRIGGER_RE` keyword match; all other turns default to `friend`.
- **`_legacy_supervisor_route` shadow helper** — pure function that returns the old supervisor's routing decision; called inside `distress_router` to log `[ShadowCompare]` entries when decisions diverge. Enables safe Phase 1 cutover validation. Removed in Phase 2 after parity confirmed.
- **Routing threshold named constants** (`_ANALYST_DISTRESS_THRESHOLD = 0.72`, `_FAST_MODEL_DISTRESS_THRESHOLD = 0.55`, `_FAST_MODEL_MSG_LEN_MAX = 120`) — single source of truth; no more magic numbers in routing logic.
- **`backend/tests/test_distress_router.py`** — 26 tests covering all 5 mandatory Phase 1 regression cases, fast-model flag logic, routing_history tracking, `route_after_distress_router`, `AnalystBundle` immutability, and shadow-compare logging.

### Changed
- **`ChatGraphState`** — removed `analyst_calls_this_turn`, `supervisor_route`, `supervisor_reason`; added `route_decision: Literal["analyst", "friend"]`, `route_reason: str`, `analyst_bundle: AnalystBundle | None` (placeholder for Phase 2).
- **`_ANALYST_TRIGGER_RE`** — expanded to include `phuong an`, `phuong phap`, `giai phap`, `y tuong`, `tinh toan`, `plan`, `strategy`, `solution`, `idea`; fixed word boundaries; removed invalid `re.VIETNAMESE` flag from spec.
- **`use_fast_friend_model` init** — changed from `distress < 0.65` (caller) to `False` in both `run_non_sos_turn` and `stream_non_sos_turn_events`; `distress_router` now owns this flag using the new threshold constants.
- **`build_chat_graph`** — wired `distress_router` as first node; replaced `supervisor` + `route_after_supervisor` conditional edges with `distress_router` + `route_after_distress_router`.
- **`stream_non_sos_turn_events` inline routing** — updated inline supervisor call to `distress_router(state)` + `route_after_distress_router(state)`.
- **`analyst_node`** — removed `calls` counter; no longer reads or returns `analyst_calls_this_turn`.

### Removed
- **`supervisor_node`** — replaced by `distress_router`.
- **`route_after_supervisor`** — replaced by `route_after_distress_router`.
- **`_ANALYST_CALLS_CAP`** — analyst call cap now enforced by graph structure (no cycles), not by a counter.

---

## [Unreleased] — Sprint 5 · 2026-04-27

### Added
- **`PROACTIVE_VOICE_AUTO_DISTRESS_THRESHOLD`** (default `0.8`) — proactive TTS enqueues when `final_distress` reaches this threshold (or escalation signal), **without** user voice consent (safety-first).
- **`backend/scripts/verify_elevenlabs.py`** — smoke-check `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` via the same `text_to_speech` path as production (minimal 1-char probe; avoids `models.list()` which needs `models_read`).

### Changed
- **Planning docs alignment (LangGraph refactor):** synchronized `BUILDING-PLAN.md`, `BUILDING-PLAN-AGENT-SPECS.md`, `BUILDING-PLAN-PERSONAS.md`, and `PROJECT_BRIEF.md` with execution order: Sprint A = Phases 1-5 core only, Sprint B = personas; removed `persona_router` ambiguity from core graph, moved output sanitization into FriendNode, and added mandatory `decide_sos()` parity/shadow gate before deleting legacy Friend safety fallback.
- **API docs alignment:** updated `docs/API_SPEC.md` chat pipeline description to Sprint A execution order (`distress_router` → `analyst_node` conditional → `friend_node` with internal sanitizer), explicitly marked persona subsystem as Sprint B defer, and corrected proactive voice payload docs to remove `copy_ngan`/consent-gated language.
- **Backend plan alignment:** updated `vingroup-agent-skills/BACKEND_PLAN.md` to Sprint A graph (`distress_router` → AnalystNode conditional → FriendNode), 6-turn context, no `analyst_calls_this_turn`, proactive TTS without voice consent, and DistressRouter/Analyst observability naming.
- **Proactive voice** — TTS script is the **assistant/Friend reply text** (not a separate `build_voice_script` template). Removed `copy_ngan` meta line from intervention payload. Blaze restored as primary/fallback provider (`TTS_PROVIDER=blaze|elevenlabs|auto`); ElevenLabs voice settings tuned for calmer delivery (stability ~0.82, similarity_boost ~0.78, speed ~0.9).
- **Voice consent** — removed from chat routing, proactive enqueue payload, Register, Chat UI toggle, and signup follow-up policy call. Policy endpoints may remain for legacy clients.
- **`Sidebar.tsx`** — Removed "Bài tập" (Dumbbell) as a standalone nav item; renamed "Nguồn lực" → "Tài nguyên" with `Library` icon. Mobile bottom nav rebalanced to 5 remaining items.
- **`Resources.tsx`** — Full rewrite: (1) Vietnamese labels for all category tabs (Thiền định, Ngủ & Thở, Âm nhạc, Trí tuệ, Vận động); (2) new **SleepTab** component for "Ngủ & Thở" category — shows 4 breathing/relaxation exercises (cards linking to `/serene/exercises?exercise=…`) + Sleep Stories section + Soundscapes section; (3) `AnimatePresence` fade-slide transitions between tabs; (4) extracted `ResourceGrid` component for generic categories; (5) loads exercises via `exerciseService.list()` with `FALLBACK_EXERCISES` fallback; default landing category changed to `sleep`.
- **Architecture planning docs** — aligned `BUILDING-PLAN.md`, `BUILDING-PLAN-PERSONAS.md`, and `BUILDING-PLAN-AGENT-SPECS.md` with persona decision: user-facing agent name stays **Friend** (no Mây/An/Lửa/La Bàn/Gương naming), persona routing is deferred to Sprint B, and `nguoi_yeu` is not auto-suggested unless prior opt-in.
- **Docs naming alignment** — updated `docs/API_SPEC.md`, `docs/SEQUENCE_DIAGRAMS.md`, and `docs/FRONTEND_PLAN.md` to use **Friend + persona/feature labels** for user-facing language; removed legacy mascot naming (Mây/An/Lửa/La Bàn/Gương) while preserving technical agent terminology where needed.
- **Project-wide doc sync (phase 2)** — updated `vingroup-agent-skills/BACKEND_PLAN.md` and `docs/voicebot_knowledge_base.txt` to align user-facing naming with **Friend + feature surfaces** (`check-in nhanh`, `bài tập ổn định`, `kết nối hỗ trợ`, `dashboard tiến triển`) and set crisis payload display name to `Friend`.

---

## [Unreleased] — Sprint 4 · 2026-04-27

### Added
- **`anonymousShareService.ts`** — `POST /bamboo/send` + `GET /bamboo/inbox` with graceful localStorage fallback when backend endpoint is unavailable; 3 curated mock messages for offline inbox demo.
- **`BambooForestPage.tsx`** (`/serene/bamboo`) — Full anonymous sharing feature: (1) **Composer** with category selector (Lời khích lệ / Chia sẻ / Hỏi đáp), styled textarea, character counter; (2) **Confirmation modal** with 3-item checklist the user must tick before sending (no harmful content / no PII / suitable for strangers) — "Gửi" disabled until all checked; (3) **Dual action** — "Gửi vào dòng suối 🌊" sends to random user, "Đốt an toàn 🔥" discards locally; (4) **Community Guidelines modal** (Info button); (5) **Done/Burn splash** screens; (6) **Inbox tab** with received anonymous messages styled per category. Bamboo forest dark-olive gradient background.
- **`DayDetailSheet.tsx`** (`frontend/src/components/wellness/`) — Framer-motion bottom sheet; opens on MoodCalendar cell tap; shows date, mood emoji, score bar, word chips, journal note; spring entrance animation.
- **`ProgressStats.tsx`** (`frontend/src/components/wellness/`) — 4-stat grid (streak days, weekly check-ins, total sessions, hearts/tim); weekly check-in dot bar with animated fill; integrated into `Reflect.tsx`.

### Changed
- **`MoodCalendar.tsx`** — Added optional `onDayClick(date, score, label)` prop; cells are now `<button>` elements when `onDayClick` provided; tap highlights with scale animation.
- **`Reflect.tsx`** — Integrated `DayDetailSheet` (tapping calendar cells opens day detail); integrated `ProgressStats` section after milestones chips; added `selectedDay` state.
- **`Sidebar.tsx`** — Added "Rừng Trúc" nav item (Leaf icon, `/serene/bamboo`).
- **`paths.ts`** / **`AppRoutes.tsx`** — Registered `/serene/bamboo` route.

---

## [Unreleased] — Sprint 3 · 2026-04-27

### Added
- **`OnboardingFlow.tsx`** — 8-step new-user questionnaire (Splash → Nickname → Gender → Age group → Mental concerns checklist → Stress frequency slider → Sleep schedule time-pickers → Goals); data persisted to `localStorage`; route `/serene/onboarding` wired into `AppRoutes.tsx` + `paths.ts`.
- **`ScreeningFlow.tsx`** — Likert pill UI replaces plain radio buttons; frequency dot indicators (0–3 filled dots per option); animated `AnalyzingLoader` with 3-step message sequence shown while submitting final answer; instrument selection cards with icon + description.
- **`ResultsPage.tsx`** — Dual animated score bars (raw score % + severity %, `motion` fill); per-severity recommendation exercise cards (2 cols); Web Share API share button with clipboard fallback; "Chat with Serene" CTA card at bottom; action buttons upgraded with Lucide icons.
- **`MoodGauge.tsx`** (`frontend/src/components/common/`) — SVG semicircle gauge 1–10; animated spring needle; gradient color track (red→yellow→green); click-to-set + stepper buttons; accessible `role="slider"` attributes.
- **`StreakCelebration.tsx`** (`frontend/src/components/common/`) — Animated modal celebrating consecutive check-in days; S M T W T F S dot circles (amber = done); hearts reward badge; spring scale entrance animation; integrated into `CheckinFlow` summary step.
- **`DateDivider.tsx`** (`frontend/src/components/chat/`) — Date separator between chat messages when day changes (shows "Hôm nay" / "Hôm qua" / formatted date); wired into Chat.tsx message feed via `timestamp` field on `UiMessage`.

### Changed
- **`CheckinFlow.tsx`** — Added `StreakCelebration` modal on submit completion; fixed English "Chat with Mây" button to Vietnamese.
- **`Chat.tsx`** — Added `timestamp?: number` to `UiMessage` type; new user/assistant messages include `Date.now()` timestamp; `DateDivider` rendered between messages on day boundaries.

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
- `Home.tsx`: removes safety gate from CTAs; replaces the 4-card mood row + CTA row with one equal-width 3-mode row (`Check-in nhanh`, `Làm bài sàng lọc`, `Trò chuyện ngay`).
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

## [Unreleased] - Sprint A Phase 5 � 2026-05-07

### Fixed
- Synced ORM column names with Supabase SQL schema: `tone_cam_xuc` -> `assistant_tone` and `muc_do` -> `severity_level`.
- Added missing ORM fields for existing core models: `MoodCheckin.source`, `ConversationMemory.pii_checked/expires_at/source`, `UserProfile.schema_version/last_active_session_id/summary_count`, and `ClinicalProfile.score_source/model_version`.
- Added ORM models for analyst pipeline and safety domains: `SessionSummaryArchive`, `RiskInferenceLog`, `SessionRiskSnapshot`, `AnalystSignal`, `InsightHypothesis`.
- Replaced dashboard raw SQL in `backend/app/dashboard/service.py` with SQLAlchemy ORM query using `InsightHypothesis`.
- Enforced PostgreSQL schema resolution for Supabase via `search_path=app,public,extensions` in DB session engine config and integration-test fixtures.

### Added
- Alembic migration `0012_sync_core_schema.py` with guarded rename/add-column logic to support both legacy and already-synced DB states.
- Real PostgreSQL integration suite `backend/tests/test_db_integration.py` covering connectivity, table/column consistency, ORM query smoke tests, and write/read flow.
- Real DB fixtures in `backend/tests/conftest.py`: `real_db_url`, `real_engine`, `real_db`.
- Verified `backend/scripts/verify_db_schema.py` execution against Supabase with UTF-8 console mode on Windows.
