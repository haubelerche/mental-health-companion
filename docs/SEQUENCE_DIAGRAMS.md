# Sequence Diagrams



---

## Diagram 1 — Guest-first vào app → chọn nhu cầu → Safety Gate

Luồng khách mở app không đăng ký, chọn nhu cầu (Check-in / Screening / Chat), gọi API guest session, sau đó qua Safety Gate (`POST /v1/intake/safety-check`): service đánh giá rủi ro; nếu cần hướng crisis thì ghi pre-flag Postgres và trả route + hotline, ngược lại vào flow đã chọn.

**Mô tả luồng (theo hình):**

1. Người dùng mở app **chưa đăng ký** — client gọi `POST /v1/guest/session/start` (và heartbeat nếu cần giữ phiên trial).
2. App hiển thị lựa chọn nhu cầu: **Check-in**, **Screening**, hoặc **Chat** — có thể gọi `POST /v1/guest/choice` để backend ghi nhận nhánh.
3. **Bắt buộc** qua **Safety Gate**: `POST /v1/intake/safety-check` (các câu hỏi ngắn về quá tải / không an toàn / cần hỗ trợ ngay).
4. Backend tính `risk_level`, `should_route_crisis`, `recommended_next_step`.
5. Nếu **cần crisis**: ghi **pre-flag** (Postgres hoặc state guest), trả thêm route an toàn + metadata hotline (không nhét user vào chat “bình thường” mù mờ).
6. Nếu **không crisis**: cho phép vào đúng nhánh đã chọn (check-in / screening / chat) theo `BACKEND_PLAN.md` §5.

![Diagram 1 — Guest-first vào app → chọn nhu cầu → Safety Gate](./images/diagram-01-guest-first.png)

---

## Diagram 2 — Chat message (Mây) → (SOS gate) → LangGraph hoặc crisis → sync writes + async pipeline

Luồng gửi tin nhắn chat: frontend → FastAPI; middleware tải working memory (Redis cache / Postgres); **đánh giá SOS rule-based trước** — nếu không SOS thì LangGraph (Supervisor / Analyst / Friend); nếu SOS thì **bỏ qua LangGraph trong turn đó** và trả payload crisis (Diagram 4); trả response; ghi đồng bộ `messages` / `conversations` trên Postgres; Celery xử lý bất đồng bộ cập nhật profile, memory embedding và `sync_outbox` (nhánh không-SOS).

**Mô tả luồng (theo hình):**

1. Client gọi **`POST /v1/chat/message`** với nội dung tin nhắn và (tuỳ chọn) `session_id`.
2. **Middleware**: `SET LOCAL app.current_user_id`; tải **song song** profile (Redis → fallback Postgres), cửa sổ **~8 tin gần nhất**, mood hôm nay; ghép **state** cho LangGraph **khi và chỉ khi** không vào nhánh SOS.
3. **Cổng SOS (rule-based, không LLM)** trên nội dung tin (từ khóa / policy sản phẩm). **Nếu SOS:** gọi **SOS Handler** như finalizer — payload **`BACKEND_PLAN.md` §7.2**, **không** chạy Supervisor → Analyst → Friend trong cùng request (**Diagram 4**). **Nếu không SOS:** **LangGraph** — **Supervisor** định tuyến → **Analyst** (ngầm) → **Friend** sinh phản hồi; thang `distress_score` / gợi voice (§7.9 bậc C) vẫn nằm trên luồng này, tách khỏi SOS keyword.
4. **Trả HTTP 200** ngay sau khi có nội dung trả lời (REST hoặc stream tuỳ triển khai).
5. **Ghi đồng bộ (sync)**: insert/update `messages`, `conversations` trong transaction Postgres (RLS); nếu SOS thêm `crisis_logs`, `admin_audit_log`, cập nhật **`clinical_profiles`** (xem Diagram 4).
6. **Sau response (async)** — chủ yếu nhánh **không-SOS**: Celery — cập nhật `clinical_profiles`, patch `user_profiles`, invalidate Redis, extract memory → embed → `conversation_memories`, enqueue **`sync_outbox`** cho Neo4j worker.

![Diagram 2 — Chat message → LangGraph → sync + async](./images/Chat_message.png)

---

## Diagram 3 — Session end summarizer → atomic profile update → outbox sync Neo4j

Khi hết phiên hoặc batch trigger: Session Summarizer đọc messages, tóm tắt (hoặc bỏ qua nếu đã tóm tắt / SOS / một tin), tạo embedding; trong một transaction Postgres ghi `conversation_memories`, cập nhật profile summaries, snapshot, `sync_outbox`; xóa cache Redis profile. Worker outbox định kỳ đọc outbox và đồng bộ lên Neo4j (User, Session, Trigger, Emotion, MemoryNode theo hợp đồng bootstrap).

**Mô tả luồng (theo hình):**

