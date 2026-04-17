# Mô tả kiến trúc: Graph (Neo4j) → Risk Scoring → Multi-agent → Safety

Tài liệu này tóm tắt thiết kế theo hướng **system design**, thống nhất dependency giữa các tầng và làm rõ mức **production-readiness**. Neo4j đóng vai trò pattern + knowledge; điểm số sàng lọc chính thức (PHQ-9/GAD-7) và transcript được coi là **source of truth ở Postgres** (Supabase), khớp `docs/BACKEND_PLAN.md`.

---

# I. Tổng quan kiến trúc (Unified System Perspective)

Hệ thống có thể định nghĩa như sau:

> Một **hybrid AI architecture** kết hợp:

* **Graph-based Knowledge Layer (Neo4j / GraphRAG)** — taxonomy lâm sàng + cạnh hành vi runtime người dùng
* **Probabilistic Risk Modeling (NLP/ML scoring)** — suy luận có độ không chắc chắn
* **Deterministic Safety Layer (rule-based override)** — luật cố định, không phụ thuộc LLM
* **Multi-agent Orchestration (role-specialized agents)** — Supervisor / Analyst / Friend / SOS

Điểm mạnh: **không phụ thuộc một paradigm duy nhất**

* Graph → cấu trúc tri thức lâm sàng + bộ nhớ hành vi (cạnh `FELT`, `EXPERIENCED`, `USED_COPING`, …)
* ML/NLP → suy luận tín hiệu từ hội thoại
* Rule-based → đảm bảo **safety determinism**

Phù hợp mental-health AI vì:

> **Độ an toàn (safety) ưu tiên hơn tối ưu hóa mô hình thuần ML.**

---

# II. Đánh giá Neo4j Layer (Ontology + Behavioral Memory)

## 1. Vai trò trong toàn hệ thống

Neo4j không chỉ là storage:

* **Clinical Knowledge Graph** (DSM-linked taxonomy, triệu chứng, distortion, instrument→item→symptom)
* **User Behavioral Memory Graph** (cạnh runtime: `FELT`, `EXPERIENCED`, `USED_COPING`, …)
* **Nguồn tính năng (feature-like signals)** cho pipeline risk / routing agent

Neo4j cung cấp input cho:

* Intent / safety keyword matching (qua subgraph `SafetyKeyword`, item nặng như PHQ9_Q9, …)
* Behavioral context scoring (mật độ cạnh theo thời gian)
* Clinical signal aggregation (quan hệ `MEASURES`, `HAS_SYMPTOM`, comorbidity, …)

**Lưu ý kiến trúc dự án:** điểm số PHQ-9/GAD-7 *đã chấm* và metadata nhạy cảm khác nằm ở Postgres (`clinical_profiles`, …); graph bổ trợ **cấu trúc** (item→symptom) và **hành vi**, không thay thế bảng điểm chính thức.

---

## 2. Mapping sang RiskScore Pipeline

Ba nhóm tín hiệu chính gắn với graph:

* **Intent**  
  ← `SafetyKeyword`, cạnh tới triệu chứng nguy cơ, item sàng lọc (ví dụ PHQ9_Q9 trong seed)

* **Behavioral context**  
  ← `[:FELT]`, `[:EXPERIENCED]`, `[:USED_COPING]` (có thuộc tính thời gian như `last_seen`, `count`, …)

* **Clinical structure (không nhất thiết = điểm thô)**  
  ← `[:HAS_SYMPTOM]`, `[:MEASURES]`, tiêu chí, đồng mắc — dùng để giải thích và aggregate, kết hợp với dữ liệu Postgres khi cần điểm số

> Neo4j: **stateful behavioral memory + structured clinical context**, không chỉ “static KB”.

---

## 3. Hạn chế & cải tiến

### (1) Temporal versioning cho ontology

* Disorder/symptom theo DSM có thể cần `valid_from` / `valid_to` (hoặc version tag) để audit khi đổi revision.

### (2) Scale trên behavioral edges

* `FELT`, `EXPERIENCED` tăng theo usage → cần **index/constraint** đúng business key, batch write (outbox), và giới hạn query (time window, degree cap).

### (3) Bootstrap modular

* Tách pipeline: ontology seed / clinical CSV / safety / runtime patterns — khớp hướng `neo4j_bootstrap_v3.cypher` + loader riêng.

---

# III. RiskScore System (Inference Layer)

## 1. Hạn chế mô hình tuyến tính đơn giản

Công thức kiểu tổng có trọng số:

$$
\text{RiskScore} = \sum_i w_i \cdot \text{signal}_i
$$

dễ gây **dilution effect**, nguy hiểm khi một tín hiệu (intent) rất cao nhưng các tín hiệu khác thấp — trái nguyên tắc:

> **Tín hiệu high-risk không được “bình quân” mất mức độ.**

---

## 2. Hướng cải tiến (Non-linear + override)

