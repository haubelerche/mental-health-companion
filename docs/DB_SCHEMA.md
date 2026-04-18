# DB Schema

**Stack:** PostgreSQL 15 + pgvector extension  
**Ngày:** 2026-04-12 | **Phiên bản:** 1.2

---

## 1. ER Diagram
<img width="6951" height="3257" alt="csdl" src="https://github.com/user-attachments/assets/85e81523-078f-4029-883f-08ad230acc0c" />


## 2. Danh sách Tables

### 2.1 `users` — Tài khoản người dùng

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `user_id` | VARCHAR(50) | PK | Hashed ID, không bao giờ là email |
| `display_name` | VARCHAR(255) | NOT NULL | Tên hiển thị |
| `email` | VARCHAR(255) | UNIQUE NOT NULL | Email đăng nhập |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash |
| `disclaimer_accepted` | BOOLEAN | DEFAULT FALSE | Bắt buộc tick khi signup |
| `analytics_opt_in` | BOOLEAN | DEFAULT FALSE | Quyền dùng data cho analytics |
| `data_retention_days` | INTEGER | DEFAULT 90 | Số ngày giữ dữ liệu |
| `is_active` | BOOLEAN | DEFAULT TRUE | Soft disable account |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `last_active` | TIMESTAMP | DEFAULT NOW() | Cập nhật mỗi lần request |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Cập nhật khi sửa profile (display_name, email, v.v.) — dùng cho audit trail |

> ⚠️ **`data_retention_days` — Không tự enforce:** Trường này chỉ là metadata. Cần một scheduled job (pg_cron hoặc external cron) thực sự xóa dữ liệu sau N ngày. **GDPR compliance gap** cho đến khi job tồn tại và được kiểm thử.

---

### 2.2 `refresh_tokens` — Auth token store

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `token_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `token_hash` | VARCHAR(255) | NOT NULL | SHA-256 của refresh token thực |
| `ip_address` | VARCHAR(45) | | IP khi issued |
| `expires_at` | TIMESTAMP | NOT NULL | TTL 30 ngày |
| `revoked_at` | TIMESTAMP | NULLABLE | Set khi logout |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

> Token thực lưu trong httpOnly cookie. DB chỉ lưu hash để validate và revoke.

---

### 2.3 `conversations` — Phiên chat

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `session_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `message_count` | INTEGER | DEFAULT 0 | Cập nhật mỗi lượt chat |
| `started_at` | TIMESTAMP | DEFAULT NOW() | |
| `last_message_at` | TIMESTAMP | DEFAULT NOW() | |
| `deleted_at` | TIMESTAMP | NULLABLE | Soft delete |
| `hard_deleted_at` | TIMESTAMP | NULLABLE | GDPR hard delete |
| `anonymous_summary` | JSONB | NULLABLE | Giữ 90 ngày sau soft delete — chỉ chứa thống kê ẩn danh (số turn, tone), không có nội dung |

> **`anonymous_summary` JSON schema:** `{ "turn_count": <int>, "dominant_tone": "<string|null>", "had_sos": <bool> }`. Không có field nào khác — validate tại app layer trước khi ghi để đảm bảo queryability.

---

### 2.4 `messages` — Tin nhắn

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `message_id` | VARCHAR(50) | PK | |
| `session_id` | VARCHAR(50) | FK → conversations | |
| `user_id` | VARCHAR(50) | FK → users | **Load-bearing cho RLS policy**; cũng tối ưu query — KHÔNG xóa cột này |
| `role` | VARCHAR(20) | CHECK IN ('user','assistant') | |
| `content` | TEXT | NOT NULL, MAX 2000 chars | PII-masked trước khi lưu |
| `tone_cam_xuc` | VARCHAR(20) | NULLABLE | ho_tro / xac_nhan / vui_tuoi / lam_diu |
| `sos_triggered` | BOOLEAN | DEFAULT FALSE | True nếu tin nhắn này kích hoạt SOS |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

