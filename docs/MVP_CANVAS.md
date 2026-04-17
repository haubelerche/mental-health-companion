### 1. Target User

- Sinh viên đại học hoặc người mới đi làm (Gen Z) đang đối mặt với áp lực học tập, thi cử, lo âu xã hội, không kiểm soát được cảm xúc hoặc có dấu hiệu burnout/trầm cảm nhẹ đến trung bình.

### 2. Job-to-be-done

- "Khi tôi cảm thấy kiệt sức và bế tắc vì áp lực học hành/mối quan hệ vào lúc nửa đêm, tôi muốn có một người bạn đồng trang lứa để tâm sự an toàn, không phán xét, giúp tôi gỡ rối cảm xúc và tìm ra các giải pháp thực tế ngay tại trường đại học của mình."

### 3. Pain Point

- **Sợ định kiến xã hội:** Ngại đến phòng tham vấn trực tiếp vì sợ bạn bè, thầy cô nhìn thấy và đánh giá
- **Sự khô khan lâm sàng:** Các app tâm lý hiện tại giống như "hỏi cung" hoặc "khám bệnh", gây cảm giác nặng nề.
- **Thiếu sự thấu cảm và thực tế:** Các chatbot thông thường đưa ra lời khuyên sáo rỗng (Toxic Positivity) hoặc không hiểu bối cảnh trường lớp.
- **Tính lặp lại:** Phải kể đi kể lại một vấn đề từ đầu nếu đổi người tư vấn.

### 4. Current Workaround

- Viết ẩn danh trên các trang mạng (không có chuyên môn, dễ nhận phản ứng toxic) hoặc chọn không nói ra, đè nén tiêu cực trong lòng, kể với gia đình, bạn bè nhưng nhận được phản hồi tiêu cực hoặc không hữu ích…
- Sử dụng chatbot AI thông thường (ChatGPT/Claude bản miễn phí) – thiếu rào cản an toàn lâm sàng và dễ bị hệ thống AI thao túng vì thiên hướng đồng ý với tất cả mọi thứ người dùng nói ra làm mất đi khả năng tư duy độc lập và nhận định thực tế.

### 5. Problem Statement

- Làm thế nào để cung cấp một giải pháp hỗ trợ tâm lý mang cảm giác **tự nhiên, phản hồi tức thì như trò chuyện với người bạn thân của riêng mình**, có khả năng **gợi ý giải pháp thực tế, nhớ các chi tiết về họ**, đồng thời ngầm **sàng lọc chuẩn lâm sàng**, đảm bảo **an toàn 24/7** và chuyển tuyến kịp thời cho các ca nguy cơ cao?

### 6. Core Outcome

- **Về phía người dùng:** Được lắng nghe, trút bỏ những tiêu cực trong lòng và học được cách chăm sóc sức khỏe tinh thần. Mọi nhu cầu từ tư vấn, trò chuyện, tập luyện, giải tỏa cảm xúc, an ủi… đều được thực hiện chỉ với một ứng dụng AI thông minh và bảo mật.

### 7. MVP Features

Kiến trúc được chia thành luồng **Đồng bộ (Sync – ưu tiên tốc độ)** và **Bất đồng bộ (Async – ưu tiên chuyên môn)**:

---

#### Agent 1 – Supervisor
- **Model:** GPT-4o-mini (temperature 0.1)
- **Vai trò:** Điểm phân luồng trung tâm — nhận state từ Middleware, phân tích intent người dùng, quyết định agent tiếp theo.
- **Tính năng:**
  - Phân loại intent: `greeting` / `tâm sự nhẹ` / `distress` / `crisis`
  - Đọc `muc_do_khung_hoang` từ state để quyết định có kích hoạt SOS không
  - Gọi Analyst khi phát hiện dấu hiệu distress; gọi Friend cho các nhánh bình thường
  - Giới hạn đệ quy tối đa 3 lần (recursion guard) để tránh vòng lặp vô hạn giữa các agent
  - Output: `QuyetDinhDinhTuyen` – bao gồm agent tiếp theo, lý do định tuyến, mức ưu tiên

---

#### Agent 2 – Friend
- **Model:** GPT-4o (temperature 0.7)
- **Vai trò:** Nhân vật duy nhất người dùng nhìn thấy— tạo phản hồi thấu cảm, tự nhiên theo phong cách Gen Z.
- **Tính năng:**
  - Phản hồi hội thoại đồng cảm, tránh toxic positivity và lời khuyên sáo rỗng
  - Lồng ghép câu hỏi khai thác lâm sàng từ Analyst một cách tự nhiên, không giống "hỏi cung"
  - Sinh 3 **quick replies** gợi ý phản hồi nhanh cho người dùng dựa trên `tone_cam_xuc`
  - Đính kèm **thẻ UI** (bài tập thở 4-7-8, grounding, nguồn tài nguyên) khi Analyst đề xuất
  - Viết lại "Lời nhắn tuần" từ tổng hợp của Analyst (weekly summary, temp 0.4)
  - Gợi ý prompt viết nhật ký (journal) từ Knowledge Base
  - Output: `PhanHoiHoiThoai` – nội dung trả lời, tone cảm xúc, quick replies, thẻ đính kèm

---