### (a) Intent-dominant

$$
\text{RiskScore} = \max(\text{IntentScore},\ \text{AggregatedSignals}) + \text{Penalty}
$$

### (b) Weighted escalation (gợi ý)

$$
\text{RiskScore} = \alpha \cdot \text{Intent} + (1-\alpha)\cdot \text{Avg}(L,B,C) + \text{Penalty}
$$

* $\alpha$ động (ví dụ $\alpha \ge 0.7$ khi intent cao)
* Penalty khi: red-flag keywords, escalation đột ngột, mật độ distress lặp lại

---

## 3. Intent không chỉ là scalar (Critical)

Đại diện vector 2 chiều (hoặc struct tương đương trong code):

$$
\text{Intent} = (\text{Severity},\ \text{Immediacy})
$$

Phân biệt: nguy cơ cao nhưng chưa tức thời vs cần can thiệp ngay.

---

## 4. Time-series behavioral

* Sliding window trên tin nhắn gần (ví dụ 10–20 turn) — thường lấy từ Postgres `messages`, không nhất thiết chỉ từ graph.
* Time decay trên cạnh / sự kiện:

$$
w(t) = e^{-\lambda \,\Delta t}
$$

Neo4j hỗ trợ qua thuộc tính thời gian trên cạnh (`first_seen`, `last_seen`, …) và truy vấn có `WHERE`/aggregation theo khoảng thời gian.

---

## 5. Clinical signal refinement

Tách rõ trong implementation:

* **Self-reported / scored** (assessment đã chấm) → Postgres
* **Model-inferred** (từ hội thoại) → log riêng, không ghi đè điểm chính thức mà không có luồng xác thực

Bảng Postgres **`risk_inference_log`** lưu các tín hiệu suy luận (phiên bản model, `score`, `detail` JSONB đã kiểm soát); **không** thay thế `clinical_profiles` và không expose cho role `app_user` (chỉ admin/service).

---

# IV. Multi-Agent Orchestration Layer

## 1. Phân tầng

* **Analyst / Supervisor** — inference + routing
* **Friend** — lớp giao tiếp người dùng
* **SOS Handler** — override deterministic, không LLM (theo plan)

---

## 2. Gap: Memory / Context orchestration

Cần một lớp (có thể là service + agent nhỏ, không nhất thiết “agent” LLM riêng) để:

* Truy vấn Neo4j (pattern) + Postgres/pgvector (episodic) + Redis/profile JSON
* Phân biệt chronic vs acute crisis

Nếu thiếu: risk dễ **bias** theo context ngắn hạn.

**Đóng gap dữ liệu (repo):** tầng đọc/ghi được chuẩn hóa trong `docs/BACKEND_PLAN.md` (L1 Postgres + L2 Redis/`user_profiles` + L3 pgvector/Neo4j); risk theo session có bản ghi Postgres (`session_risk_snapshots`) và tùy chọn mirror graph (`Session` / `RiskProfile` + constraint trong `data/neo4j_bootstrap_v3.cypher`).

---

## 3. Pipeline chuẩn hóa (logic)

```text
User Input
   ↓
Signal Extraction (NLP) + structured flags
   ↓
Risk Scoring (non-linear + overrides)
   ↓
Supervisor Decision
   ↓
{ Friend | SOS | Hybrid }
```

---

# V. Safety Layer (Deterministic Control)

## 1. Nguyên tắc

* ML có thể sai; **safety layer không được phép “im lặng sai”** — phải có default an toàn và audit.

Ví dụ pseudo-code (ngưỡng chỉ minh họa, lấy từ config):

```python
if intent_immediacy >= CRISIS_THRESHOLD:  # ví dụ từ policy, không hard-code magic
    crisis_mode = True
```

---

## 2. Parallel intervention model

Khi `crisis_mode`:

* Ổn định cảm xúc
* Attention anchoring / grounding
* Hỗ trợ bên ngoài (hotline, referral metadata)

Kích hoạt **song song** trong response contract (không bắt buộc tuần tự một UI duy nhất).

---

## 3. Penalty & escalation triggers

* Keyword / graph `SafetyKeyword`
* Sudden escalation (delta risk theo window)
* Repeated distress density

---

# VI. Schema & Data Model Extensions

## 1. Session-level risk (gợi ý lưu — có thể Postgres hoặc Neo4j tùy SLO)

Nếu lưu trên node `Session` trong Neo4j (runtime), ví dụ thuộc tính (đặt tên thống nhất với worker):

```cypher
// Ví dụ: cập nhật sau khi Supervisor chốt risk cho session
MATCH (s:Session {session_id: $session_id})
SET s.risk_score = $risk_score,
    s.intent_severity = $intent_severity,
    s.intent_immediacy = $intent_immediacy,
    s.crisis_mode = $crisis_mode,
    s.escalation_flag = $escalation_flag,
    s.risk_updated_at = datetime()
```