---

### 2.5 `mood_checkins` — Mood hàng ngày

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `checkin_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `mood` | VARCHAR(50) | NOT NULL | peaceful / melancholic / radiant / restless / stressed / okay |
| `emoji` | VARCHAR(10) | NULLABLE | |
| `note` | TEXT | NULLABLE | Ghi chú tự do |
| `logged_date` | DATE | NOT NULL | Ngày theo UTC+7 — unique per user |
| `logged_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | NULLABLE | Set khi PATCH |

> UNIQUE constraint: `(user_id, logged_date)` — enforce 1 checkin/ngày.
>
> ⚠️ **Timezone:** `logged_date` là ngày theo **UTC+7**, nhưng PostgreSQL `DATE` không có timezone. Việc convert UTC → UTC+7 phải xảy ra **ở application layer** trước khi INSERT. DB constraint chỉ enforce uniqueness trên giá trị DATE đã nhận — không tự convert timezone.

---

### 2.6 `clinical_profiles` — Điểm lâm sàng tích lũy

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `profile_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users, UNIQUE | 1 profile per user |
| `phq9_score` | INTEGER | NULLABLE, 0–27 | Tính bởi Analyst agent ngầm |
| `gad7_score` | INTEGER | NULLABLE, 0–21 | |
| `phq9_coverage` | JSONB | DEFAULT '{}' | Câu nào đã được ánh xạ |
| `gad7_coverage` | JSONB | DEFAULT '{}' | |
| `crisis_level` | INTEGER | DEFAULT 0, 0–5 | muc_do_khung_hoang hiện tại |
| `last_scored_at` | TIMESTAMP | NULLABLE | |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | |

> Không bao giờ expose score thô ra FE user — chỉ dùng nội bộ và B2B dashboard.

---

### 2.7 `crisis_logs` — Sự kiện SOS

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `log_id` | VARCHAR(50) | PK | |
| `session_id` | VARCHAR(50) | FK → conversations | |
| `user_id` | VARCHAR(50) | FK → users | Hashed, không PII |
| `muc_do` | VARCHAR(20) | NOT NULL | vua / cao / tuc_thoi |
| `context_summary` | TEXT | NULLABLE | Tóm tắt ẩn danh, không raw content |
| `reviewed` | BOOLEAN | DEFAULT FALSE | Admin đã review chưa |
| `triggered_at` | TIMESTAMP | DEFAULT NOW() | |
| `reviewed_at` | TIMESTAMP | NULLABLE | |
| `reviewed_by` | VARCHAR(50) | NULLABLE | admin_id |

> ⚠️ **`context_summary` — Không có DB-level enforcement:** Assertion "không raw content" chỉ là documentation. App layer **phải** sanitize (strip PII) trước khi ghi. Integration test `T-CRISIS-CTX-SANITIZE` là bắt buộc. Cân nhắc encrypt column này at-rest riêng biệt với main tablespace.

---

### 2.8 `journal_entries` — Nhật ký

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `journal_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `prompt_id` | VARCHAR(50) | FK → journal_prompts, NULLABLE | Null nếu tự viết |
| `content` | TEXT | NOT NULL, MAX 10000 chars | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | NULLABLE | Set khi PATCH |
| `deleted_at` | TIMESTAMP | NULLABLE | GDPR soft delete — parity với conversations |

---

### 2.9 `journal_prompts` — Gợi ý viết journal

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `prompt_id` | VARCHAR(50) | PK | |
| `text` | TEXT | NOT NULL | Nội dung gợi ý |
| `is_active` | BOOLEAN | DEFAULT TRUE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

---