1. **Trigger**: phiên **idle** (ví dụ 30 phút), user **đóng phiên**, hoặc **job batch** ban đêm.
2. **Guard**: kiểm tra idempotency (đã tóm tắt chưa), bỏ qua nếu phiên chỉ có SOS đơn lẻ hoặc không đủ nội dung (theo policy).
3. **Summarizer** đọc `messages` trong session, gọi LLM tóm tắt (≤500 ký tự), **PII mask**; tạo **embedding** cho bản tóm tắt.
4. **Một transaction Postgres**: insert `conversation_memories`; append `user_profiles.profile.session_summaries` (FIFO 50); overflow → `session_summaries_archive`; ghi `user_profile_snapshots`; insert **`sync_outbox`** (event session ended / memory); **xóa** cache Redis `profile:{user_id}`.
5. **Outbox worker** (vài giây một lần): đọc `sync_outbox`, `MERGE` **Neo4j** (User, Session, MemoryNode, cạnh runtime…) — **không** dual-write trực tiếp từ request chat.

![Diagram 3 — Session end summarizer → Postgres → Neo4j outbox](./images/Session_end_summarizer.png)

---

## Diagram 4 — Crisis detected trong chat → de-escalation response + admin review

Tin nhắn có dấu hiệu tự hại (lexicon / rule sản phẩm): **`POST /v1/chat/message`** đánh giá SOS **trước khi** gọi LangGraph và kích hoạt **SOS Handler (rule-based, State Finalizer)** — **không** chạy Supervisor → Analyst → Friend trong cùng turn (`BACKEND_PLAN.md` §6.3). Response trả về client theo contract **`BACKEND_PLAN.md` §7.2**: `conversation_mode: de_escalation`, `risk_level`, `assistant_text`, **`assistant_strategy`**, **`micro_actions`**, **`hotline_cards`**, **`grounding_actions`**, **`referral_options`**, `followup_priority` — hỗ trợ **dual-focus UI** (`BACKEND_PLAN.md` §7.4–§7.6).

Đồng bộ: ghi messages, `crisis_logs`, `admin_audit_log`; cập nhật mức khủng hoảng trên **`clinical_profiles`** (ví dụ `crisis_level`); **cờ aggregate trên `user_profiles`** có thể bổ sung theo phase sản phẩm. `crisis_logs` **không** đi qua `sync_outbox` / Neo4j.

**Mô tả luồng (theo hình):**

1. User gửi tin nhắn có dấu hiệu **tự hại / khủng hoảng** (rule keyword / policy — khác với chỉ `distress_score` cao trong luồng LangGraph; thang §7.9 bậc D xem `BACKEND_PLAN.md` §7.9).
2. **SOS Handler** (không phụ thuộc LLM cho quyết định cuối) được gọi từ **chat gateway** như **State Finalizer** — **không** cho Friend “chat thường” trả lời thay thế trong cùng turn.
3. Backend ghép **payload §7.2**: `assistant_text`, `assistant_strategy`, `micro_actions`, `hotline_cards`, v.v. — FE hiển thị **vừa** an ủi / giữ kết nối **vừa** hành động an toàn + hotline.
4. **Sync Postgres**: lưu tin user + tin assistant (SOS), `crisis_logs`, `admin_audit_log`, cập nhật **`clinical_profiles`** (khủng hoảng / thời điểm chấm).
5. **Async (tuỳ cấu hình):** email/webhook cảnh báo vận hành — **không** bắt buộc trong MVP; bản ghi `admin_audit_log` thường ghi **cùng transaction** sync với tin nhắn SOS.
6. **Admin** xem queue `crisis_logs`, đánh dấu `reviewed` trên dashboard nội bộ.

![Diagram 4 — Crisis trong chat → de-escalation + admin](./images/Crisis_detected_trong_chat.png)

---

## Diagram 5 — Signup → policy acknowledgment bắt buộc → mở quyền core APIs

Đăng ký tạo user và token; client lấy policy hiện tại; user xác nhận policy; server ghi `policy_ack_events` và `policy_acknowledged_at`. Các API nhạy cảm (ví dụ chat) kiểm tra acknowledgment — chưa xác nhận thì 403, đã xác nhận thì cho phép luồng chat / check-in / screening.

**Mô tả luồng (theo hình):**

1. **`POST /v1/auth/signup`** (hoặc convert guest → user) — tạo `users`, set cookie JWT/refresh theo `API_SPEC.md`.
2. Client gọi **`GET /v1/policies/current`** — nhận nội dung policy + phiên bản.
3. User đọc và gọi **`POST /v1/policies/acknowledge`** — server ghi `policy_acknowledged_at` (và bảng/event audit nếu có).
4. Middleware **core API** (chat, v.v.): nếu **chưa ack** → **403**; nếu **đã ack** → cho phép truy cập Diagram 2 và các luồng sản phẩm khác.

