## 1. TỔNG QUAN SẢN PHẨM
## Thông tin dự án
- **Tên cụ thể**: Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
- **Stack**: React.js + FastAPI + LangGraph + PostgreSQL + pgvector
- **Ngày**: 2026-04-12
- **Phiên bản**: 1.0
---
### 1.1. Mục tiêu chiến lược

Xây dựng một không gian "xả stress" an toàn, thấu cảm, xóa bỏ rào cản tâm lý (stigma) bằng cách ngụy trang các nghiệp vụ lâm sàng dưới hình thức trò chuyện với người đồng trang lứa (Peer-to-Peer). Hệ thống ưu tiên trải nghiệm người dùng (UX) mượt mà đồng thời đảm bảo an toàn sinh mạng tuyệt đối thông qua cơ chế giám sát ngầm.

### 1.2. Giá trị cốt lõi

- **Trải nghiệm "Tàng hình" (Invisible Clinical Layer):** Chẩn đoán và sàng lọc diễn ra bất đồng bộ, không làm gián đoạn dòng cảm xúc của người dùng.
- **Phản hồi tức thì (Real-time Empathy):** Duy trì độ trễ thấp để tạo cảm giác kết nối thực thụ.
- **An toàn tuyệt đối (Crisis First):** Ưu tiên nhận diện rủi ro tự hại lên trên mọi tác vụ khác.

## 2. TÍNH NĂNG CỐT LÕI

### 2.1. Peer Chat (Trò chuyện thấu cảm)

- **Mô tả:** Giao diện nhắn tin thời gian thực với Peer Agent.
- **Đặc điểm:** Sử dụng ngôn ngữ Gen Z, từ lóng phù hợp ngữ cảnh, tuyệt đối không dùng thuật ngữ y khoa chuyên môn trong luồng chat trực tiếp.
- **Cơ chế:** Áp dụng kỹ thuật *Validation* (Xác nhận cảm xúc) trước khi đưa ra bất kỳ gợi ý nào.

### 

### 2.2. Invisible Screening (Sàng lọc ngầm)

- **Mô tả:** Tự động phân tích lịch sử hội thoại để trích xuất điểm số lâm sàng.
- **Chỉ số:** Tính điểm PHQ-9 (Trầm cảm) và GAD-7 (Lo âu).
- **Lưu trữ:** Kết quả được đẩy vào Namespace `/clinical/` trong cơ sở dữ liệu, phục vụ báo cáo vĩ mô hoặc can thiệp chuyên sâu mà không cần người dùng điền khảo sát.

### 2.4. Crisis Guardrail (Bảo vệ khẩn cấp)

- **Mô tả:** Hệ thống giám sát ý định tự hại (Suicide Ideation) 24/7.
- **Cơ chế:** Sử dụng Safety Agent quét liên tục ngữ cảnh. Nếu vượt ngưỡng rủi ro, hệ thống kích hoạt luồng *Human-in-the-loop*, hiển thị Hotline hoặc thông báo cho bộ phận ứng cứu.

---

## 3. KIẾN TRÚC HỆ THỐNG VÀ DỮ LIỆU

### 3.1. Mô hình điều phối (Multi-Agent Orchestration)

Hệ thống vận hành trên nền tảng **LangGraph** với cấu trúc phân cấp:

- **Router Agent:** Phân loại ý định (Intent) và điều hướng cuộc hội thoại.
- **Evaluator-Optimizer Pattern:** LLM 1 (Peer) soạn thảo phản hồi, LLM 2 (CBT Evaluator) kiểm soát và chỉnh sửa bản nháp nếu phát hiện lỗi tư duy (Cognitive Distortions) trước khi gửi đến người dùng.

### 3.2. Chiến lược xử lý Đồng bộ & Bất đồng bộ (Sync/Async)

| **Luồng xử lý** | **Tác vụ** | **Mục tiêu** |
| --- | --- | --- |
| **Đồng bộ (Sync)** | Peer Response, RAG Retrieval, Safety Check | Đảm bảo phản hồi < 3 giây, duy trì mạch hội thoại. |
| **Bất đồng bộ (Async)** | Clinical Scoring, Context Compression, PII Masking | Xử lý các tác vụ nặng, tóm tắt phiên chat, lưu trữ dài hạn. |

