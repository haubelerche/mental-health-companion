# BACKEND_PLAN 
## Thông tin tài liệu

- **Mục đích**: Blueprint backend để triển khai đúng luồng sản phẩm mới (An/Mây/Lửa/La Bàn/Gương), đồng bộ với safety flow, polyglot storage, retention/PII/DR, và contract Neo4j schema v3.
- **Stack chuẩn**: FastAPI + LangGraph + PostgreSQL + Redis + pgvector + Neo4j + Celery.

---

## 1) Nguyên tắc thiết kế backend

1. **User-facing là persona, backend là technical terms**  
   API response có thể trả `agent_display_name` (An/Mây/...) cho UI, nhưng backend vẫn dùng Supervisor/Analyst/Friend/SOS Handler.
2. **Safety-first nhưng không “UI hard block” mặc định**  
   Khi phát hiện nguy cơ, backend trả gói phản hồi de-escalation + hotline/referral metadata để frontend hiển thị song song.
3. **Response nhanh, ghi dữ liệu tách lớp**  
   Theo sequence diagram: trả lời trước, async writes sau (trừ các sync writes bắt buộc).
4. **Postgres là source of truth duy nhất**  
   Redis/Neo4j là derived/cache, có thể degrade an toàn.
5. **PII tối thiểu, khẩn cấp tách riêng, audit append-only**  
   `crisis_logs` và `admin_audit_log` không đi Neo4j.

---

## 2) Backend capability map theo persona sản phẩm

| Persona (UI) | Capability backend | Dịch vụ chính |
|---|---|---|
| **An** (check-in/chào) | Guest session, mood capture, quick assessment orchestration | `welcome-service`, `checkin-service` |
| **Mây** (chat) | Chat orchestration, context recall, de-escalation mode | `chat-gateway`, `langgraph-runtime` |
| **Lửa** (ổn định nhanh) | Grounding/breath recommendation, short intervention plan | `coping-service`, `resource-selector` |
| **La Bàn** (referral) | Hotline payload, counselor/source matching, priority follow-up | `safety-service`, `referral-service` |
| **Gương** (dashboard) | Mood trend, summary timeline, reminders, progress cards | `insight-service`, `profile-service` |

---

## 3) Kiến trúc tổng thể (chuẩn triển khai)

## 3.1 Runtime layers

- **API Layer (FastAPI)**: auth, rate limit, guest/session endpoints, consent endpoints.
- **Orchestration Layer (LangGraph)**: Supervisor -> Analyst -> Friend, SOS bypass.
- **Data Layer L1 (Postgres)**: transactional + RLS.
- **Data Layer L2 (Redis + user_profiles JSONB)**: profile hot-path.
- **Data Layer L3 (pgvector + Neo4j)**: semantic recall + graph insight.
- **Async Layer (Celery + Outbox worker)**: memory extraction, summarizer, Neo4j sync, alerts.

## 3.2 Bounded context

- `identity-context`: user, tokens, consent.
- `conversation-context`: sessions, messages, orchestration metadata.
- `safety-context`: crisis detect, logs, alerts, follow-up flags.
- `insight-context`: profile aggregate, summaries, trends.
- `resource-context`: coping resources, recommendation edges.

---

## 4) Data model hợp nhất (đối chiếu bảng CSDL trong ảnh + tài liệu)

## 4.1 Core transactional tables (L1)

- `users`, `refresh_tokens`
- `conversations`, `messages`
- `mood_checkins`
- `clinical_profiles`
- `crisis_logs`
- `journal_entries`, `journal_prompts`
- `resources`, `play_events`, `bookmarks`
- `admin_audit_log`
- `sync_outbox`

## 4.2 Profile/derived tables

- `user_profiles` (JSONB aggregate, read every turn)
- `user_profile_snapshots` (append-only)
- `session_summaries_archive`
- `conversation_memories` (pgvector embeddings)

## 4.3 Kiểu dữ liệu quan trọng

- `conversation_memories.embedding`: vector(1536), model `text-embedding-3-small`
- `users.user_id`: chuẩn `usr_` + 10 hex
- `messages`: có cờ `is_triggered`/`sos_triggered` theo luồng SOS

## 4.4 Giả định vận hành (đồng bộ triển khai)

