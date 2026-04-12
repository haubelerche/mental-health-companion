# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

> Cập nhật **bất cứ khi nào** nhóm ra quyết định kỹ thuật quan trọng hoặc thay đổi hướng đi.

---

## Template

### Quyết định kỹ thuật

```markdown
### [ADR-N] Tiêu đề quyết định — DD/MM/YYYY

**Bối cảnh:** Vấn đề cần giải quyết là gì?

**Các lựa chọn đã xem xét:**
- Option A: ...
- Option B: ...

**Quyết định:** Chọn option nào và tại sao.

**Hệ quả:** Những gì bị ảnh hưởng / trade-off.
```

### Phân công

```markdown
### Sprint N — DD/MM → DD/MM/YYYY

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| | | | |
```

### Brainstorming

```markdown
### Brainstorm: [Chủ đề] — DD/MM/YYYY

**Câu hỏi:** ...

**Các ý tưởng:**
- Ý tưởng 1: ...
- Ý tưởng 2: ...

**Kết luận:** ...
```

---

## Quyết định kỹ thuật

### [ADR-1] Chọn Python 3.11 + FastAPI thay vì Node.js — 07/04/2026

**Bối cảnh:** Tuần 1 nhóm prototype bằng JavaScript (Anthropic SDK) để thử nghiệm agent loop. Bước sang tuần 2 cần chọn ngôn ngữ chính cho toàn bộ backend. Hệ thống phụ thuộc vào LangGraph, NeMo Guardrails, pgvector — phần lớn chỉ có bản Python ổn định.

**Các lựa chọn đã xem xét:**
- **Node.js + TypeScript**: Team đã có prototype tuần 1, type safety tốt. Nhưng LangGraph, NeMo Guardrails không hỗ trợ JS.
- **Python 3.11 + FastAPI**: Ecosystem AI/ML mạnh nhất, LangGraph native Python, async support tốt, Pydantic cho schema validation.

**Quyết định:** Chọn Python 3.11 + FastAPI. LangGraph là cốt lõi của orchestration — không có lựa chọn thay thế tương đương ở JS. Frontend giữ React.js (JavaScript/TypeScript).

**Hệ quả:** Prototype JavaScript tuần 1 không tái sử dụng cho backend. Schema validation chuyển từ Zod → Pydantic. Cần setup môi trường Python riêng (venv/conda).

---

### [ADR-2] Dùng LangGraph 0.2+ thay vì tự xây orchestration — 08/04/2026

**Bối cảnh:** Sau khi nghiên cứu agents research (Hậu), nhóm cần framework điều phối 3 agent (Supervisor → Analyst → Friend) với state phức tạp, routing có điều kiện và memory tích lũy qua nhiều phiên.

**Các lựa chọn đã xem xét:**
- **Tự xây orchestration**: Kiểm soát hoàn toàn nhưng tốn thời gian, dễ bug ở edge case vòng lặp agent.
- **LangChain LCEL**: Có chain/router nhưng không có built-in state graph và persistent checkpointing.
- **LangGraph 0.2+**: State graph rõ ràng, conditional edge map trực tiếp sang routing logic, checkpointing built-in cho persistent session.

**Quyết định:** Chọn LangGraph. Checkpointing là yêu cầu bắt buộc — mental health app phải giữ context hội thoại qua nhiều lượt. `TrangThaiSerene` dùng Pydantic model làm LangGraph state.

**Hệ quả:** Cần học LangGraph API (StateGraph, node, edge, checkpointer). State schema phải tuân thủ định nghĩa chặt chẽ để LangGraph quản lý đúng.

---

### [ADR-3] Analyst không giao tiếp trực tiếp với người dùng — 09/04/2026

**Bối cảnh:** Kết quả từ "MINDSET CỦA 1 THERAPIST" research (Dũng + Đạt) chỉ ra rằng ngôn ngữ lâm sàng gây stigma ngay cả khi thông tin chính xác. Analyst cần đưa ra đánh giá PHQ-9/GAD-7 nhưng không được để user cảm thấy "bị khám bệnh".