### 2.10 `resources` — Thư viện nội dung

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `resource_id` | VARCHAR(50) | PK | |
| `category` | VARCHAR(50) | NOT NULL | meditate / sleep / music / work_study / wisdom / movement |
| `title` | VARCHAR(255) | NOT NULL | |
| `description` | TEXT | NULLABLE | |
| `format` | VARCHAR(20) | NOT NULL | audio / video / article |
| `duration_sec` | INTEGER | NOT NULL | |
| `storage_key` | VARCHAR(500) | NOT NULL | CDN object key (không phải full URL — presign khi serve) |
| `thumbnail_key` | VARCHAR(500) | NULLABLE | |
| `tags` | JSONB | DEFAULT '[]' | |
| `is_active` | BOOLEAN | DEFAULT TRUE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

---

### 2.11 `bookmarks` — Nội dung đã lưu

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `bookmark_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `resource_id` | VARCHAR(50) | FK → resources | |
| `bookmarked_at` | TIMESTAMP | DEFAULT NOW() | |

> UNIQUE constraint: `(user_id, resource_id)`.

---

### 2.12 `play_events` — Tracking nghe/xem

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `event_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `resource_id` | VARCHAR(50) | FK → resources | |
| `event` | VARCHAR(20) | CHECK IN ('started','paused','completed') | |
| `duration_sec` | INTEGER | NOT NULL, ≥ 0 | Thực tế nghe bao lâu |
| `percent` | INTEGER | CHECK 0–100 | % hoàn thành |
| `tracked_at` | TIMESTAMP | DEFAULT NOW() | |

> **Analytics semantics:** Nhiều sự kiện `started` cho cùng `resource_id` trong một session là **intentional** (analytics "re-start after pause"). Client-side duplicate fires có thể được phân biệt bằng `tracked_at` delta < 1s. Không có deduplication ở DB layer.

---

### 2.13 `conversation_memories` — Long-term memory (pgvector)

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `memory_id` | VARCHAR(50) | PK | |
| `user_id` | VARCHAR(50) | FK → users | |
| `session_id` | VARCHAR(50) | FK → conversations ON DELETE SET NULL, NULLABLE | Memory sống sót sau khi conversation bị hard-delete |
| `content` | TEXT | NOT NULL | Event summary đã PII-masked |
| `memory_type` | VARCHAR(50) | | emotion / preference / fact / topic / goal |
| `embedding` | vector(1536) | NOT NULL | text-embedding-3-small |
| `importance_score` | FLOAT | 0.0–1.0 | |
| `confidence` | FLOAT | 0.0–1.0 | |
| `is_deleted` | BOOLEAN | DEFAULT FALSE | |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

> Row-Level Security bật — mỗi user chỉ đọc được memory của chính mình.

---

### 2.14 `admin_audit_log` — Audit trail admin

| Field | Type | Constraint | Mô tả |
|---|---|---|---|
| `audit_id` | BIGSERIAL | PK | Auto-increment |
| `admin_id` | VARCHAR(50) | NOT NULL | |
| `action` | VARCHAR(100) | NOT NULL | GET_CRISIS_LOGS / GET_DASHBOARD / etc. |
| `resource_accessed` | VARCHAR(255) | | Endpoint + params |
| `ip_address` | VARCHAR(45) | NOT NULL | |
| `metadata` | JSONB | DEFAULT '{}' | |
| `timestamp` | TIMESTAMP | DEFAULT NOW() | |

> Append-only — không có UPDATE/DELETE trên bảng này.

---

## 3. Data Pipeline

```
Nguồn dữ liệu                   Cách thu thập            Lưu vào
─────────────────────────────────────────────────────────────────
User messages (chat)        →   REST POST /chat/message  →  messages + conversation_memories
Mood daily check-in         →   POST /mood/checkin       →  mood_checkins
Journal entries             →   POST /reflect/journal    →  journal_entries
Resource play tracking      →   POST /play-event         →  play_events
Clinical scores (implicit)  →   Analyst agent (async)    →  clinical_profiles
Crisis events               →   SOS rule-based (sync)    →  crisis_logs
Admin actions               →   Middleware hook           →  admin_audit_log
Resources (seed data)       →   Manual / curated CSV     →  resources + journal_prompts
```