- Session idle timeout = 30 phút (trigger summarizer + idle close).
- Summary tối đa 500 ký tự (cân bằng recall vs token).
- Redis cache profile key `profile:{user_id}`, TTL ≈ 30s (freshness vs hit rate).
- `SET LOCAL app.current_user_id = $user_id` trên mỗi request Postgres có RLS (session var thống nhất với schema SQL).
- Neo4j AuraDB Free: giới hạn ~200k nodes / 400k rels; capacity planning theo growth (xem §13.4).
- `user_profiles.profile.session_summaries`: FIFO 50 mục; overflow → `session_summaries_archive`.

## 4.5 Bảng “lưu ở đâu và tại sao”

| Loại dữ liệu | Lưu ở | Không lưu ở | Lý do / trade-off |
|---|---|---|---|
| Raw messages | Postgres `messages` | Neo4j, Redis | ACID, RLS, audit; full-text nặng → dùng pgvector/RAG |
| Clinical scores (PHQ-9, GAD-7) | Postgres `clinical_profiles` | Neo4j, FE cache | Nhạy cảm — RLS/cột; graph chỉ cần symptom label |
| Embedding | `conversation_memories` (pgvector) | Neo4j | Transaction cùng Postgres; HNSW; Aura vector trên graph còn hạn chế |
| Profile aggregate | `user_profiles` JSONB + Redis | File (S3) không làm hot-path | Latency thấp mỗi turn; partial update + GIN; > ~1MB JSONB cần review thiết kế |
| Session summaries (gần) | `user_profiles.profile.session_summaries[]` | Bảng riêng cho hot-path | Một read cùng profile; FIFO |
| Session summaries (cũ) | `session_summaries_archive` | — | Compliance / audit; read thưa |
| Trigger / emotion / coping graph | Neo4j (runtime per user) | Postgres | Pattern, shortest path, gợi ý; eventual consistency (~5s outbox) |
| Knowledge graph lâm sàng (DSM/symptom/instrument) | Neo4j seed | Postgres | Tĩnh + quan hệ phức tạp; seed idempotent |
| Profile version | `user_profile_snapshots` | Redis | Append-only rollback/audit |
| Crisis logs | Postgres `crisis_logs` | Neo4j | Cực kỳ nhạy cảm; SOS rule-based không cần graph |
| Admin audit | Postgres `admin_audit_log` | Mọi nơi khác | Append-only; REVOKE UPDATE/DELETE |

## 4.6 Ba tầng memory (working / short-term / long-term)

### Working memory (in-state, 1 request)

- LangGraph state: `current_user_message`, ~8 `recent_messages` của session hiện tại, `profile_snapshot` từ Redis/Postgres, output Analyst (không persist), `recursion_count` (ví dụ max 3), `crisis_level_current`.
- Supervisor + Analyst đọc; Friend đọc + phản hồi; sau response mới persist L1/L2.

### Short-term memory (session-scoped, Postgres)

- Toàn bộ `messages` của session (persist không giới hạn 8 turn; **8** chỉ là window load vào working memory).
- `mood_checkins` “hôm nay” thường load cùng middleware.

### Long-term memory (cross-session)

1. **Episodic (pgvector):** `conversation_memories` — fact/topic + `memory_type = 'session_summary'`; RAG top-K khi cần recall theo chủ đề.
2. **Semantic / pattern (Neo4j):** cạnh runtime user (`EXPERIENCED`, `FELT`, `USED_COPING`, …) + subgraph kiến thức lâm sàng seed; đọc khi gợi ý can thiệp / cluster triệu chứng (xem §12).
3. **Aggregated profile (JSONB):** traits, summaries (≤50), trigger counts, coping history, safety flags — đọc **mỗi turn** trước orchestration.

Ví dụ truy vấn Neo4j (khớp v3, property `slug` thay cho `label` cũ):

```cypher
MATCH (u:User {user_id: $uid})-[:EXPERIENCED]->(t:Trigger {slug: $trigger_slug})
MATCH (r:Resource)-[:HELPS_WITH]->(s:Symptom)
WHERE EXISTS {
  MATCH (t)-[:MANIFESTS_AS]->(s)
}
RETURN r.resource_id, r.title_vi
LIMIT 5
```

## 4.7 Luồng ghi/đọc chi tiết (đối chiếu worker)

### Write path — message (tóm tắt 7 bước)