**Các lựa chọn đã xem xét:**
- **Analyst → User trực tiếp**: Đơn giản hơn pipeline nhưng output lâm sàng phá vỡ trải nghiệm peer chat.
- **Analyst → Friend → User**: Analyst trả `KetQuaLamSang` cho Supervisor, Friend "dịch" sang ngôn ngữ Gen Z đồng cảm trước khi gửi user.

**Quyết định:** Bắt buộc Analyst → Friend → User. Đây là nguyên tắc bất biến — user chỉ thấy một nhân vật Serene duy nhất. Recursion guard max 3 lần để tránh vòng lặp Analyst ↔ Friend.

**Hệ quả:** Thêm 1 hop latency (Analyst xong → Friend mới chạy). Đổi lại: tone hội thoại nhất quán 100%, không rủi ro output lâm sàng thô đến tay user.

---

### [ADR-4] Tách luồng Sync/Async — Clinical scoring chạy bất đồng bộ — 09/04/2026

**Bối cảnh:** Target latency P50 ≤ 2s cho Friend response, P95 ≤ 5s toàn pipeline. PHQ-9 scoring và PII masking là tác vụ nặng nhưng không cần kết quả ngay để trả lời user.

**Các lựa chọn đã xem xét:**
- **Toàn bộ Sync**: Đơn giản nhất, nhưng clinical scoring thêm ~1-2s, khó đạt target latency.
- **Tách Sync/Async**: Friend response chạy sync (ưu tiên UX), Analyst scoring + PII masking + memory write chạy async sau.

**Quyết định:** Sync — Supervisor routing, Safety check, Friend response. Async — Clinical scoring, context compression, PII masking, long-term storage. **Ngoại lệ bắt buộc:** Crisis detection (`muc_do_khung_hoang`) luôn chạy Sync — không delay an toàn sinh mạng.

**Hệ quả:** Cần thiết kế async job queue và retry logic. State có thể tạm thời không đồng bộ giữa chat response và clinical profile — chấp nhận được.

---

### [ADR-5] Dùng pgvector + PostgreSQL thay vì vector database riêng — 10/04/2026

**Bối cảnh:** Hệ thống cần lưu vector embeddings cho RAG (University Context: lịch thi, phòng ban hỗ trợ) và tóm tắt hội thoại. Database schema đã được chốt (PostgreSQL) trong task Database tuần 2.

**Các lựa chọn đã xem xét:**
- **Pinecone / Weaviate / Qdrant**: Managed/self-hosted, mạnh nhưng thêm service mới cần deploy và monitor.
- **pgvector extension**: Tích hợp trực tiếp vào PostgreSQL đang dùng, không cần service bổ sung, query kết hợp vector + relational trong 1 DB.

**Quyết định:** Dùng pgvector. Ở quy mô MVP, pgvector đủ hiệu năng. Giảm complexity deploy trên Railway (1 DB thay vì 2 service). Embeddings dùng `text-embedding-3-small` của OpenAI.

**Hệ quả:** Nếu scale lớn hậu MVP cần migrate sang vector DB chuyên dụng. Trade-off chấp nhận được cho giai đoạn này.

---

### [ADR-6] SOS Layer là rule-based, không dùng LLM — 10/04/2026

**Bối cảnh:** Khi `muc_do_khung_hoang ≥ 4`, hệ thống phải can thiệp khẩn cấp dưới 2 giây. An toàn sinh mạng không được phụ thuộc vào LLM có thể hallucinate hoặc có latency cao.

**Các lựa chọn đã xem xét:**
- **LLM-based**: Hiểu ngữ cảnh tốt hơn nhưng không deterministic, latency không đảm bảo.
- **Rule-based (keyword + score threshold)**: Deterministic, latency gần 0, không bao giờ "quên" check.
- **Hybrid**: Rule-based lớp đầu (fast), LLM lớp thứ hai khi rule không chắc.

**Quyết định:** Rule-based cho SOS Layer kết hợp NeMo Guardrails ở input. Safety Recall ≥ 99% là metric bất biến — Recall quan trọng hơn Precision khi đây là vấn đề sinh mạng. SOS chỉ hiển thị hotline/referral (1800-599-920), không kết nối live counselor.

