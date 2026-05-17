# Dashboard Insight Pipeline Audit

Date: 2026-05-17

## Context

Serene.AI should not evaluate or present the Internal Analyst Agent as a user-facing chatbot. The analyst layer should create structured, evidence-backed signals; user-facing dashboard copy must pass through safe backend contracts before the frontend renders it.

## Existing Source Tables And APIs

| Layer | Current source | Useful fields observed | Current gap |
|---|---|---|---|
| Mood check-ins | `mood_checkins`, `/checkin/quick`, `/dashboard/checkin-history` | `mood_score`, `mood_label`, `emotions`, `triggers`, `time_bucket`, `logged_date`, `note.extra.sleep_hours` | Quick check-in did not honor explicit morning/evening slot; sleep is stored as check-in metadata, not a dedicated table. |
| Nutrition | `nutrition_meal_checkins` | `meal_slot`, `items_text`, `meal_time`, `created_at` | Dashboard did not convert meals into basic nutrition tags or energy observations. |
| Sleep | `mood_checkins.note.extra.sleep_hours` after this patch also `sleep_start`, `wake_time` | `sleep_hours`, `sleep_start`, `wake_time` | No dedicated sleep check-in model yet; analysis is intentionally conservative. |
| Chat intensity | `conversations` | `message_count`, `last_message_at`, `summary` | There is no direct real-world-contact signal, so high app usage is only a proxy and must be worded cautiously. |
| Memories/profile | `user_profiles.profile_data` | `trigger_tags`, `emotion_counts`, `coping_history` | Earlier cards counted events but did not connect them to actionable interpretation. |
| Screening | `clinical_profiles` | `phq9_score`, `gad7_score`, `dass21_scores`, `mdq_positive`, `pcl5_score` | Screening scores were not converted into safe, non-diagnostic dashboard interpretation. |
| Analyst/safe insights | `insight_hypotheses`, `/dashboard/safe-insights` | `title`, `user_safe_summary`, `evidence_count`, `confidence`, `severity_band` | Existing rows often contained generic copy such as "Tin hieu gan day" and repeated safety disclaimers without insight. |

## Placeholder Sources Found

| Code path | Issue |
|---|---|
| `backend/app/dashboard/service.py::_fetch_hypothesis_insights` | Fallback title used "Tin hieu gan day"; old rows with placeholder summaries were rendered if they passed safety checks. |
| `backend/app/dashboard/service.py::_profile_insights` | Heuristic cards used generic trigger/emotion/coping language and repeated "Serene chi coi day la tin hieu ban dau". |
| `backend/app/dashboard/service.py::_build_wellness_dimensions` | Lifestyle cards summarized counts but did not explain sleep, nutrition, real-world connection, or what action should follow. |
| `frontend/src/services/dashboardService.ts` | Reflect dashboard composed cards client-side from several endpoints, so backend insight contracts were partially flattened before rendering. |
| `frontend/src/components/dashboard/LifestyleRhythmPanel.tsx` | The panel rendered "Co the/coping" style language and did not prefer safe backend insight cards when those existed. |
| `frontend/src/components/dashboard/PatternGroupCards.tsx` | Cards rendered summary text but hid interpretation, missing data, and recommended actions from the new contract. |

## Root Cause

The dashboard pipeline had a structural mismatch: the product collected multi-domain data, but the dashboard mostly rendered availability counters and generic safe summaries. Safety filtering existed, but it was being used as a replacement for interpretation rather than as a final guardrail after deterministic evidence analysis.

The highest-impact missing layer was a typed dashboard insight builder that produces user-safe interpretations from concrete evidence counts, windows, missing-data hints, and one to three small next actions.

## Implemented P0 Fixes

| Priority | Fix | Status |
|---|---|---|
| P0 | Filter old placeholder-like safe insight rows before rendering. | Done |
| P0 | Add dashboard card fields for `category`, `interpretation`, `recommended_actions`, and `missing_data`. | Done |
| P0 | Build contextual cards for weekly life state, trigger impact, sleep, nutrition, real-world connection, and screening. | Done |
| P0 | Honor explicit evening check-in slot in quick check-in. | Done |
| P0 | Add minimal sleep input fields and cross-midnight duration calculation in check-in flow. | Done |
| P0 | Make Reflect dashboard render backend interpretation/action/missing-data fields. | Done |
| P0 | Add backend tests for contextual insight behavior and no-diagnosis screening language. | Done |

## Remaining P1/P2 Work

| Priority | Recommendation | Rationale |
|---|---|---|
| P1 | Add a dedicated `sleep_checkins` table with `bedtime`, `wake_time`, `duration_hours`, `sleep_quality`, `local_date`. | Current sleep support is minimal and stored in check-in metadata. A dedicated table improves trend reliability. |
| P1 | Persist generated contextual cards into `dashboard_safe_insights` or `insight_hypotheses` with stable `card_id`. | The current patch can serve safe cards dynamically; persistence would improve auditability and Langfuse-style trace correlation. |
| P1 | Add a real-world connection check-in field. | Current connection analysis infers from high Serene usage and loneliness themes, which is useful but probabilistic. |
| P1 | Add integration test for the live dashboard endpoint with seeded mood, meals, sleep, chat, and screening rows. | Unit tests cover analyzers; endpoint-level regression should lock the full contract. |
| P2 | Replace legacy mojibake strings in dashboard frontend files. | Some files display UTF-8 incorrectly in PowerShell output; rendered app may be fine, but source hygiene should be normalized in a separate encoding-safe patch. |

## Safety Notes

The updated insight layer uses screening language such as "ket qua sang loc" and "khong phai chan doan" rather than diagnostic conclusions. It does not expose raw transcripts, clinical notes, risk indicators, internal rationale, or raw model scores to the frontend.