1. `POST /v1/chat/message` vào API.
2. Middleware (sync): `SET LOCAL app.current_user_id`, load profile Redis→Postgres, 8 message gần, mood hôm nay, build state.
3. LangGraph: route; crisis bypass; SOS check sau Analyst khi không bypass.
4. Trả response (stream/REST).
5a. **Sync:** transaction `messages` ×2, `conversations`, nếu SOS thì `crisis_logs` + `admin_audit_log`.  
5b. **Async:** `clinical_profiles`, patch `user_profiles` + `DEL profile:{uid}`, `sync_outbox`.  
5c. **Celery (trễ nhẹ):** extract memory → embed → `conversation_memories` + outbox `memory.created`.
6. Outbox worker (~5s batch): `MERGE` Neo4j idempotent, cập nhật trạng thái outbox.
7. Session summarizer (idle 30m / close / batch): PII check → summary ≤500 chars → embed → transaction: memory summary, append profile, archive overflow, snapshot, outbox `session.ended`, invalidate Redis.

### Read path — agent → nguồn

| Agent | Dữ liệu đọc | Nguồn |
|---|---|---|
| Supervisor | `crisis_level`, last 8 messages, mood hôm nay, traits | Redis/`user_profiles`, `messages`, `mood_checkins` |
| Analyst | clinical snapshot, ≤50 summaries, top semantic memories, pattern graph, instrument→symptom map | `user_profiles`, pgvector, Neo4j |
| Friend | traits, last 8, coping history, gợi ý resource/coping | `user_profiles`, `messages`, Neo4j (`HELPS_WITH`, …) |

---

## 5) API plan theo hành trình frontend mới

## 5.1 Guest-first trial (không bắt đăng ký ngay)

### Endpoint

- `POST /v1/guest/session/start`
- `POST /v1/guest/session/heartbeat`
- `POST /v1/guest/choice` (check-in | screening | chat)
- `POST /v1/guest/convert` (guest -> account sau signup)

### Rule backend

- Giới hạn trial bằng cấu hình server-side (`max_duration_sec` hoặc `max_actions`).
- Dùng token guest riêng, không trộn với `users`.
- Cho phép lưu tạm in-memory/Redis; chỉ persist dài hạn khi convert thành account (hoặc policy cho phép).

## 5.2 Welcome + Safety gate (bắt buộc sau mọi nhánh)

- `POST /v1/intake/safety-check`
- Input: 3 câu an toàn ngắn (quá tải / không an toàn / cần hỗ trợ ngay).
- Output:
  - `risk_level` (0-5),
  - `should_route_crisis` (bool),
  - `recommended_next_step`.

## 5.3 Check-in (An)

- `POST /v1/checkin/quick`
- Ghi mood + stress/sleep/study + optional note.
- Trả summary ngắn + next action.
- Sync write bắt buộc: `mood_checkins`, có thể thêm message artifact nếu vào chat context.

## 5.4 Screening flow

- `GET /v1/screenings/catalog`
- `POST /v1/screenings/submit`
- Backend chấm điểm, map severity nội bộ, trả nhãn user-friendly (mild/moderate/high-like).

## 5.5 Chat (Mây)

- `POST /v1/chat/message`
- Quy trình theo Diagram 1:
  - middleware load profile/messages/mood,
  - LangGraph route,
  - response ngay,
  - sync writes,
  - async writes + extraction.

## 5.6 Crisis & referral (La Bàn + Lửa)

- `POST /v1/safety/escalate` (internal)
- `GET /v1/safety/hotlines`
- `GET /v1/referrals/options`
- Response luôn gồm hotline payload để FE render đồng thời trong chat.

## 5.7 Dashboard (Gương)

- `GET /v1/dashboard/overview`
- `GET /v1/dashboard/mood-trend`
- `GET /v1/dashboard/history`
- `GET /v1/dashboard/follow-up`

## 5.8 Consent/policy sau đăng ký

- `POST /v1/auth/signup`
- `GET /v1/policies/current`
- `POST /v1/policies/acknowledge`
- Chặn truy cập core APIs nếu thiếu `policy_acknowledged_at`.

---

## 6) Sequence execution chuẩn (rút từ 3 diagram)

## 6.1 Diagram 1 — message -> agents -> response + async writes

- **Sync (blocking)**:
  - load profile từ Redis (fallback Postgres),
  - load 8 messages gần nhất + mood hôm nay,
  - invoke LangGraph (Supervisor/Analyst/Friend hoặc SOS bypass),
  - commit writes bắt buộc (`messages`, `conversations`, và nếu SOS thì `crisis_logs` + `admin_audit_log`).
