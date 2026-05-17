# Serene — System Architecture

**Version:** 2.0 (2026-05-17)  
**Stack:** FastAPI · LangGraph · PostgreSQL/pgvector · Redis · Neo4j · React 19

---

## Tổng quan kiến trúc

Serene sử dụng kiến trúc **Lightweight Multi-Agent** với 3 agent chính được điều phối bởi LangGraph. Mỗi request chat đi qua Safety Gate trước khi vào bất kỳ LLM nào.

```
                           ┌─────────────────────────────────────────────────────┐
                           │                  SERENE BACKEND                     │
                           │                                                     │
  User                     │  ┌──────────┐   ┌────────────┐   ┌──────────────┐  │
  ──────── HTTPS ──────────┼─►│ FastAPI  │──►│ SafetyGate │──►│  LangGraph   │  │
  Browser / Mobile         │  │ Router   │   │ (rule-based│   │  Orchestrator│  │
                           │  └──────────┘   │ determinst)│   └──────┬───────┘  │
                           │       │         └─────┬──────┘          │          │
                           │       │               │ SOS             ▼          │
                           │       │               │          ┌──────────────┐  │
                           │       │               │          │  AnalystNode │  │
                           │       │               │          │  (internal)  │  │
                           │       │               │          └──────┬───────┘  │
                           │       │               │                 │          │
                           │       │               ▼                 ▼          │
                           │       │        ┌────────────┐   ┌──────────────┐  │
                           │       │        │  Safety    │   │  FriendNode  │  │
                           │       │        │  Finalizer │   │  (Serene)    │  │
                           │       │        └────────────┘   └──────────────┘  │
                           │       │                                            │
                           │       ▼                                            │
                           │  ┌──────────────────────────────────────────┐     │
                           │  │              Services Layer               │     │
                           │  │  Memory │ TTS │ Screening │ Notification  │     │
                           │  │  RAG    │ Neo4j Sync │ Outbox Worker      │     │
                           │  └──────────────────────────────────────────┘     │
                           │                                                     │
                           └─────────────────────────────────────────────────────┘
                                    │                    │
                           ┌────────▼────────┐   ┌──────▼──────────┐
                           │   PostgreSQL    │   │     Redis        │
                           │   + pgvector   │   │  (cache/queue)   │
                           └─────────────────┘   └─────────────────┘
                                    │
                           ┌────────▼────────┐
                           │     Neo4j       │
                           │  (derived graph,│
                           │   no PII/msgs)  │
                           └─────────────────┘
```

---

## Các thành phần chính

### 1. Frontend (React 19 + TypeScript + Vite)

```
User Browser
     │
     ├── Chat Interface        → POST /api/v1/chat/message
     ├── Dashboard             → GET  /api/v1/dashboard/*
     ├── Memory Cards          → GET/POST /api/v1/memories/*
     ├── Screening (PHQ/GAD)   → POST /api/v1/screenings/submit
     ├── Resource Hub          → GET  /api/v1/resources/*
     ├── Persona Selector      → PUT  /api/v1/users/persona
     └── SSE Notifications     → GET  /api/v1/notifications/stream
```

Frontend chỉ là **display layer** — không sở hữu bất kỳ logic safety, reward, hay unlock nào.

### 2. FastAPI Backend

| Router | Path | Mô tả |
|---|---|---|
| Chat | `/api/v1/chat/*` | Chat message + history + SSE stream |
| Auth | `/api/v1/auth/*` | JWT + Google OAuth |
| Memories | `/api/v1/memories/*` | Memory cards CRUD |
| Screenings | `/api/v1/screenings/*` | PHQ-9/GAD-7 submit + latest |
| Dashboard | `/api/v1/dashboard/*` | Mood chart, lifestyle, summary |
| Resources | `/api/v1/resources/*` | Resource Hub + YouTube |
| Notifications | `/api/v1/notifications/*` | Push notifications + SSE |
| Voice | `/api/v1/voice/*` | TTS request + audio delivery |

### 3. Safety Gate (Deterministic, Pre-LLM)

```
Mọi request chat → SafetyGate.decide()
                        │
                ┌───────┴────────┐
          SOS trigger?         Normal
                │                │
         SafetyFinalizer     DistressRouter
         (Crisis path)       → AnalystNode?
                                 └── FriendNode
```

**SafetyGate** dùng keyword scoring + distress threshold — **không dùng LLM**. Chạy trong < 100ms. Kết quả quyết định toàn bộ luồng.

**SOS path:** SafetyFinalizer → CrisisInterventionPlanner → CrisisLog + AdminAuditLog + hotline payload. FriendNode **không** được gọi.

### 4. LangGraph Orchestration