**Hệ quả:** Sẽ có false positive — chấp nhận được. LLM không được tham gia vào quyết định SOS.

---

## Phân công

### Sprint 1 — 31/03 → 06/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Nghiên cứu Anthropic Tool Use API | Lương Thanh Hậu | 02/04 | ✅ Xong |
| Xây dựng agent loop cơ bản (JS prototype) | Lương Thanh Hậu | 03/04 | ✅ Xong |
| Debug message history format (`tool_result`) | Lê Hoàng Đạt | 04/04 | ✅ Xong |
| Thêm timeout + error handling cho API calls | Lương Thanh Hậu | 05/04 | ✅ Xong |
| Research tổng quan thị trường mental health app | Lương Tiến Dũng | 05/04 | ✅ Xong |
| Đánh giá và đề xuất techstack cho Sprint 2 | Cả nhóm | 06/04 | ✅ Xong |

---

### Sprint 2 — 07/04 → 13/04/2026

**Research & Foundation**

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| DATABASE — Thiết kế schema PostgreSQL + pgvector | Cả nhóm | 09/04 | ✅ Xong |
| COMPETITOR ANALYSIS — Tìm kiếm và phân tích các App MHSD | Lương Tiến Dũng | 09/04 | ✅ Xong |
| TÓM LẠI VẤN ĐỀ — Tổng hợp pain points và problem statement | Lương Thanh Hậu | 09/04 | ✅ Xong |
| SAI SÓT HIỆN TẠI — Rà soát lỗ hổng trong approach ban đầu | Lương Thanh Hậu | 09/04 | ✅ Xong |
| PROOF OF CONCEPT — Validate feasibility kỹ thuật | Lê Hoàng Đạt | 09/04 | ✅ Xong |
| AGENTS RESEARCH — Nghiên cứu multi-agent patterns, LangGraph | Lương Thanh Hậu | 09/04 | ✅ Xong |
| MINDSET CỦA 1 THERAPIST — Research nguyên tắc tư vấn tâm lý | Lương Tiến Dũng + Lê Hoàng Đạt | 09/04 | ✅ Xong |

**Documentation (Đã chốt)**

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| ARCHITECTURE.md — Kiến trúc multi-agent, state schema, sơ đồ | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| PRD.md — User stories, acceptance criteria, KPIs | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| MVP_CANVAS.md — Target user, pain points, validation metrics | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| PROBLEM_BRIEF.md — Bối cảnh, chân dung user, phân tích đối thủ | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| DATA_DESCRIPTION.md — Mô tả dữ liệu, DB schema chi tiết | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| BRIEF FRONTEND — Tóm tắt yêu cầu UI/UX cho frontend | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |
| FRONTEND PROTOTYPE | Lương Thanh Hậu | 09/04 | ✅ Đã chốt |

**Đang tiến hành**

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| CONTEXT ENGINEERING — Nghiên cứu kỹ thuật quản lý context LLM | Lương Thanh Hậu | 13/04 | 🔄 Đang research |
| XÂY DATABASE | Lê Hoàng Đạt | 13/04 | 🔄 Đang research |
| XÂY FRONTEND | Lương Tiến Dũng | 13/04 | 🔄 Đang research |

---

## Brainstorming

### Brainstorm: Mindset của 1 therapist → áp dụng vào AI agent — 08/04/2026

**Câu hỏi:** Một therapist thực sự làm gì trong buổi trị liệu đầu tiên? Agent cần "học" điều gì từ đó?

**Các ý tưởng:**
- **Ý tưởng 1 (Lương Tiến Dũng):** Therapist không chẩn đoán ngay — họ tạo không gian an toàn trước. Agent Friend cần validation trước, gợi ý sau. Không bao giờ nói "bạn bị trầm cảm" trong lượt đầu.
- **Ý tưởng 2 (Lê Hoàng Đạt):** Therapist dùng câu hỏi mở (open-ended) thay vì câu hỏi có/không. Friend nên hỏi "Kể thêm cho mình nghe..." thay vì "Bạn có cảm thấy buồn không?".
- **Ý tưởng 3 (Lương Tiến Dũng):** Therapist nhớ detail từ buổi trước — "Lần trước bạn kể về deadline, bây giờ thế nào rồi?". Cần memory có structured summary, không chỉ raw text.