- **Async (non-blocking)**:
  - update `clinical_profiles`,
  - update/invalidate `user_profiles`,
  - insert `sync_outbox`,
  - memory extraction + embeddings + outbox memory event.

## 6.2 Diagram 2 — session end summarizer atomic transaction

- Trigger: idle 30m / explicit close / batch đêm.
- Guard:
  - idempotency (`is_already_summarized`),
  - PII detection.
- LLM summary (`<= 500 chars`) + embedding.
- Transaction atomic:
  - insert summary memory,
  - append profile summaries (trim 50),
  - overflow -> `session_summaries_archive`,
  - snapshot profile,
  - outbox `session.ended`,
  - invalidate Redis.
- Outbox worker sync Neo4j theo batch 5s.

## 6.3 Diagram 3 — SOS path

- SOS check xảy ra **trước Friend final response**.
- SOS handler là **rule-based, no LLM**.
- Sync writes bắt buộc:
  - user msg + SOS response msg,
  - `crisis_logs`,
  - `admin_audit_log`,
  - update `user_profiles` safety flags.
- Async alert gửi admin/email/webhook.
- `crisis_logs` **không sync Neo4j**.

---

## 7) Safety behavior mới (khớp FRONTEND_PLAN v2.0)

## 7.1 Tránh hard-stop UI duy nhất

Backend không chỉ trả `sos_fullscreen=true`; cần trả cấu trúc đa phần:

- `conversation_mode`: `de_escalation`
- `hotline_cards[]`: luôn render được ngay
- `grounding_actions[]`: bài thở/5-4-3-2-1
- `referral_options[]`: counselor/nguồn hỗ trợ
- `followup_priority`: true/false

## 7.2 Crisis response contract (đề xuất)

```json
{
  "risk_level": 4,
  "conversation_mode": "de_escalation",
  "agent_display_name": "Mây",
  "assistant_text": "Mình đang ở đây với bạn. Mình muốn giúp bạn an toàn ngay lúc này.",
  "hotline_cards": [
    {"label": "Hotline Ngày Mai", "phone": "1800-599-920"},
    {"label": "Cấp cứu", "phone": "115"}
  ],
  "grounding_actions": [{"id": "grounding_54321"}, {"id": "breath_478"}],
  "referral_options": [{"type": "counselor"}, {"type": "trusted_contact"}],
  "followup_priority": true
}
```

---

## 8) Outbox, idempotency, consistency

- Tuyệt đối dùng outbox, không dual-write Postgres + Neo4j trong 1 request.
- Trạng thái outbox: `pending -> processing -> done|failed`.
- Retry 3 lần exponential; cảnh báo admin khi `failed`.
- Neo4j queries dùng `MERGE` idempotent.
- Cho phép lag ~5s vì graph là derived layer.

---

## 9) Privacy, security, compliance

### 9.1 Nguyên tắc chung

- Mask PII trước khi lưu `messages`.
- `clinical_profiles` khóa select cho `app_user` (chỉ service role đọc đầy đủ).
- `crisis_logs` chỉ admin role.
- `admin_audit_log` append-only (không update/delete).

### 9.2 Retention (mặc định đề xuất — điều chỉnh theo Legal)

| Dữ liệu | Giữ | Sau TTL |
|---|---|---|
| `messages` | `data_retention_days` (vd. 90) | Soft delete → hard delete +30 ngày |
| `conversation_memories` | 365 ngày từ `created_at` | `is_deleted` → purge embedding +30 ngày |
| `session_summaries` trong profile | 50 bản ghi (FIFO) | Overflow → `session_summaries_archive` |
| `session_summaries_archive` | vd. 365 ngày | DELETE theo policy |
| `user_profile_snapshots` | vd. 90 ngày; cap vd. 100/user | DELETE oldest |
| `sync_outbox` | xóa `done` sau vd. 7 ngày | Job định kỳ |
| `crisis_logs` | theo legal (thường giữ lâu) | không auto-delete mặc định |
| `admin_audit_log` | vd. 24 tháng | archive cold storage |
| `play_events` | vd. 180 ngày | aggregate rồi xóa raw |
| `refresh_tokens` hết hạn | vd. 30 ngày | DELETE |
| `mood_checkins` | theo `data_retention_days` | cần cột soft-delete nếu chưa có |
| Redis profile | TTL ~30s | tự hết hạn |

