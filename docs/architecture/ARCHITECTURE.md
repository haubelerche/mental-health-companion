# Serene.AI — System Architecture

> Source of truth: [`docs/product/PRD.md`](../product/PRD.md) §6–§8.  
> This document is a human-readable summary for onboarding and review. On any conflict, PRD wins.  
> Last updated: 2026-05-17

---

## 1. Tổng quan

Serene sử dụng kiến trúc **backend-centered, safety-first**. Frontend là display layer thuần túy — không sở hữu safety logic, reward, persona unlock, crisis decisioning hay TTS dedup.

```text
User
  → Frontend (React 19 / TypeScript / Vite)
  → Backend API (FastAPI / Python 3.11)
  → Input Normalization + PII Masking
  → Safety Gate                  ← chạy trước mọi LLM call
       ├── Crisis / SOS  → Safety Agent → controlled crisis payload
       └── Non-crisis    → Risk Router
               ├── Simple support     → Friend Agent
               └── Needs insight      → Analyst Agent → Friend Agent
  → Output Validator
  → Response
  → Async workers: memory, TTS, dashboard rollup, notification, eval logs
```

---

## 2. Stack

### Backend

| Layer | Công nghệ |
|---|---|
| Language / Runtime | Python 3.11 |
| Web Framework | FastAPI (async) |
| AI Orchestration | LangGraph-style StateGraph |
| LLM | OpenAI-compatible (GPT-4o / GPT-4o-mini) |
| Database chính | PostgreSQL 15 + pgvector |
| Cache / Queue | Redis |
| Outbox / Workers | Background worker queue (TTS, memory, rollup, notification) |
| Observability | Langfuse traces + python-json-logger + Prometheus metrics |
| Auth | JWT (PyJWT) + OAuth2 (Google) |
| Migrations | Alembic |
| Testing | pytest (901 tests) |

### Frontend

| Layer | Công nghệ |
|---|---|
| Framework | React 19 + TypeScript |
| Build | Vite (`tsc -b && vite build`) |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Realtime | Server-Sent Events (SSE) |
| HTTP | Single `httpClient.ts` layer — no direct backend calls from components |

### Infrastructure

| Layer | Công nghệ |
|---|---|
| Deploy | Railway (backend + PostgreSQL + Redis) |
| Frontend Deploy | Vercel |
| CI | GitHub Actions (pytest + frontend lint/build) |

---

## 3. Agent Runtime

Hệ thống có đúng ba vai trò agent:

| Agent | User-facing | Trách nhiệm |
|---|:---:|---|
| **Friend Agent** | ✓ | Trò chuyện, phản hồi cảm xúc, áp dụng persona/style, viết câu trả lời cuối cùng trong normal flow. |
| **Analyst Agent** | ✗ | Phân tích dữ liệu hội thoại, mood, screening, meal, memory; tạo structured `AnalystBundle`. Không viết response cho user. |
| **Safety Agent** | ✓ qua payload | Xử lý high-risk/SOS, de-escalation, voice grounding, hotline/referral, ghi crisis log + audit log. |

Mọi thành phần còn lại (screening, persona router, reward, memory, dashboard, resource, TTS, meme, notification) là **Service / Router / Worker** — không phải agent có danh tính riêng.

### Kiến trúc bị từ chối (không triển khai)

- Năm agent độc lập user-facing.
- Persona-specific agent có memory hoặc safety policy riêng.
- LLM-generated crisis policy (LLM chỉ được viết `CrisisInterventionPlan` sau khi Safety Gate kích hoạt deterministic).
- Chẩn đoán hoặc xác suất rối loạn user-facing.
- Frontend sở hữu safety, reward, unlock, wallet hoặc TTS dedup.

---

## 4. Safety Gate

Safety Gate là **deterministic rule-based layer**, chạy trước mọi LLM call:

```text
Input
  → Input Normalization + PII Masking
  → Safety Gate
       ├── SOS / high-risk  → bypass normal flow → Safety Agent
       └── Normal           → Router → Friend Agent (± Analyst)
```

- Safety override thắng mọi persona, reward, voice và style.
- Crisis turn không gọi Analyst, không gọi normal Friend Agent.
- Kết quả phải ghi `CrisisLog` + `AdminAuditLog`.

---

## 5. Advisor-assisted Analyst Pipeline