**Kết luận:** Friend agent cần prompt system nhấn mạnh 3 nguyên tắc: (1) Validation trước, gợi ý sau. (2) Open-ended questions. (3) Reference memory cụ thể từ lượt trước. Analyst là "chuyên gia ngầm" — không được xuất hiện trong conversation.

---

### Brainstorm: Proof of Concept — Validate feasibility hệ thống — 08/04/2026

**Câu hỏi:** Trước khi code full system, cần validate những gì để chắc architecture khả thi?

**Các ý tưởng:**
- **Ý tưởng 1 (Lê Hoàng Đạt):** Test LangGraph với state schema `TrangThaiSerene` — xem routing Supervisor → Analyst → Friend có hoạt động đúng không với mock node.
- **Ý tưởng 2 (Lê Hoàng Đạt):** Test implicit PHQ-9 scoring bằng vài đoạn hội thoại mẫu — so sánh kết quả GPT-4o-mini + fewshot với kết quả chuyên gia chấm thủ công.
- **Ý tưởng 3 (Lương Thanh Hậu):** Test NeMo Guardrails với tập crisis keyword — đo false positive rate, đảm bảo SOS trigger đúng.

**Kết luận:** POC tập trung vào 2 điểm rủi ro cao nhất: (1) LangGraph routing với real state, (2) Implicit PHQ-9 accuracy. NeMo test sau khi có tập keyword chuẩn hơn. Lê Hoàng Đạt dẫn POC.

---

### Brainstorm: Competitor Analysis — Khoảng trống thị trường — 09/04/2026

**Câu hỏi:** Các app mental health hiện tại (Vmood, SnS, Wysa, Woebot) đang thiếu gì? Đây là cơ hội của nhóm ở đâu?

**Các ý tưởng:**
- **Ý tưởng 1 (Lương Tiến Dũng):** Không có app nào nhắm riêng sinh viên VN. Vmood và SnS xây cho "cộng đồng chung" — không có module thi cử, burnout học đường.
- **Ý tưởng 2 (Lương Tiến Dũng):** Wysa có AI tốt nhưng tiếng Anh. Vmood có tiếng Việt nhưng không có AI. Không ai có cả hai — first mover advantage nếu làm được.
- **Ý tưởng 3 (Lương Tiến Dũng):** Tất cả đối thủ quá nặng về "chẩn đoán", thiếu trải nghiệm "tâm sự với bạn bè". Sinh viên VN ngại gặp chuyên gia nhưng sẵn sàng chia sẻ với người đồng trang lứa.

**Kết luận:** 3 lợi thế cạnh tranh rõ ràng: (1) AI chatbot tiếng Việt. (2) Định hướng sinh viên đại học. (3) Peer-to-peer experience thay vì clinical interface. Chiến lược phân phối: B2B2C qua trường đại học.

---

### Brainstorm: Context Engineering cho LLM agents — 12/04/2026

**Câu hỏi:** Làm sao quản lý context window hiệu quả khi conversation dài, có cả memory, clinical profile và system prompt?

**Các ý tưởng:**
- **Ý tưởng 1 (Lương Thanh Hậu):** Sliding window — chỉ giữ 8 lượt hội thoại gần nhất trong working memory. Các lượt cũ hơn được compress thành event summary.
- **Ý tưởng 2 (Lương Thanh Hậu):** Phân cấp context — System prompt cố định + Clinical profile tóm tắt (không raw) + 8 turns gần nhất. Tránh nhồi toàn bộ lịch sử vào prompt.
- **Ý tưởng 3 (Lương Thanh Hậu):** Event-based memory — thay vì lưu từng tin nhắn, lưu "sự kiện" (VD: "User chia sẻ về deadline 15/04, cảm thấy overwhelmed"). Tiết kiệm token hơn nhiều.

**Kết luận:** Kết hợp sliding window (8 turns) + event-based long-term memory. Clinical profile chỉ lưu điểm số và coverage, không raw conversation. Đang research thêm về compression techniques — chưa chốt implementation.