### 9.3 PII masking pipeline

**PII:** tên thật, email, phone, địa danh nhận diện, CMND/CCCD, thông tin y tế nhận diện cá nhân.

| Bước | Action | Owner |
|---|---|---|
| Trước `INSERT messages.content` | Replace tên/email/phone → `[PERSON]`, `[EMAIL]`, `[PHONE]` | App middleware |
| `conversation_memories` | Chỉ từ nguồn đã mask; summarizer verify | Summarizer |
| `crisis_logs.context_summary` | Strip PII, giữ ngữ cảnh lâm sàng | SOS handler |
| `sync_outbox.payload` | IDs + label đã kiểm soát, không raw transcript | Producer |
| `user_profiles.profile` | nickname/initials cho display hint | App |

**Không bao giờ đưa vào Neo4j:** raw message (kể cả masked), email/tên thật, điểm số PHQ/GAD thô (chỉ symptom label nếu cần), crisis logs, secret/token.

### 9.4 GDPR / right to erasure (chuỗi xử lý)

1. `users.is_active = FALSE` + soft-delete các bảng user-scoped.
2. Sau ~30 ngày: hard delete `messages`, `journal_entries`, `mood_checkins` (theo policy).
3. `conversation_memories`: `is_deleted = TRUE`, purge embedding sau buffer.
4. `user_profiles` + `user_profile_snapshots`: DELETE theo user.
5. Neo4j: `DETACH DELETE` subgraph gắn `User {user_id}` và dữ liệu runtime chỉ thuộc user đó.
6. `conversations.anonymous_summary` (nếu có và đã khử danh tính): có thể giữ theo legal/product.
7. `admin_audit_log`: giữ bản ghi pháp lý (không xóa theo user erase thông thường — xác nhận với Legal).

---

## 10) KPI, SLO, monitoring

## 10.1 KPI chức năng

- Safety recall: mục tiêu ~100% cho trigger nguy cơ cao.
- P95 chat response: mục tiêu < 3s ở luồng không SOS.
- Outbox success rate: >= 99.5%.
- Profile cache hit (Redis): >= 80% trong giờ cao điểm.

## 10.2 Logging/observability

- Correlation ID cho mỗi request/session.
- Metrics theo agent branch:
  - Supervisor route distribution,
  - SOS triggers,
  - Analyst loop count,
  - memory extraction latency.
- Dashboard admin cần tách rõ:
  - operational metrics,
  - safety metrics,
  - data sync health.

---

## 11) Kế hoạch triển khai theo phase

## Phase A — Core safety + conversational backbone

- Chat API + LangGraph runtime.
- Safety gate + SOS handler + hotline payload.
- Sync writes + audit log.

## Phase B — Profile intelligence

- `user_profiles` aggregate + Redis cache.
- Summarizer session-end + snapshots.
- Dashboard APIs (Gương) cơ bản.

## Phase C — Semantic/graph enrichment

- pgvector retrieval.
- Outbox worker + Neo4j sync.
- Referral ranking + personalized coping recommendations.

## Phase D — Compliance hardening

- Retention jobs,
- erase workflows,
- access control review,
- DR drill.

---

## 12) Neo4j schema v3 — contract backend / graph worker

**Mục tiêu:** Neo4j 5.x (AuraDB Free ~200k nodes / 400k rels). **Triết lý:** taxonomy là **node + cạnh kiểu hóa**, không dùng một property string làm discriminator đa nghĩa. **Idempotent:** `IF NOT EXISTS` cho index/constraint; seed `MERGE` + `SET` trong bootstrap (chạy lại ghi đè property seed có chủ đích).

### 12.1 Ba tầng tri thức trên graph

```
TẦNG 1 — FOUNDATIONS (:Construct, :PsychProcess, :Term) — đại cương / glossary
        UNDERLIES, PSYCH_BASIS_FOR, RELATES_TO
TẦNG 2 — CLINICAL (:Disorder, :DisorderCategory, :Symptom, :SymptomCategory,
        :Instrument, :Item, :Episode, :DiagnosticCriterion, :Substance,
        :MedicalCondition, :CognitiveDistortion, …)
TẦNG 3 — INTERVENTION & USER (:Resource, :ResourceCategory, :CopingAction,
        :CopingCategory, :Trigger, :Emotion, :SafetyKeyword, :User, :Session,
        :MemoryNode) + GraphRAG (:Agent, :AgentCapability, :Assessment)
```

