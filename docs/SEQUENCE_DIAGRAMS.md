# Sequence Diagrams

---

## Diagram 1 — Guest-first vào app → chọn nhu cầu → Safety Gate

Luồng khách mở app không đăng ký, chọn nhu cầu (Check-in / Screening / Chat), gọi API guest session, sau đó qua Safety Gate (`POST /v1/intake/safety-check`): service đánh giá rủi ro; nếu cần hướng crisis thì ghi pre-flag Postgres và trả route + hotline, ngược lại vào flow đã chọn.

![Diagram 1 — Guest-first vào app → chọn nhu cầu → Safety Gate](./images/diagram-01-guest-first.png)

---

## Diagram 2 — Chat message (Mây) → LangGraph → sync writes + async pipeline

Luồng gửi tin nhắn chat: frontend → FastAPI; middleware tải working memory (Redis cache / Postgres); LangGraph (Supervisor / Analyst / Friend) xử lý, nhánh crisis nếu cần; trả response; ghi đồng bộ messages và conversation trên Postgres; Celery xử lý bất đồng bộ cập nhật profile, memory embedding và `sync_outbox`.

![Diagram 2 — Chat message → LangGraph → sync + async](./images/Chat_message.png)

---

## Diagram 3 — Session end summarizer → atomic profile update → outbox sync Neo4j

Khi hết phiên hoặc batch trigger: Session Summarizer đọc messages, tóm tắt (hoặc bỏ qua nếu đã tóm tắt / SOS / một tin), tạo embedding; trong một transaction Postgres ghi `conversation_memories`, cập nhật profile summaries, snapshot, `sync_outbox`; xóa cache Redis profile. Worker outbox định kỳ đọc outbox và đồng bộ lên Neo4j (User, Session, Trigger, Emotion, MemoryNode theo hợp đồng bootstrap).

![Diagram 3 — Session end summarizer → Postgres → Neo4j outbox](./images/Session_end_summarizer.png)

---

## Diagram 4 — Crisis detected trong chat → de-escalation response + admin review

Tin nhắn có dấu hiệu tự hại: LangGraph gọi SOS handler; nếu vượt ngưỡng crisis thì bỏ qua path Analyst/Friend thường, trả payload de-escalation + hotline; ghi messages, `crisis_logs`, audit; cập nhật cờ an toàn trên profile; frontend hiển thị phản hồi crisis; thông báo admin; dashboard đọc và đánh dấu reviewed. `crisis_logs` không đi qua `sync_outbox` / Neo4j.

![Diagram 4 — Crisis trong chat → de-escalation + admin](./images/Crisis_detected_trong_chat.png)

---

## Diagram 5 — Signup → policy acknowledgment bắt buộc → mở quyền core APIs

Đăng ký tạo user và token; client lấy policy hiện tại; user xác nhận policy; server ghi `policy_ack_events` và `policy_acknowledged_at`. Các API nhạy cảm (ví dụ chat) kiểm tra acknowledgment — chưa xác nhận thì 403, đã xác nhận thì cho phép luồng chat / check-in / screening.

![Diagram 5 — Signup → policy ack → core APIs](./images/Signup.png)

---

### Diagram 6 — Happy path: chat bình thường (Supervisor → Analyst → Friend, không SOS)

![M1 — Happy path chat](./images/happycase.png)

### Diagram 7 — Thang an toàn trong chat (tiêu cực / khuyên nhủ / SOS / gọi thoại có điều kiện)

![M2 — Thang an toàn trong chat](./images/diagram-m2-safety-ladder.png)

### Diagram 8 — Cập nhật dashboard: tổng hợp ngày / tuần / tháng (on-demand + batch tùy chọn)

![M3 — Dashboard Gương theo chu kỳ](./images/diagram-m3-dashboard.png)

### Diagram 9 — Bad case: người dùng nói về tự hại (SOS, đồng bộ đầy đủ)

![M4 — Bad case tự hại và SOS](./images/badcase.png)

---