```
State: RuntimeState
  ├── user_id, session_id
  ├── messages[]
  ├── safety_tier (low/medium/high/crisis)
  ├── analyst_bundle (AnalystBundle | None)
  ├── persona_mode
  └── routing_history[]

Graph:
  START
    │
  SafetyGate ──── crisis ──────────────► SafetyFinalizer ── END
    │
  DistressRouter
    ├── needs_analyst ───► AnalystNode ──► FriendNode ── END
    └── direct ──────────────────────────► FriendNode ── END
```

### 5. AnalystNode (Internal, không user-facing)

Nhận `messages[]` → trả `AnalystBundle`:
- `distress_score` (0.0–1.0)
- `risk_label` (low/medium/high)
- `emotion_clusters[]`
- `coping_suggestions[]`
- `resource_context`

`AnalystBundle` chỉ đi vào `FriendNode` system prompt — **không bao giờ** xuất hiện trong user-facing response.

### 6. FriendNode (Serene Conversation Agent)

- Nhận context từ AnalystBundle + conversation history + persona mode
- Gọi LLM (GPT-4o) với system prompt Serene
- Áp dụng `_sanitize_assistant_reply()` trước khi trả về
- Sinh `CrisisInterventionPlan` (visible_text + voice_script) khi cần

### 7. Services Layer

| Service | Mô tả |
|---|---|
| `memory_service` | CRUD memory cards, long-term summary |
| `tts_service` / `voice_tts_worker` | ElevenLabs queue, dedup signature, không block chat |
| `screening_service` | PHQ-9/GAD-7 scoring + ClinicalProfile update |
| `resource_library_service` | Wellness resources + YouTube integration |
| `notification_service` | SSE push, outbox worker |
| `autocbt_service` | CBT exercise guidance |
| `neo4j_sync` | Pattern graph sync (derived only, no PII) |
| `observability` | JSON logging + Prometheus metrics |

---

## Luồng dữ liệu chính

### Luồng Chat bình thường

```
1. User gửi tin nhắn
2. POST /api/v1/chat/message
3. FastAPI → mask_pii() → SafetyGate.decide()
4. Gate: allow_normal_flow
5. DistressRouter → AnalystNode (nếu cần) → FriendNode
6. FriendNode gọi OpenAI API
7. _sanitize_assistant_reply() → strip clinical language
8. Response trả về user (visible_text)
9. Async: TTS queue, memory update, Neo4j sync
```

### Luồng SOS

```
1. User gửi tin nhắn nguy hiểm
2. SafetyGate.decide() → safety_finalize
3. SafetyFinalizer kích hoạt
4. CrisisInterventionPlanner sinh crisis payload
5. CrisisLog + AdminAuditLog ghi ngay (sync)
6. Response: de-escalation text + hotline VN
7. TTS: voice_script riêng biệt (không giống visible_text)
8. Crush persona bị vô hiệu hóa
```

### Luồng TTS

```
1. FriendNode sinh response
2. Outbox worker nhận TTS job (async)
3. LLM sinh voice_script (background)
4. ElevenLabs synthesize audio
5. Dedup: hash(voice_script + style_id) → skip nếu trùng
6. Audio URL trả về qua SSE / polling
```

---

## Database Schema (tóm tắt)

### PostgreSQL (Source of Truth)

| Table | Mô tả |
|---|---|
| `users` | Auth, profile, persona preference |
| `sessions` | Chat sessions + checkpointing |
| `messages` | Conversation history (PII masked trước lưu) |
| `memory_cards` | Long-term memory entries |
| `clinical_profiles` | PHQ-9/GAD-7 scores, severity_band |
| `crisis_logs` | SOS events (admin-only access) |
| `admin_audit_logs` | Mọi hành động safety |
| `memory_embeddings` | pgvector embeddings cho RAG |
| `tts_jobs` | TTS queue + dedup signature |
| `outbox_events` | Async side-effects queue |
| `wellness_resources` | Resource Hub content |
| `notifications` | Push notification records |

### Neo4j (Derived, No PII)

Chỉ lưu **pattern graph** được dẫn xuất từ PostgreSQL:
- `:MemoryNode` — concept nodes (không raw text)
- `:EmotionPattern` — emotion cluster references  
- `:TopicEdge` — liên kết concept

Neo4j **không được** lưu: raw messages, PII, crisis logs, clinical assignments.

---

## Invariants bắt buộc

1. **SafetyGate chạy trước mọi LLM call** — không có exception
2. **SOS bypass toàn bộ normal flow** — FriendNode không xử lý crisis turns
3. **AnalystNode không bao giờ nói chuyện với user** — output chỉ là AnalystBundle
4. **Không chẩn đoán** — không emit "bạn bị X", không disorder probability
5. **mask_pii() trước mọi DB write** chứa free-text user
6. **TTS không block chat response** — async queue
7. **Crush persona = OFF khi high-risk state**
8. **Frontend không sở hữu safety logic** — chỉ display