### 12.2 Node chính (tóm tắt unique key)

| Nhóm | Label | Unique key | Ghi chú triển khai |
|---|---|---|---|
| Foundations | `Construct`, `PsychProcess`, `Term` | `slug` | `name_vi` / `name_en` / `definition_*` |
| Clinical | `Disorder` | `slug` | `icd_code`, `dsm5_code` là thuộc tính (index, không UNIQUE) |
| | `DisorderCategory`, `SymptomCategory`, `Episode`, … | `slug` hoặc `code` | `Symptom`: bỏ property `category` — dùng cạnh `IN_SYMPTOM_CATEGORY` |
| | `Instrument`, `Item` | `code` | Bỏ `instrument_code` trên `Item`; quan hệ `HAS_ITEM` |
| Intervention | `Resource` | `resource_id` | Bỏ `category` — dùng `IN_RESOURCE_CATEGORY` |
| | `ResourceCategory`, `CopingCategory` | `slug` | Phân cấp `SUBCATEGORY_OF` |
| | `CopingAction` | `action_id` | `is_adaptive` (seed) |
| | `Trigger`, `Emotion` | `slug` | Đổi từ `label` (v2) |
| Runtime | `User` | `user_id` | Đồng bộ với Postgres `usr_*` |
| | `Session` | `session_id` | Bỏ `dominant_emotion` string → cạnh `HAS_DOMINANT_EMOTION` |
| | `MemoryNode` | `memory_id` | `memory_type`, `importance` |
| GraphRAG (SECTION 10 bootstrap) | `Agent`, `AgentCapability`, `Assessment` | `slug` / `assessment_id` | Vector index trên `embedding` nếu bật GraphRAG |

### 12.3 Relationship types (nhóm chức năng)

- **Taxonomy (v3.3 typed):** `IN_SYMPTOM_CATEGORY`, `IN_DISORDER_CATEGORY`, `IN_RESOURCE_CATEGORY`, `IN_COPING_CATEGORY`, `SUBCATEGORY_OF` (không dùng `:IN_CATEGORY` đa nghĩa; migration SECTION 11 chuyển đổi).
- **Clinical:** `HAS_ITEM`, `MEASURES`, `CO_OCCURS_WITH`, `HAS_SYMPTOM`, `HAS_EPISODE`, `HAS_CRITERION`, `MANIFESTS_IN`, `DIFFERENTIAL_WITH`, `INDUCED_BY` (substance-induced), `RULE_OUT_SCREEN` (Disorder→MedicalCondition, **sàng lọc / rule-out**, không đọc là “MDD do bệnh cơ thể”), `AMPLIFIES`.
- **Foundations:** `UNDERLIES` (PsychProcess→Construct), `PSYCH_BASIS_FOR` (PsychProcess→Symptom), `RELATES_TO`.
- **Intervention:** `HELPS_WITH` (Resource→Symptom), `IS_RESOURCE`, `TARGETS_SYMPTOM` (CopingAction→Symptom).
- **User/session:** `HAS_SESSION`, `MENTIONS_TRIGGER`, `HAS_DOMINANT_EMOTION`, `EXPERIENCED`, `FELT`, `USED_COPING`, `CONTAINS_MEMORY`.
- **Safety:** `INDICATES`, `FLAGS_ITEM` (bootstrap: chỉ severity cao → ví dụ `PHQ9_Q9`).
- **Bridge:** `MANIFESTS_AS` (Trigger→Symptom), `COMMONLY_TRIGGERS` (Trigger→CognitiveDistortion).
- **GraphRAG / multi-agent (SECTION 10):** `HAS_CAPABILITY`, `HANDLES_DOMAIN`, `EVOKES` (Trigger→Emotion, prior), `CAUSES_SYMPTOM`, `INVOLVES_SUBSTANCE`, `AGGRAVATES_TRIGGER`, `MODULATES_SYMPTOM`, `SUBMITTED_ASSESSMENT`, `USED_INSTRUMENT`, `INCLUDES_ASSESSMENT`.

**Vector index:** tạo trong bootstrap SECTION 10 — `vector.dimensions` khớp model (vd. 1536 + `text-embedding-3-small`). Nếu môi trường không hỗ trợ VECTOR INDEX, tách/tắt block SECTION 10.

### 12.4 Quy tắc chuẩn hóa graph