#### Agent 3 – Analyst
- **Model:** GPT-4o-mini + few-shot prompting (temperature 0.0)
- **Vai trò:** Chạy ngầm — người dùng không nhìn thấy trực tiếp. Thực hiện sàng lọc lâm sàng ẩn danh qua hội thoại.
- **Tính năng:**
  - Ánh xạ nội dung hội thoại vào thang đo **PHQ-9** (trầm cảm, 0–27) và **GAD-7** (lo âu, 0–21)
  - Theo dõi **độ bao phủ (coverage)**: nếu < 70% tiêu chí → chuyển sang chế độ `hoi_mo` để Friend hỏi thêm
  - Phát hiện **cognitive distortions** (lối tư duy tiêu cực): catastrophizing, black-and-white thinking…
  - Tính `muc_do_khung_hoang` (0–5) sau mỗi lượt chat
  - Tổng hợp điểm số tích lũy theo phiên và theo tuần (batch job offline)
  - Output: `KetQuaLamSang` – điểm PHQ-9/GAD-7, mức khủng hoảng, độ bao phủ, hành động đề xuất (`tiep_tuc_tro_chuyen` / `hoi_them_cau_mo` / `goi_y_tai_nguyen` / `chuyen_sos`)

---

#### Safety Guardrail – SOS Layer (Rule-based)
- **Cơ chế:** Chạy song song, không phụ thuộc LLM — đảm bảo phản hồi khủng hoảng dưới 2 giây.
- **Tính năng:**
  - **Input Guardrails (NeMo):** Lọc prompt injection, từ khóa độc hại, từ khóa khủng hoảng trước khi vào pipeline
  - **Crisis Detector:** Kích hoạt khi `muc_do_khung_hoang ≥ 4` hoặc phát hiện từ khóa tự hại → override toàn bộ flow
  - **Output Guardrails:** Kiểm tra hallucination, vấn đề đạo đức trên mọi phản hồi trước khi trả về user
  - **Render thẻ cứu hộ tĩnh:** Hotline `1800-599-920`, bản đồ phòng khám/bệnh viện gần nhất (Folium)
  - **Grounding exercise:** Gợi ý bài tập thở/grounding tức thì khi mức độ vừa (level 3)
  - Output: `HanhDongCuuHo` – mức độ khẩn cấp, hotline, thẻ cứu hộ, bài tập grounding

---

#### Tính năng UI/UX (Non-agent)

| Tính năng | Mô tả | Cơ chế |
|---|---|---|
| **Mood Picker (Home)** | Chọn trạng thái cảm xúc đầu ngày | Middleware ghi thẳng `lich_su_tam_trang`, không gọi LLM |
| **Quote of the Day** | Câu trích dẫn tạo động lực hàng ngày | Static content từ Knowledge Base |
| **Thiền ngắn (5 phút)** | Bài thiền có hướng dẫn âm thanh tiếng Việt | Static từ Self-help Library |
| **Biểu đồ xu hướng 7 ngày** | Hiển thị lịch sử cảm xúc (react-plotly.js) | Aggregate từ long-term storage qua Analyst batch |
| **Weekly Note** | Tổng kết tuần cá nhân hóa | Analyst tổng hợp → Friend rewrite (temp 0.4) |
| **Journal (Nhật ký)** | Ô viết nhật ký tự do có prompt gợi ý | Friend sinh prompt từ Knowledge Base |
| **Connect (Hotline + Map)** | Trang tài nguyên tham khảo luôn hiển thị | Static referral + Folium map; cũng xuất hiện tự động khi SOS kích hoạt |
| **Dashboard B2B** | Báo cáo tổng hợp ẩn danh cho nhà trường/tổ chức | Batch job offline, aggregate và ẩn danh hóa |

---

#### Tính năng Bảo mật & Hạ tầng (In-scope MVP)
- **PII Masking:** Che giấu thông tin cá nhân trước khi lưu vào bộ nhớ (Fernet symmetric)
- **Mã hóa dữ liệu:** AES-256 at rest, TLS 1.3 in transit
- **JWT Authentication:** Xác thực người dùng theo phiên
- **Working Memory:** Lưu 8 lượt hội thoại gần nhất để duy trì ngữ cảnh
- **Long-term Memory:** Event-based summary lưu PostgreSQL + pgvector cho cá nhân hóa
- **Disclaimer bắt buộc:** User tick xác nhận "AI không thay thế chuyên gia" khi đăng ký

### 8. Validation Metric

Thay vì dùng các chỉ số đánh giá phần mềm truyền thống, hệ thống sử dụng các chỉ số đo lường AI Agentic:

- **Safety Recall Rate (Tỷ lệ không bỏ sót rủi ro):** Đạt 100% trong việc nhận diện ý định tự hại/khủng hoảng. Đối với an toàn sinh mạng, *Recall (không bỏ sót)* quan trọng hơn *Precision (báo nhầm)*. Mọi ca nguy cơ đều phải được kích hoạt kịch bản khẩn cấp dưới 2 giây.
- **Latency & UX (Tốc độ & Trải nghiệm):** Agent 1 phải phản hồi trong khoảng 1-3 giây đối với các câu chat thông thường để duy trì ảo giác "chat với người thật".
- **User Engagement (Tỷ lệ giữ chân):** Số lượng phiên chat (sessions) vượt qua 10 lượt trao đổi (turn) thay vì người dùng thoát app ngay sau 1-2 tin nhắn.
- **Implicit Clinical Accuracy (Độ chuẩn xác ngầm):** Tỷ lệ khớp (Kappa score) > 85% giữa điểm số PHQ-9/GAD-7 do Agent 3 tự động gán nhãn so với kết quả đánh giá ngẫu nhiên của chuyên gia tâm lý trên cùng tập dữ liệu ẩn danh.

---

###