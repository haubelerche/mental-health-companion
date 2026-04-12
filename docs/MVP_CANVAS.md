## Thông tin dự án
- **Tên cụ thể**: Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
- **Stack**: React.js + FastAPI + LangGraph + PostgreSQL + pgvector
- **Ngày**: 2026-04-12
- **Phiên bản**: 1.0
---
### 1. Target User

- **Chính (B2C):** Sinh viên đại học (Gen Z) đang đối mặt với áp lực học tập, thi cử, lo âu xã hội, hoặc có dấu hiệu burnout/trầm cảm nhẹ đến trung bình.

### 2. Job-to-be-done

- "Khi tôi cảm thấy kiệt sức và bế tắc vì áp lực học hành/mối quan hệ vào lúc nửa đêm, tôi muốn có một người bạn đồng trang lứa để tâm sự an toàn, không phán xét, giúp tôi gỡ rối cảm xúc và tìm ra các giải pháp thực tế ngay tại trường đại học của mình."

### 3. Pain Point

- **Sợ bị dán nhãn (Stigma):** Ngại đến phòng tham vấn trực tiếp vì sợ bạn bè, thầy cô nhìn thấy và đánh giá
- **Sự khô khan lâm sàng:** Các app tâm lý hiện tại giống như "hỏi cung" hoặc "khám bệnh", gây cảm giác nặng nề.
- **Thiếu sự thấu cảm và thực tế:** Các chatbot thông thường đưa ra lời khuyên sáo rỗng (Toxic Positivity) hoặc không hiểu bối cảnh trường lớp.
- **Tính lặp lại:** Phải kể đi kể lại một vấn đề từ đầu nếu đổi người tư vấn.

### 4. Current Workaround

- Viết ẩn danh trên các trang "Confession" của trường (không có chuyên môn, dễ nhận phản ứng toxic).
- Sử dụng chatbot AI thông thường (ChatGPT/Claude bản miễn phí) – thiếu rào cản an toàn lâm sàng và kiến thức học đường đặc thù.
- Chịu đựng một mình hoặc tìm đến các nội dung Self-help chung chung.

### 5. Problem Statement

- Làm thế nào để cung cấp một giải pháp hỗ trợ tâm lý mang cảm giác **tự nhiên, phản hồi tức thì như trò chuyện với người bạn thân**, có khả năng **gợi ý giải pháp học vụ thực tế**, đồng thời ngầm **sàng lọc chuẩn lâm sàng**, đảm bảo **an toàn 24/7** và chuyển tuyến kịp thời cho các ca nguy cơ cao?

### 6. Core Outcome

- **Về phía người dùng:** Chuyển đổi từ trạng thái "Hỗn loạn cảm xúc" sang "Nhận thức có cấu trúc", cảm thấy được lắng nghe và nhận được giải pháp/thông tin hỗ trợ thiết thực từ chính trường đại học của mình.
- **Về phía B2B (Nhà trường):** Sở hữu một "Radar đo lường sức khỏe tinh thần" theo thời gian thực. Thu thập được bộ Hồ sơ tâm lý vĩ mô (Macro-trend Dashboard) cực kỳ chính xác mà không vi phạm quyền riêng tư của sinh viên.

### 7. MVP Features (Hybrid Hierarchical Multi-Agent Architecture)

Kiến trúc được chia thành luồng Đồng bộ (Sync - ưu tiên tốc độ) và Bất đồng bộ (Async - ưu tiên chuyên môn):

- **Agent 1: Peer Listener (Luồng Sync - Giao tiếp frontend):**
    - Đóng vai trò là "người bạn đồng hành". Xử lý giao tiếp thời gian thực với độ trễ cực thấp (<3 giây).
    - Áp dụng kỹ thuật lắng nghe, xác nhận cảm xúc (Validation) và sử dụng ngôn ngữ Gen Z. Không chẩn đoán, không dùng thuật ngữ y khoa.
- **Agent 2: Anonymization & Crisis Guardrail (Luồng Async - Xử lý ngầm):**
    - **Bảo mật:** Tự động che giấu thông tin định danh (PII Masking như tên, MSSV, SĐT) thành các thẻ `[PERSON]`, `[ID]` ngay khi nhận tin nhắn để bảo vệ quyền riêng tư.
    - **An toàn (Safety Net):** Liên tục quét ngữ cảnh để nhận diện *ý định* tự hại (sự vô vọng, cảm giác là gánh nặng) thay vì chỉ bắt từ khóa. Nếu phát hiện rủi ro cao, lập tức ngắt luồng (Escalation) để cung cấp hotline hoặc báo động cho chuyên viên tâm lý của trường (Human-in-the-loop).
- **Agent 3: Clinical Screener & CBT Evaluator (Luồng Async - Chuyên gia ngầm):**
    - **Đánh giá ngầm:** Phân tích lịch sử chat để tự động tính điểm PHQ-9/GAD-7 lưu vào hồ sơ (Namespace `/clinical/`) mà không cần hỏi cung người dùng.
    - **Tối ưu hóa (Evaluator-Optimizer):** Chỉ kích hoạt khi phát hiện suy nghĩ lệch lạc phức tạp. Agent này sẽ truy xuất dữ liệu từ **University Context RAG** (lịch thi, phòng ban hỗ trợ) và **CBT Coping Skills** (kỹ năng đối phó), từ đó *điều chỉnh bản nháp* câu trả lời của Agent 1 trước khi gửi cho sinh viên.
- **Agent 4: B2B Analyst (Hậu kiểm & Báo cáo):**
    - Trích xuất các dữ liệu đã được ẩn danh hoàn toàn để phân tích xu hướng (Ví dụ: "Tỷ lệ burnout tăng vọt ở sinh viên năm 3 ngành IT vào tuần trước thi"). Tạo Dashboard tự động cho nhà trường.

### 8. Validation Metric

Thay vì dùng các chỉ số đánh giá phần mềm truyền thống, hệ thống sử dụng các chỉ số đo lường AI Agentic:

- **Safety Recall Rate (Tỷ lệ không bỏ sót rủi ro):** Đạt 100% trong việc nhận diện ý định tự hại/khủng hoảng. Đối với an toàn sinh mạng, *Recall (không bỏ sót)* quan trọng hơn *Precision (báo nhầm)*. Mọi ca nguy cơ đều phải được kích hoạt kịch bản khẩn cấp dưới 2 giây.
- **Latency & UX (Tốc độ & Trải nghiệm):** Agent 1 phải phản hồi trong khoảng 1-3 giây đối với các câu chat thông thường để duy trì ảo giác "chat với người thật".
- **User Engagement (Tỷ lệ giữ chân):** Số lượng phiên chat (sessions) vượt qua 10 lượt trao đổi (turn) thay vì người dùng thoát app ngay sau 1-2 tin nhắn.
- **Implicit Clinical Accuracy (Độ chuẩn xác ngầm):** Tỷ lệ khớp (Kappa score) > 85% giữa điểm số PHQ-9/GAD-7 do Agent 3 tự động gán nhãn so với kết quả đánh giá ngẫu nhiên của chuyên gia tâm lý trên cùng tập dữ liệu ẩn danh.
- **B2B Value:** Số lượng Actionable Insights (thông tin có thể hành động) mà nhà trường áp dụng được từ Dashboard (ví dụ: quyết định mở workshop giảm stress khi biểu đồ lo âu tăng).

---

###