1. Unique business key = `slug` (lowercase, snake_case, ASCII) cho taxonomy/concept.
2. Tên hiển thị: `name_vi` + `name_en`.
3. Không dùng string discriminator; mọi “category” là node + cạnh typed.
4. Không denormalize nhầm: quan hệ đi qua edge; property chỉ của node.
5. `UNIQUE` constraint trên business key cho mọi label có seed/runtime.

### 12.5 Thứ tự triển khai Neo4j (chuẩn repo hiện tại)

1. `change_schema/migration_v2_to_v3.cypher` — **chỉ khi** còn graph v2 cần nâng cấp.
2. `data/neo4j_bootstrap_v3.cypher` — constraints, index (fulltext + vector SECTION 10), seed cốt lõi (vd. ≥17 `DisorderCategory`, 45 `Disorder` có thể mở rộng CSV), Agent + cạnh GraphRAG.
3. `data/load_data.py` — nạp CSV `data_raw/disorders*.csv` (Aura: không dùng `LOAD CSV` từ `file://`).
4. `change_schema/validate_v3.cypher` — chạy từng block sau nạp.

**Nội dung migration v2→v3 (tóm tắt):** tạo `SymptomCategory` / `ResourceCategory` / `CopingCategory` từ property `category` cũ; link rồi `REMOVE n.category`; đổi `Trigger.label` → `slug`, `Emotion.label` → `slug`; drop index cũ; tạo constraint/index mới. Sau migration mới chạy lại bootstrap.

---

## 13) Disaster recovery & graceful degradation

### 13.1 Neo4j mất / lag

- **Mất:** Friend giảm chất lượng gợi ý graph → fallback `resources` Postgres + rule static; Analyst mất pattern graph → fallback `trigger_tags` trong `user_profiles`; subgraph instrument→symptom có thể fallback dict tạm trong code.
- **Không mất:** chat/messages, profile, outbox `pending` chờ replay.
- **Recovery:** restore Aura backup → re-seed subgraph tĩnh bằng `data/neo4j_bootstrap_v3.cypher` (idempotent) → replay `sync_outbox` trạng thái `pending`/`failed` từ mốc trước sự cố; subgraph runtime user bù dần từ outbox.

### 13.2 Redis mất

- Đọc `user_profiles` trực tiếp Postgres (+20–50ms/turn). Redis chỉ cache — không mất dữ liệu. Pattern: try Redis → catch → Postgres.

### 13.3 Postgres corruption / restore

- Hệ thống dừng theo L1; restore point-in-time từ backup nhà cung cấp.
- `user_profiles` có thể tái tạo một phần từ `user_profile_snapshots`.
- Embedding cũ hơn backup có thể cần regenerate.
- Neo4j subgraph user: nếu **mất đồng thời** outbox chưa apply và backup Postgres cũ → partial loss graph; chấp nhận hoặc replay từ queue nếu còn.

### 13.4 Capacity ~1k active users (ước lượng)

- Aura Free ceiling: kiểm tra tốc độ tạo node/rel từ outbox; giới hạn batch worker; theo dõi count trên Aura console.

---

## 14) Checklist khớp tài liệu nguồn (đã kiểm tra)

- [x] Khớp 3 sequence diagrams về thứ tự sync/async và bypass SOS.
- [x] Khớp kiến trúc dữ liệu: polyglot 3-layer, memory tiers, retention, PII, DR, outbox.
- [x] Khớp contract Neo4j v3 (typed category rels, migration order, GraphRAG SECTION 10).
- [x] Khớp frontend plan mới: trial-first, safety gate, 3 nhánh nhu cầu, policy bắt buộc sau signup.
- [x] Khớp sơ đồ bảng CSDL trong ảnh (`csdl.png`) ở các bảng chính.
- [x] Có tính đến benchmark feature matrix (`image.png`) cho kết nối chuyên gia, theo dõi dài hạn, khả năng mở rộng B2B.

---

## 15) Open decisions cần chốt với Product/Legal

1. Trial limit chính thức: theo **thời gian** hay **số hành động**.
2. Chính sách persist dữ liệu guest trước khi convert account.
3. Ngưỡng `risk_level` dùng để auto-escalate từng bối cảnh (chat/check-in/screening).
4. SLA xử lý follow-up ưu tiên trong mô hình B2B.
5. Danh sách hotline/counselor theo khu vực và chiến lược cập nhật dữ liệu.