![Diagram 5 — Signup → policy ack → core APIs](./images/Signup.png)

---

### Diagram 6 — Happy path: chat bình thường (Supervisor → Analyst → Friend, không SOS)

**Mô tả luồng (theo hình):**

1. User nhắn trong ngữ cảnh **không** vượt ngưỡng SOS.
2. **Supervisor** phân loại intent (chào hỏi, tâm sự nhẹ, cần gợi ý, …).
3. **Analyst** (ngầm) cập nhật/ước lượng tín hiệu lâm sàng, distortions, gói **instruction** cho Friend — user không thấy trực tiếp.
4. **Friend** (Mây) trả lời thấu cảm, có thể kèm `the_dinh_kem` / quick replies — **không** kích hoạt `sos_triggered`.
5. Ghi DB và pipeline async như Diagram 2 (không nhánh crisis Diagram 4).

![M1 — Happy path chat](./images/happycase.png)

---

### Diagram 7 — Thang an toàn trong chat (tiêu cực / khuyên nhủ / SOS / gọi thoại có điều kiện)

**Mô tả luồng (theo hình):**

1. Hệ thống phân **tầng mức độ** phản ứng theo mức rủi ro / nội dung: từ **tiêu cực nhẹ** (đồng cảm, gợi mở), lên **khuyên can / can thiệp nhẹ**, tới **cảnh báo SOS** và **gợi ý gọi hỗ trợ có điều kiện** (theo policy sản phẩm và pháp lý).
2. Mỗi bậc có **copy + UI** tương ứng (ví dụ thang “thang an toàn” trong chat — không chỉ một nút duy nhất).
3. Khi leo tới ngưỡng cao nhất, khớp **Diagram 4** (payload §7.2, không chỉ một dòng hotline).

![M2 — Thang an toàn trong chat](./images/diagram-m2-safety-ladder.png)

---

### Diagram 8 — Cập nhật dashboard: tổng hợp ngày / tuần / tháng (on-demand + batch tùy chọn)

**Mô tả luồng (theo hình):**

1. **Gương** (dashboard) gọi API tổng hợp: xu hướng mood, lịch sử phiên, nhắc nhở — ví dụ `GET /v1/dashboard/overview`, `mood-trend`, `history`, `follow-up` (`BACKEND_PLAN.md` §5.7).
2. Dữ liệu đọc chủ yếu từ **Postgres** (`mood_checkins`, `conversations`, aggregates trong `user_profiles`); có thể kèm job **batch** (tuần/tháng) để làm nhẹ P95.
3. **Không** đặt PII nhạy cảm vào response công khai; điểm PHQ/GAD thô chỉ nội bộ/B2B.

![M3 — Dashboard Gương theo chu kỳ](./images/diagram-m3-dashboard.png)

---

### Diagram 9 — Bad case: người dùng nói về tự hại (SOS, đồng bộ đầy đủ)

**Mô tả luồng (theo hình):**

1. User diễn đạt **ý định tự hại** hoặc nội dung **khủng hoảng** khớp rule SOS (keyword / policy). Đây là **nhánh SOS**; **bậc D** (`distress_score` > 0.9, outbound tin cậy, v.v.) là **mở rộng** theo `BACKEND_PLAN.md` §7.9 + §15, có thể tách job/worker.
2. **Chat gateway** (`POST /v1/chat/message`) chuyển sang **SOS / de-escalation** **trước LangGraph** (giống Diagram 4): SOS Handler rule-based, payload **§7.2**.
3. **Đồng bộ** phía server trong một commit: tin nhắn, `crisis_logs`, `admin_audit_log`, **`clinical_profiles`**; cảnh báo admin bổ sung (email/webhook) là **async tuỳ cấu hình**.
4. FE hiển thị **dual-focus**: vẫn giữ kết nối an toàn + hotline + micro-actions — khớp `BACKEND_PLAN.md` §7.5–§7.6 (không chỉ một màn hình số điện thoại).

![M4 — Bad case tự hại và SOS](./images/badcase.png)

---

## Ghi chú contract API (crisis)

- **`API_SPEC.md`** — `POST /v1/chat/message`: khi `sos_triggered: true`, `data` chứa các field khớp **`BACKEND_PLAN.md` §7.2**; hotline/referral đọc thêm từ **`GET /v1/safety/hotlines`**, **`GET /v1/safety/referrals/options`**.
- **`BACKEND_PLAN.md` §7** — contract JSON (§7.2), nguyên tắc tâm lý / pattern copy / dual-focus / pitfall (§7.4–§7.8); thang **`distress_score`** và bậc hành vi (≥0.8 gợi thoại, >0.9 khẩn + tin cậy) — **§7.9** (bậc C/D không thay thế SOS keyword trừ khi product map rõ).

---