**Ghi chú:** `BACKEND_PLAN` ưu tiên Postgres làm source of truth; snapshot risk trên graph là **derived** và phải đồng bộ/outbox nếu cần nhất quán với DB. Bảng Postgres **`session_risk_snapshots`** (trong `data/postgres_additions.sql`) là nơi ghi bản ghi risk đã chuẩn hóa (0–1), không chứa transcript.

---

## 2. RiskProfile node (tùy chọn — explainability)

```cypher
MATCH (s:Session {session_id: $session_id})
MERGE (s)-[:HAS_RISK_PROFILE]->(rp:RiskProfile {profile_id: $profile_id})
SET rp.score = $risk_score,
    rp.components = $components_json,
    rp.created_at = datetime()
```

Phục vụ audit / offline analysis; tránh nhân đôi dữ liệu nhạy cảm không cần thiết.

---

# VII. Tổng kết kỹ thuật

* Ba lớp bổ trợ nhau: **Graph (structure + behavior)**, **ML (inference)**, **Rules (safety)**
* Multi-agent có ranh giới rõ
* Mở rộng production: outbox Postgres → Neo4j, RLS, retention (xem plan)

---

## Ưu tiên hoàn thiện

1. Loại dilution: intent-dominant + penalty + threshold có cấu hình
2. Lớp memory/context: Postgres (messages, pgvector) + Redis profile + Neo4j pattern
3. Chuẩn hóa temporal modeling (window + decay + audit)
4. Bootstrap/ETL modular

---

# VIII. Định hướng tiếp theo

1. Formalize RiskScore trong code (config + tests)
2. FSM crisis mode (rõ transition, idempotency)
3. Cypher/time-series cho behavioral queries có giới hạn chi phí
4. Evaluation: safety metrics, false negative intent

---

# Kết luận

Nền tảng hợp lý về **clinical reasoning**, **kiến trúc polyglot**, và **safety philosophy**. Việc còn lại là **formalization + implementation detail** (RLS, outbox, ngưỡng, observability) để đạt **production-grade reliability**.

---

# IX. Triển khai lớp dữ liệu Postgres (Supabase) — checklist

Phần này gắn với **mục III.5** (tách điểm chính thức vs suy luận mô hình), **mục VI** (risk theo session), và artifact trong repo: `data/postgres_additions.sql`.

## 1. Chốt schema chiến lược

- **Khuyến nghị:** đặt bảng ứng dụng trong schema `public` (đơn giản với Supabase Data API + RLS).
- **Nếu giữ** schema kiểu `extensions.*`: phải cấu hình schema exposed + RLS chặt; tránh nhầm với schema `extensions` hệ thống của Postgres.

## 2. Thứ tự migration (không chạy DDL “context only” từ tool thiết kế)

1. Áp dụng `data/postgres_additions.sql` làm migration hợp nhất cho lớp dữ liệu mở rộng (profile/outbox/archive + risk/inference), sau khi schema lõi đã tồn tại.
2. Không chạy các file migration rời cho risk/inference nữa để tránh trùng object/policy.

## 3. Hai hướng RLS (chọn một cho production Supabase)

| Hướng | Khi nào | Policy điển hình |
|--------|---------|-------------------|
| **A — FastAPI + pool** (repo hiện tại) | Backend set `SET LOCAL app.current_user_id` mỗi transaction | `user_id = current_setting('app.current_user_id', true)::text` |
| **B — Supabase client trực tiếp** | FE gọi PostgREST với JWT user | `user_id = (auth.uid())::text` (chỉ khi `users.user_id` trùng kiểu với `auth.users`) |

Bảng nội bộ (`sync_outbox`, `user_profile_snapshots` nhạy cảm, `risk_inference_log`): chỉ **service role** / RPC backend; không expose qua anon key.

## 4. Extensions

- **`vector`**: bắt buộc cho `conversation_memories.embedding` (kích thước khớp model, ví dụ 1536).
- Tùy chọn: `pgcrypto`, `pg_cron` (retention theo `docs/BACKEND_PLAN.md` §9.2).

## 5. Đồng bộ Neo4j (derived)

- Outbox: `pending → processing → done | failed` (`sync_outbox`).
- Worker chỉ MERGE dữ liệu đã kiểm soát; **không** đẩy `crisis_logs`, transcript thô, hay điểm PHQ/GAD thô sang graph.
- Snapshot risk trên node `Session` / `RiskProfile` (mục VI) là **derived**; nếu cần nhất quán với Postgres, mirror từ `session_risk_snapshots` hoặc payload outbox đã mask.

## 6. Smoke test tối thiểu

- RLS: user A không đọc dữ liệu user B.
- Outbox: insert → worker → `status = done`.
- Neo4j: runtime + seed khớp `data/neo4j_bootstrap_v3.cypher` / tests integration.