**Dữ liệu thật không cần ở Gate 2** — xem Mock Data ở mục 4.

---

## 4. Mock Data

### users

| user_id | display_name | email | disclaimer_accepted | created_at |
|---|---|---|---|---|
| `usr_a1b2c3d4e5` | Minh Anh | `minh.anh@example.com` | TRUE | 2026-04-01T08:00:00Z |
| `usr_f6g7h8i9j0` | Tiến Đạt | `tien.dat@example.com` | TRUE | 2026-04-03T14:22:00Z |

---

### mood_checkins

| checkin_id | user_id | mood | emoji | note | logged_date |
|---|---|---|---|---|---|
| `mc_001` | `usr_a1b2c3d4e5` | stressed | 😮‍💨 | Deadline đồ án dồn hết tuần này | 2026-04-10 |
| `mc_002` | `usr_a1b2c3d4e5` | okay | 😐 | Nộp xong rồi, nhẹ hơn | 2026-04-11 |
| `mc_003` | `usr_f6g7h8i9j0` | melancholic | 😔 | Không rõ tại sao buồn | 2026-04-10 |

---

### conversations

| session_id | user_id | message_count | started_at |
|---|---|---|---|
| `sess_xyz001` | `usr_a1b2c3d4e5` | 8 | 2026-04-10T23:00:00Z |
| `sess_xyz002` | `usr_f6g7h8i9j0` | 4 | 2026-04-11T01:15:00Z |

---

### messages

| message_id | session_id | role | content | tone_cam_xuc | sos_triggered |
|---|---|---|---|---|---|
| `msg_001` | `sess_xyz001` | user | Cảm thấy hơi bất lực vì bài tập quá nhiều... | NULL | FALSE |
| `msg_002` | `sess_xyz001` | assistant | Nghe có vẻ bạn đang gồng gánh nhiều thứ một lúc. Áp lực kiểu này mệt lắm... | xac_nhan | FALSE |
| `msg_003` | `sess_xyz001` | user | Mình không muốn tiếp tục nữa | NULL | FALSE |
| `msg_004` | `sess_xyz001` | assistant | Mình thấy bạn đang rất khó khăn. Bạn không đơn độc — có thể gọi **1900 1267** (cấp cứu trầm cảm, BV Tâm thần TP.HCM, 24/7) hoặc **115** khi cần cấp cứu y tế. | NULL | TRUE |

> **Semantic của `sos_triggered`:** flag đánh dấu trên **assistant message** IS SOS response, không phải trên user message gây trigger. `msg_003` có `sos_triggered = FALSE` là đúng — SOS rule phát hiện content của `msg_003` rồi sinh ra `msg_004` với flag `TRUE`. Đây là thiết kế cố ý để biết "tin nhắn nào của bot là SOS response."

---

### clinical_profiles

| profile_id | user_id | phq9_score | gad7_score | crisis_level | last_scored_at |
|---|---|---|---|---|---|
| `cp_001` | `usr_a1b2c3d4e5` | 11 | 8 | 1 | 2026-04-10T23:15:00Z |
| `cp_002` | `usr_f6g7h8i9j0` | NULL | NULL | 0 | NULL |

---

### crisis_logs

| log_id | session_id | muc_do | reviewed | triggered_at |
|---|---|---|---|---|
| `cl_001` | `sess_xyz001` | cao | FALSE | 2026-04-10T23:22:00Z |

---

### resources

| resource_id | category | title | format | duration_sec | storage_key |
|---|---|---|---|---|---|
| `res_001` | meditate | Thiền cho người lo âu | audio | 600 | `audio/meditate/anxiety_10min.mp3` |
| `res_002` | sleep | The Midnight Woods | audio | 1800 | `audio/sleep/midnight_woods.mp3` |
| `res_003` | meditate | Thở 4-7-8 | audio | 180 | `audio/breath/478_breathing.mp3` |
| `res_004` | wisdom | Nhận diện suy nghĩ tiêu cực | article | 300 | `article/cbt/negative_thoughts.md` |

