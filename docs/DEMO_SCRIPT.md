# Serene - Kịch bản video demo 3-5 phút

## Context

Video demo cần thuyết minh ba nội dung bắt buộc: bài toán, tính năng chính và luồng xử lý AI Agent. Kịch bản này được thiết kế để nhóm quay trong 3-5 phút, đủ ngắn cho yêu cầu form nhưng vẫn chứng minh được kiến trúc safety-first.

## Problem Statement Technical Deep-Dive

Serene không nên được demo như một chatbot tổng quát. Giá trị cốt lõi cần thể hiện là: người dùng có thể chia sẻ riêng tư bằng tiếng Việt, hệ thống phản hồi đồng cảm nhưng không chẩn đoán, phân tích pattern nội bộ để tạo insight, và chuyển sang luồng SOS có kiểm soát khi có tín hiệu nguy cơ cao.

| Phân đoạn | Thời lượng | Mục tiêu |
|---|---:|---|
| Mở bài | 20-30 giây | Nêu vấn đề và định vị Serene |
| Demo luồng bình thường | 80-110 giây | Chat, check-in, resource, dashboard |
| Demo luồng AI Agent | 60-80 giây | SafetyGate, AnalystNode, FriendNode, async side effects |
| Demo luồng SOS | 40-60 giây | SafetyFinalizer, hotline/referral, no-diagnosis boundary |
| Kết quả và evidence | 30-40 giây | Test/eval metrics và tài liệu |
| Kết thúc | 10-20 giây | Nhắc link GitHub, architecture, evidence |

## Technical Deep-Dive

### 1. Lời mở đầu

Nội dung nói:

Serene là AI mental-health companion bằng tiếng Việt dành cho sinh viên và người trẻ Việt Nam. Dự án giải quyết khoảng trống hỗ trợ tâm lý ban đầu: người dùng cần một nơi riêng tư để nói thật, nhận hỗ trợ tức thời và biết bước tiếp theo, nhưng hệ thống không chẩn đoán và không thay thế chuyên gia.

Màn hình gợi ý:

Landing page hoặc màn hình đăng nhập, sau đó chuyển nhanh vào chat.

### 2. Demo luồng người dùng bình thường

Tin nhắn mẫu:

```text
Dạo này mình áp lực quá, ngủ không ngon, cứ nghĩ đến deadline là thấy nghẹt thở.
```

Điểm cần nói khi quay:

| Màn hình | Nội dung thuyết minh |
|---|---|
| Chat | Serene phản hồi bằng tiếng Việt tự nhiên, xác nhận cảm xúc, không dùng ngôn ngữ chẩn đoán |
| Persona | Persona chỉ là style mode, không tạo nhiều danh tính gây lệch safety |
| Check-in | Người dùng ghi mood, emotion, trigger, sleep/energy để hệ thống có dữ liệu structured |
| Resource Hub | Hệ thống gợi ý breathing, grounding, sleep routine hoặc resource phù hợp |
| Dashboard | Mood trend, trigger-emotion pattern, lifestyle rhythm và next steps giúp người dùng tự quan sát |

### 3. Giải thích AI Agent Flow

Nội dung nói:

Mỗi lượt chat đi qua SafetyGate trước khi gọi LLM. Nếu tín hiệu bình thường, DistressRouter quyết định có cần AnalystNode hay không; AnalystNode chỉ tạo structured bundle nội bộ, không nói trực tiếp với người dùng. FriendNode dùng bundle đó để phản hồi với tone Serene. Memory, TTS, Neo4j sync và dashboard insight chạy bất đồng bộ qua outbox để giảm latency.

Sơ đồ nói ngắn:

```text
User -> Frontend -> FastAPI -> SafetyGate
     -> DistressRouter -> AnalystNode -> FriendNode -> Response
     -> Async Outbox: Memory, TTS, Dashboard, Graph Sync
```

### 4. Demo luồng SOS

Tin nhắn mẫu chỉ dùng trong môi trường demo kiểm soát:

```text
Mình đã lên kế hoạch rồi, tối nay mình sẽ làm.
```

Điểm cần nói:

| Cơ chế | Ý nghĩa |
|---|---|
| SafetyGate | Chạy trước LLM, phát hiện tín hiệu nguy cơ cao bằng rule-based logic |
| SafetyFinalizer | Bypass normal chat flow, không đưa cho FriendNode trả lời tùy ý |
| Crisis payload | Trả de-escalation text, micro-action và hotline/referral |
| Audit log | Ghi crisis/audit event để có bằng chứng vận hành |
| Boundary | Serene không chẩn đoán, không đưa chỉ dẫn nguy hiểm, không thay chuyên gia |

### 5. Kết quả và evidence

Nội dung nói:

Repository có 901 backend tests theo báo cáo hiện có, 88/88 golden conversation cases pass, 50 adversarial guardrail cases không có fail, 59 RAGAS heuristic questions không có hard fail và AI security attackset 130 cases. Các tài liệu chính nằm trong `docs/ARCHITECTURE.md`, `docs/EVALUATION_EVIDENCE.md`, `JOURNAL.md`, `WORKLOG.md` và `SUBMISSION_REPORT.md`.

## Strategic Recommendations

| Rủi ro demo | Cách kiểm soát |
|---|---|
| Video quá dài | Cắt bớt phần UI phụ, ưu tiên chat, dashboard, SOS, architecture |
| Demo gây hiểu nhầm là chẩn đoán | Luôn nhắc "không chẩn đoán, không thay thế chuyên gia" |
| Live backend lỗi | Chuẩn bị sẵn local recording hoặc ảnh chụp màn hình, nhưng phải nói rõ nếu là bản local |
| Link video bị khóa | Kiểm tra bằng cửa sổ ẩn danh trước khi nộp |
| Dữ liệu cá nhân xuất hiện | Dùng tài khoản demo và dữ liệu giả |
