# MVP 48h Smoke Report

Ngay chay: 2026-04-19

## Backend Core Tests

- Command: `pytest backend/tests -q`
- Result: PASS
- Summary: `11 passed, 1 warning`

## Frontend Validation

- Command: `npm run lint` (trong `frontend/`)
- Result: PASS
- Command: `npm run build` (trong `frontend/`)
- Result: PASS

## Safety Voice Contract Checks

- `POST /v1/chat/message` non-SOS:
  - Co `intervention` (nullable) trong payload.
  - Khi escalation + consent + no cooldown: tra `intervention.type = proactive_voice`, co `voice.tts_job_id`.
- `POST /v1/chat/message` SOS:
  - Van giu SOS-first finalizer.
  - Co the tra kem `intervention` khi du dieu kien consent/cooldown.
- Voice async:
  - `GET /v1/chat/voice-jobs/{tts_job_id}`: tra status `queued|processing|ready|failed`.
  - `GET /v1/chat/voice-jobs/{tts_job_id}/audio`: tra file audio khi job ready.

## MVP Acceptance Snapshot

- Auth + CSRF frontend/backend: PASS
- Chat functional (happy path + SOS path): PASS
- Proactive voice v1 (consent + cooldown + async queue): PASS
- Route mismatch fix (`/serene/*`): PASS
- Regression backend core tests: PASS