Analyst Agent gọi các advisor chuyên biệt để phân tích sâu. Advisor không phải agent user-facing và không viết câu trả lời cuối cùng.

| Advisor | Nguồn dữ liệu | Output |
|---|---|---|
| Screening Advisor | PHQ-9 / GAD-7 | Severity band, trend, caveat không chẩn đoán |
| Deep Screening Advisor | DASS-21, MDQ, PCL-5 | Stress profile, mood-variation signal, trauma signal, confidence |
| Mood Advisor | Mood check-in | Mood trend, trigger, volatility |
| Lifestyle Advisor | Meal, sleep, onboarding | Pattern ăn/ngủ/năng lượng |
| Memory Advisor | Memory cards / session summary | Stressor, coping history, preference |
| Resource Advisor | Resource library + RAG | Coping / resource candidates có provenance |
| Safety Context Advisor | Risk snapshots, crisis logs (safe summary) | Cảnh báo luồng high-risk |

---

## 6. Data Architecture

### Source of truth

| Store | Vai trò |
|---|---|
| **PostgreSQL** | Source of truth duy nhất cho dữ liệu bền vững (user, message, screening, memory, crisis log, insight, reward) |
| **pgvector** | Embedding phục vụ semantic memory, RAG retrieval |
| **Redis** | Cache, rate limit, ephemeral session state, queue coordination |
| **Outbox / Worker** | TTS, memory extraction, dashboard rollup, notification, eval events — async, không chặn request chính |

### Data domains

| Domain | Dữ liệu |
|---|---|
| Identity / Auth | User, consent, auth tokens |
| Conversation | Sessions, messages, summaries, assistant metadata |
| Screening | PHQ-9/GAD-7, DASS-21, MDQ, PCL-5 scores, severity band, timestamp |
| Mood / Lifestyle | Mood check-in, triggers, meal, sleep schedule |
| Memory | Memory cards, audit events, duplicate count |
| Safety | Risk snapshots, crisis logs, admin audit logs |
| Analyst | Structured signals, hypotheses, evidence refs, dashboard-safe insights |
| Resource / RAG | Wellness resources, bookmarks, embeddings |
| Reward / Persona | Wallet, reward events, inventory, persona unlock, selected persona |
| Voice / TTS | TTS jobs, style id, audio status |
| Notification | Push / SSE events |

### Privacy rules

- Raw user text không đưa vào logs/metrics.
- PII phải được mask trước khi lưu vào vùng không cần raw text.
- Crisis logs và risk inference là backend-only.
- Dashboard chỉ đọc insight đã sanitize.
- PCL-5 / MDQ chỉ lưu/hiển thị dạng screening signal — không phải nhãn chẩn đoán.
- External search không nhận raw PII hoặc nội dung crisis cụ thể.

---

## 7. Persona Registry

Persona là **style mode** của Friend Agent — không phải agent riêng, không có memory hay safety policy riêng.

| Persona | Canonical ID | Availability | Guardrail |
|---|---|---|---|
| Dũng | `dung_luong` | Core / mặc định | Meme/hài chỉ dùng khi low-risk |
| Đạt | `dat_le` | Core | Không chẩn đoán, không giảng đạo |
| Hậu | `hau_luong` | Unlockable — 500 Tim | Không tạo phụ thuộc cảm xúc qua voice |

Safety override thắng mọi persona. High-risk / SOS luôn ép về style an toàn.

---

## 8. TTS / Voice

- Text response trả về trước; TTS chạy async (không block chat).
- `CrisisInterventionPlan` có `visible_text` (render lên UI) và `voice_script` (chỉ đọc qua audio element) riêng — không render `voice_script` thành text.
- TTS có trạng thái rõ: `queued → processing → completed / failed / deduped`.
- Dedup theo nội dung + style để tránh audio lặp.

---

## 9. Observability

Mỗi chat turn phải có Langfuse trace gồm:

- Session id ẩn danh, safety decision + reason codes
- Route: `direct / analyst-assisted / crisis`
- Persona / style decision
- Memory cards được dùng
- Advisor được gọi (input đã sanitize + output summary)
- Prompt version, model, latency, token / cost
- Output validator verdict
- Fallback / degradation nếu xảy ra

---

## 10. Sequence Diagrams

Xem thêm: [`docs/architecture/SEQUENCE_DIAGRAMS.md`](./SEQUENCE_DIAGRAMS.md)