---

### journal_prompts

| prompt_id | text |
|---|---|
| `prompt_01` | Hôm nay điều gì khiến bạn cảm thấy tự hào về bản thân? |
| `prompt_02` | Điều gì đang chiếm nhiều năng lượng nhất của bạn tuần này? |
| `prompt_03` | Nếu nói chuyện với bản thân 1 năm trước, bạn sẽ nói gì? |

---

### conversation_memories

| memory_id | user_id | memory_type | content | importance_score |
|---|---|---|---|---|
| `mem_001` | `usr_a1b2c3d4e5` | emotion | [PERSON] đang cảm thấy áp lực về deadline cuối tuần | 0.85 |
| `mem_002` | `usr_a1b2c3d4e5` | fact | [PERSON] hay thức khuya sau 23h khi bị stress | 0.72 |

---

## 5. Indexes & Constraints tóm tắt

```sql
-- Enforce 1 mood checkin per user per day (UTC+7)
ALTER TABLE mood_checkins ADD CONSTRAINT uq_mood_per_day UNIQUE (user_id, logged_date);

-- 1 clinical profile per user
ALTER TABLE clinical_profiles ADD CONSTRAINT uq_clinical_user UNIQUE (user_id);

-- No duplicate bookmarks
ALTER TABLE bookmarks ADD CONSTRAINT uq_bookmark UNIQUE (user_id, resource_id);

-- CHECK constraints cho clinical_profiles (không enforce trong DDL ban đầu)
ALTER TABLE clinical_profiles
    ADD CONSTRAINT chk_phq9 CHECK (phq9_score IS NULL OR (phq9_score >= 0 AND phq9_score <= 27)),
    ADD CONSTRAINT chk_gad7 CHECK (gad7_score IS NULL OR (gad7_score >= 0 AND gad7_score <= 21)),
    ADD CONSTRAINT chk_crisis_level CHECK (crisis_level >= 0 AND crisis_level <= 5);

-- CHECK constraints cho conversation_memories
ALTER TABLE conversation_memories
    ADD CONSTRAINT chk_importance CHECK (importance_score IS NULL OR (importance_score >= 0 AND importance_score <= 1)),
    ADD CONSTRAINT chk_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1));

-- Content length enforcement (TEXT không tự limit — phải CHECK)
ALTER TABLE messages
    ADD CONSTRAINT chk_content_length CHECK (length(content) <= 2000);
ALTER TABLE journal_entries
    ADD CONSTRAINT chk_journal_length CHECK (length(content) <= 10000);

-- CHECK constraints cho messages.role và tone_cam_xuc
-- (documented in §2.4 nhưng thiếu trong DDL ban đầu)
ALTER TABLE messages
    ADD CONSTRAINT chk_role CHECK (role IN ('user', 'assistant')),
    ADD CONSTRAINT chk_tone CHECK (
        tone_cam_xuc IS NULL
        OR tone_cam_xuc IN ('ho_tro', 'xac_nhan', 'vui_tuoi', 'lam_diu')
    );

-- CHECK constraint cho play_events.event
-- (documented in §2.12 nhưng thiếu trong DDL ban đầu)
ALTER TABLE play_events
    ADD CONSTRAINT chk_event CHECK (event IN ('started', 'paused', 'completed'));

-- Performance indexes
-- messages: chat load (mọi lần mở session đều query) + user-level filter
CREATE INDEX idx_messages_session ON messages (session_id, created_at);
CREATE INDEX idx_messages_user ON messages (user_id);

-- mood_checkins: history theo user, sort mới nhất trước
CREATE INDEX idx_mood_user_date ON mood_checkins (user_id, logged_date DESC);

-- crisis_logs: admin review queue — filter unreviewed + sort mới nhất
CREATE INDEX idx_crisis_review ON crisis_logs (reviewed, triggered_at DESC);

-- refresh_tokens: validate token theo user + filter hết hạn
CREATE INDEX idx_token_user_expiry ON refresh_tokens (user_id, expires_at);

-- conversation_memories: non-vector lookup (filter trước khi ANN search)
CREATE INDEX idx_memory_user_active ON conversation_memories (user_id, is_deleted, created_at);

-- play_events: usage analytics theo user + resource
CREATE INDEX idx_play_user ON play_events (user_id, tracked_at DESC);

-- pgvector HNSW index for fast ANN search
CREATE INDEX idx_memory_embedding ON conversation_memories
    USING hnsw (embedding vector_cosine_ops)
    WHERE is_deleted = FALSE;

-- ─────────────────────────────────────────────────────────────────────────────
-- Row-Level Security
-- ─────────────────────────────────────────────────────────────────────────────
-- Quy tắc chung:
--   • current_setting(..., true) suppresses error → trả NULL nếu chưa set
--   • IS NOT NULL guard: tránh trường hợp empty-string cast vượt qua policy
--   • FORCE ROW LEVEL SECURITY: áp dụng cả với table owner (ngăn migration
--     account bypass mà không cần BYPASSRLS). Migration account KHÔNG được
--     cấp BYPASSRLS.
--
-- CONNECTION LIFECYCLE CONTRACT (bắt buộc — vi phạm → RLS isolation bị phá vỡ):
--   • Mỗi transaction PHẢI SET LOCAL app.current_user_id = $user_id
--   • SET LOCAL tự reset khi transaction kết thúc — an toàn với connection pool
--   • Connection pool KHÔNG ĐƯỢC tái sử dụng connection giữa các user
--     mà không reset session vars (SET LOCAL scope đã đủ nếu dùng transactions)
--   • Kiểm tra: integration test T-RLS-EMPTY (app.current_user_id chưa set
--     → tất cả RLS tables phải trả empty result set, không raise error)
-- ─────────────────────────────────────────────────────────────────────────────

-- Helper macro (dùng trong mọi user-scoped policy):
-- current_setting('app.current_user_id', true) IS NOT NULL
--   AND user_id = current_setting('app.current_user_id', true)::text

-- conversation_memories
ALTER TABLE conversation_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_memories FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_memory_isolation ON conversation_memories
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_messages_isolation ON messages
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- mood_checkins
ALTER TABLE mood_checkins ENABLE ROW LEVEL SECURITY;
ALTER TABLE mood_checkins FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_mood_isolation ON mood_checkins
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- journal_entries
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_journal_isolation ON journal_entries
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- conversations
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_conversations_isolation ON conversations
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- bookmarks
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookmarks FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_bookmarks_isolation ON bookmarks
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- play_events
ALTER TABLE play_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE play_events FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_play_events_isolation ON play_events
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- refresh_tokens
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_tokens_isolation ON refresh_tokens
    USING (
        current_setting('app.current_user_id', true) IS NOT NULL
        AND user_id = current_setting('app.current_user_id', true)::text
    );

-- clinical_profiles: user KHÔNG được thấy raw PHQ-9/GAD-7 scores
-- → Revoke SELECT hoàn toàn, chỉ grant các cột safe (crisis_level, updated_at)
-- → Raw scores chỉ dùng nội bộ qua service_role / B2B dashboard
ALTER TABLE clinical_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_profiles FORCE ROW LEVEL SECURITY;
REVOKE SELECT ON clinical_profiles FROM app_user;
GRANT SELECT (profile_id, user_id, crisis_level, updated_at) ON clinical_profiles TO app_user;
-- WRITE PATH: RLS enabled + FORCE với không có policy nào matching cho INSERT/UPDATE
-- → PostgreSQL deny-all by default (safe-by-default). Chỉ service_role (bypass RLS)
--   được ghi clinical scores. Behavior này là intentional nhưng PHẢI được verify bởi
--   integration test T-CP-WRITE-BLOCK (INSERT với app_user phải raise permission error).

-- crisis_logs: KHÔNG expose cho user — chỉ admin đọc/ghi được
-- (session_id + muc_do + triggered_at vẫn là thông tin nhận dạng được)
-- WITH CHECK đảm bảo không role nào khác có thể INSERT crisis log giả.
ALTER TABLE crisis_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crisis_logs FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_crisis_admin_only ON crisis_logs
    FOR ALL
    USING (current_setting('app.current_role', true)::text = 'admin')
    WITH CHECK (current_setting('app.current_role', true)::text = 'admin');

-- admin_audit_log: chỉ admin role mới đọc/ghi được
-- WITH CHECK ngăn mọi role không phải admin INSERT log giả.
ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY rls_audit_admin_only ON admin_audit_log
    FOR ALL
    USING (current_setting('app.current_role', true)::text = 'admin')
    WITH CHECK (current_setting('app.current_role', true)::text = 'admin');

-- Admin audit log: append-only — revoke cả DELETE lẫn UPDATE
-- Revoke từ PUBLIC trước để bảo vệ các role được tạo trong tương lai.
-- (UPDATE có thể dùng để tamper logs, phải chặn)
REVOKE DELETE, UPDATE ON admin_audit_log FROM PUBLIC;
REVOKE DELETE, UPDATE ON admin_audit_log FROM app_user;
```

