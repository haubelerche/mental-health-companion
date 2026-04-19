# AI Test Coverage and Gap Report

Ngay cap nhat: 2026-04-19

## 1) Muc tieu bao cao

- Xac nhan cac tinh nang AI hien tai da co test chuyen sau.
- Doi chieu `docs/` + plan + code de tim cac luong AI con thieu hoac moi o muc roadmap.

## 2) Ket qua test AI hien tai

- Command: `pytest backend/tests -q`
- Result: `24 passed`

## 2.1 Nhom test da cover

### Orchestration and routing
- `backend/tests/test_langgraph_chat.py`
  - Supervisor route happy/greeting
  - Route qua Analyst khi distress cao
  - Analyst cap (`analyst_calls_this_turn`) duoc ton trong

### Safety scoring and SOS gate
- `backend/tests/test_safety_and_sos.py`
  - map distress -> risk level
  - SOS override force critical
  - keyword SOS true/false
  - escalation signal:
    - threshold crossed
    - rapid delta

### Chat AI integration
- `backend/tests/test_chat_router_integration.py`
  - non-SOS chat success
  - SOS bypass LangGraph
  - proactive voice intervention duoc bat khi du dieu kien

### Proactive voice async internals
- `backend/tests/test_proactive_voice.py`
  - fallback script khi khong co OpenAI key
  - cooldown active/remaining
  - parse invalid tts job id
  - normalize iterable audio bytes

### Consent API cho voice
- `backend/tests/test_voice_consent.py`
  - get default consent false
  - set consent persist true
- `backend/tests/test_policies_voice_consent.py`
  - GET `/v1/policies/voice-consent`
  - POST `/v1/policies/voice-consent`

### Golden evaluator + legal-dependent safety flow
- `backend/tests/test_ai_golden_eval.py`
  - golden cases cho `decide_sos`, supervisor routing, escalation signal
- `backend/tests/test_safety_escalate_integration.py`
  - legal gate OFF -> khong enqueue outbound
  - legal gate ON + opt-in + contact -> enqueue outbound request

## 3) Doi chieu docs va tinh trang feature AI

## 3.1 Da khop tot voi docs/plan

- SOS-first gate truoc LangGraph (khop `docs/SEQUENCE_DIAGRAMS.md` Diagram 2/4).
- Non-SOS path van Supervisor -> Analyst -> Friend.
- Proactive voice theo authority Safety layer (khong giao quyen override cho Friend).
- Consent gate + cooldown cho proactive voice.
- Async TTS flow (chat request khong bi block boi ElevenLabs).

## 3.2 Con thieu / chua day du so voi thiet ke tong

### A) Safety orchestration depth
1. **Classifier chuyen biet**:
   - Hien tai distress/escalation dua nhieu vao heuristic/keyword.
   - Chua co model classifier rieng cho self-harm intent va escalation trend theo timestamp.

2. **Bac C/D day du theo `BACKEND_PLAN` §7.9**:
   - Da co scaffolding `POST /v1/safety/escalate` + trusted contact opt-in/legal gate.
   - Chua co telephony/SMS provider thuc te va policy engine theo khu vuc.

### B) Voice pipeline production-hardening
3. **Job queue robustness**:
   - Da co worker process rieng: `python -m app.core.voice_tts_worker`.
   - Da co lease/retry/stale-reclaim o muc MVP.
   - Chua co dead-letter queue va dashboard operational metrics day du.

4. **Audio storage and lifecycle**:
   - Audio dang phuc vu qua local path endpoint.
   - Chua co object storage + signed URL + retention cleanup.

### C) Evaluation and AI quality gates
5. **Offline eval cho prompts**:
   - Chua co benchmark set cho `voice_script` safety quality (length, wording safety, empathy score).

6. **Regression eval cho routing**:
   - Da co bo golden case co ban.
   - Chua mo rong thanh tap 20-50 case da dang theo domain VN.

### D) Frontend AI observability (for AI team handoff)
7. **Realtime event channel**:
   - Da co SSE endpoint: `GET /v1/chat/voice-jobs/{tts_job_id}/events`.
   - Frontend hien tai van poll (chua chuyen qua SSE client).

8. **Voice fallback UX metrics**:
   - Chua ghi metric cho ty le autoplay fail, ty le fallback text.

### E) Spec/doc sync
9. **API_SPEC cap nhat intervention schema**:
   - Da sync `intervention.proactive_voice`, voice-job endpoints, trusted-contact safety endpoints.
   - Con thieu openapi-generated contract check trong CI.

## 4) Khuyen nghi uu tien tiep theo cho AI Engineer

## P0 (ngay lap tuc sau MVP)
- Them contract test cho `intervention` schema (strict keys + nullable behavior).
- Them integration test cho SSE stream client behavior.
- Them dead-letter va metric dashboard cho voice worker.

## P1 (ngan han)
- Them bo test golden cho distress/escalation (20-50 cases).
- Them evaluator tu dong cho quality `voice_script` (safety + empathy constraints).
- Bo sung telemetry: escalation rate, proactive voice trigger rate, cooldown suppression rate.

## P2 (sau khi on dinh)
- Chuyen frontend tu polling sang SSE hoac WebSocket de giam delay UX.
- Trusted-contact outbound workflow thuc te (telephony/SMS provider) khi legal + consent + infra san sang.

## 5) Ket luan

- Cac tinh nang AI cot loi cua MVP (routing, SOS-first, safety ladder, proactive voice async, consent gate) da duoc test va pass.
- He thong da dat muc "functional MVP" cho phan AI.
- Cac gap con lai chu yeu thuoc production-hardening, legal escalation, va evaluator-depth.
