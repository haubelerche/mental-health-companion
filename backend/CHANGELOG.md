# Changelog — Serene

> Format: [Keep a Changelog](https://keepachangelog.com) | Vingroup Engineering

---

## [Unreleased]

### Fixed
- **Evidence-based Reflect insights** — Added first-class `sleep_checkins` and persisted `dashboard_safe_insights`, centralized the safe dashboard builder boundary, added `/dashboard/safe-insights?window=7d|14d|30d`, and rewired Reflect copy toward evidence, interpretation, and next actions without raw clinical/risk fields.
- **Dashboard insight placeholders** — Safe dashboard cards now filter generic placeholder rows and add deterministic, evidence-backed insight cards for weekly life state, trigger impact, sleep, nutrition, real-world connection, and screening results. Reflect dashboard cards now render backend interpretation, missing-data hints, and concrete next actions instead of only generic summaries.
- **Evening check-in and sleep capture** — Quick check-in now honors explicit `time_bucket` values, including evening check-ins, and accepts minimal sleep inputs (`sleep_start`, `wake_time`, computed `sleep_hours`) for dashboard sleep analysis.
- **Chat duplicate text bubbles** — `applyIntervention()` no longer renders `voice_script` as a visible chat bubble when `voice_job_ids` is empty (provider disabled). Removed the `else if (intervention.voice_script)` branch that violated the `visible_text ≠ voice_script` contract.
- **TTS fallback shown as chat text** — `pollVoiceJob()` on timeout/failed/provider_disabled no longer appended `fallbackScript` to messages; removed `fallbackScript` parameter entirely. Failures now only update the `voiceStatus` badge.
- **Chat layout overflow** — `flex-1 min-h-0 overflow-y-auto` on the feed div (was `mb-8`) and `shrink-0` on the input form (was `sticky bottom-15`) prevent message bubbles from clipping behind the input bar.
- **SQLite schema error in all test fixtures** — Added `tables_for_sqlite = [t for t in Base.metadata.sorted_tables if not t.schema]` filter to `create_all` / `drop_all` calls in 12 test files. The `ScreeningAnswers` model introduced in migration 0021 uses `schema="app"` which SQLite does not support.

### Added
- `backend/tests/test_sos_voice_plan.py` — new test file asserting the SOS voice plan contract: `visible_text ≠ voice_script`, no markdown/URLs in `voice_script`, `reply=None` in SOS response, `hotline_cards` non-empty, `CrisisInterventionPlan` schema validation.
- `TestEnqueueVoiceJob` in `test_tts_dedup.py` — integration tests for dedup (`skipped_duplicate`), `provider_disabled` fast-path, and failed-job-allows-retry.

### Added (previous)
- `backend/app/safety/` — centralised safety layer with three distinct concerns:
  - `content_guardrail.py` — shared SOS/diagnosis/harmful/spam pattern library
  - `letter_guardrail.py` — rule-based letter review pipeline (WordCount → SOS → Spam → Content)
  - `output_validator.py` — SafetyOutputValidator for Friend/dashboard/TTS generated text
  - `verdicts.py` — typed LetterSafetyVerdict and OutputSafetyVerdict Pydantic contracts
  - `escalation.py` — outbox bridge routing SOS signals from content surfaces to safety flow
  - `policy.py` — shared constants (min words, daily reward cap, forbidden phrases)
- `LetterReviewEvent` ORM model — immutable audit log for every guardrail run on a therapy letter
- Migration `0020_letter_guardrail_schema` — adds review_status, review_reason_code, content_masked, safety_event_id, reviewed_at to therapy_letters; creates letter_review_events table

### Changed
- `POST /letters` now runs the full letter guardrail pipeline before persistence:
  - Harmful content and SOS signals block delivery; letter persisted as pending_review for audit
  - Approved long letters (>=100 words, safe content) grant 10 Tim via grant_hearts() with idempotency key, capped at 2 rewards/day
  - All runs write a LetterReviewEvent row for traceability
- TherapyLetter model — added review_status (default not_reviewed), review_reason_code, content_masked, safety_event_id, reviewed_at

### Security
- SOS signals in letter content are checked before spam/farming gate — crisis signals cannot be silenced by repetition detection