---

## 6. Required Integration Tests

Danh sách test cases bắt buộc phải tồn tại trước khi deploy schema lên staging/production.

| ID | Test Case | Table | Loại |
|---|---|---|---|
| `T-MOOD-UNIQUE` | Duplicate mood checkin cùng ngày bị reject | `mood_checkins` | Constraint |
| `T-MOOD-TZ` | Boundary UTC vs UTC+7: 23:30 local = ngày trước theo UTC | `mood_checkins` | Edge case |
| `T-MSG-ISOLATION` | User A không đọc được messages của User B qua RLS | `messages` | RLS isolation |
| `T-CP-COLSEC` | `app_user` không SELECT được `phq9_score` / `gad7_score` | `clinical_profiles` | Column-level grant |
| `T-CRISIS-NOADMIN` | Non-admin session không đọc được `crisis_logs` | `crisis_logs` | Admin policy |
| `T-CRISIS-INSERT` | Non-admin không INSERT được vào `crisis_logs` (WITH CHECK) | `crisis_logs` | WITH CHECK |
| `T-CP-WRITE-BLOCK` | `app_user` INSERT vào `clinical_profiles` phải raise permission error | `clinical_profiles` | Write-path deny |
| `T-AUDIT-APPEND` | Admin INSERT thành công; UPDATE/DELETE bị reject | `admin_audit_log` | Append-only |
| `T-MEM-SURVIVE` | Memory row tồn tại sau khi conversation bị hard-delete (`ON DELETE SET NULL`) | `conversation_memories` | FK behavior |
| `T-PHQ9-CHECK` | PHQ-9 score ngoài 0–27 bị reject bởi CHECK constraint | `clinical_profiles` | CHECK constraint |
| `T-MSG-MAXLEN` | Message content > 2000 chars bị reject | `messages` | CHECK constraint |
| `T-RLS-EMPTY` | `app.current_user_id` chưa SET → tất cả RLS tables trả empty result | All RLS tables | IS NOT NULL guard |
| `T-HNSW-PLAN` | ANN search dùng HNSW index, không phải sequential scan (`EXPLAIN ANALYZE`) | `conversation_memories` | Query plan |
| `T-CRISIS-CTX-SANITIZE` | `context_summary` không chứa raw PII — app-layer sanitization test | `crisis_logs` | App layer |

> **T-MOOD-TZ detail:** User ở UTC+7 submit lúc 23:30 local (= 16:30 UTC of the previous calendar day). Backend phải convert sang UTC+7 date trước khi INSERT vào `logged_date`. Test phải mock system clock để verify đúng date boundary.