### 3.3. Quản lý bộ nhớ và Cơ sở dữ liệu (Memory OS)

- **Short-term Memory:** Sử dụng Redis hoặc LangGraph Checkpointer để lưu giữ trạng thái hội thoại hiện thời.
- **Long-term Memory:** PostgreSQL tích hợp `pgvector` để lưu trữ Vector Embeddings từ RAG và tóm tắt hội thoại sau khi đã ẩn danh hóa (Anonymization).
- **Bảo mật:** Quy trình PII Masking bắt buộc trước khi lưu dữ liệu vào Database để tuân thủ HIPAA/FERPA.

---

## 4. USER STORIES & ACCEPTANCE CRITERIA

| **Tiêu đề** | **User Story** | **Tiêu chí nghiệm thu (Acceptance Criteria)** |
| --- | --- | --- |
| **Giao tiếp tự nhiên** | Là sinh viên đang stress, tôi muốn được chào đón bằng ngôn ngữ thấy cảm và gần gũi để không cảm thấy bị "bệnh lý hóa". | 1. Phản hồi < 3s.
2. Không dùng từ chuyên môn.
3. Có câu xác nhận cảm xúc. |
| **Hỗ trợ thực tế** | Là sinh viên gặp rắc rối học vụ, tôi muốn nhận giải pháp từ trường để giải quyết vấn đề ngay. | 1. Truy xuất đúng thông tin trường học.
2. Trích dẫn tự nhiên vào hội thoại. |
| **An toàn sinh mạng** | Là người dùng bế tắc, tôi muốn hệ thống nhận diện nguy cơ tự hại để cung cấp hotline kịp thời. | 1. Safety Agent hoạt động 24/7.
2. Kích hoạt Hotline Pop-up ngay khi rủi ro vượt ngưỡng. |
| **Báo cáo chuyên môn** | Là chuyên viên tâm lý, tôi muốn có điểm PHQ-9/GAD-7 tự động để theo dõi sức khỏe SV. | 1. Cập nhật điểm ngầm vào DB.
2. Dữ liệu phải được mã hóa/ẩn danh (PII Masking). |

---

## 5. QUY TRÌNH NGƯỜI DÙNG (USER JOURNEY)

1. **Tiếp nhận (Trigger):** Người dùng gặp áp lực (VD: 1h sáng làm đồ án), mở ứng dụng.
2. **Định danh (Onboarding):** Đăng nhập tối giản (ẩn danh), chọn trường học/tâm trạng qua Emoji.
3. **Tương tác (Engage):** Người dùng chia sẻ sự tiêu cực.
4. **Phân loại ngầm (Triage):** Router Agent đánh giá mức độ khẩn cấp. Safety Agent quét rủi ro.
5. **Phản hồi tối ưu:** Peer Agent kết hợp cùng CBT Evaluator đưa ra câu trả lời thấu cảm, lồng ghép kỹ năng đối phó từ RAG.
6. **Kết thúc & Lưu trữ:** Sau khi người dùng thoát, hệ thống tự động tóm tắt (Summarization), chấm điểm lâm sàng và lưu vào kho dữ liệu an toàn.

---

## 6. CHỈ SỐ ĐO LƯỜNG HIỆU QUẢ (KPIS)

- **Safety Recall Rate (Mục tiêu 100%):** Không bỏ sót bất kỳ trường hợp có ý định tự hại nào.
- **System Latency (Mục tiêu < 3s):** Thời gian phản hồi trung bình (TTFT) để đảm bảo tính tự nhiên.
- **Implicit Clinical Accuracy (Mục tiêu > 85%):** Độ tương đồng giữa điểm số AI chấm và chuyên gia tâm lý chấm độc lập.
- **User Engagement (Mục tiêu > 10 turns):** Tỷ lệ phiên hội thoại sâu, thể hiện sự tin tưởng của người dùng.
- **PII Compliance:** 100% dữ liệu lưu trữ dài hạn không chứa thông tin định danh cá nhân trực tiếp.

---