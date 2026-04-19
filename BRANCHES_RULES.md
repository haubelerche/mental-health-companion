## 1. Các nhánh chính (Core Branches)

Đây là xương sống của dự án, luôn tồn tại và cần bảo vệ nghiêm ngặt.

- **`main`**: Chứa code đã ổn định, sẵn sàng deploy. Mỗi commit ở đây tương ứng với một phiên bản "release candidate".
- **`develop`**: Nhánh tích hợp chính. Mọi tính năng mới đều được đưa vào đây để kiểm thử sự tương tác giữa các Agent trước khi đưa lên `main`.

---

## 2. Nhánh Feature (Theo Module Architecture)

### Nhánh hạ tầng AI (AI Infrastructure)

- **`feat/agent-core`**: Xây dựng lớp Base Agent, cấu hình LLM (GPT, Claude, local models) và cơ chế bộ nhớ (Short-term/Long-term memory).
- **`feat/graph-orchestrator`**: Phát triển luồng điều phối chính (LangGraph/StateGraph), quản lý trạng thái chuyển giao giữa các Agent (ví dụ: từ Agent sàng lọc sang Agent tư vấn).
- **`feat/knowledge-base-rag`**: Xây dựng GraphRAG hoặc VectorRAG chứa dữ liệu chuyên môn về tâm lý học (DSM-5, các liệu pháp CBT).

### Nhánh nghiệp vụ Agent (Specialized Agents)

- **`feat/agent-screening`**: Agent chuyên trách việc thực hiện các bài test tâm lý, sàng lọc ban đầu.
- **`feat/agent-empathy`**: Agent tập trung vào việc phản hồi đồng cảm và duy trì hội thoại tự nhiên.
- **`feat/agent-supervisor`**: Agent quản lý, kiểm soát chất lượng câu trả lời và đảm bảo an toàn y tế (Safety Guardrails).

### Nhánh Giao diện & Kết nối (System Integration)

- **`feat/backend-api`**: Xây dựng Fast API/NodeJS để kết nối Multi-Agent với người dùng cuối.
- **`feat/frontend-client`**: Giao diện chat, dashboard theo dõi sức khỏe tâm thần của người dùng.
- **`feat/database-schema`**: Thiết kế cơ sở dữ liệu lưu trữ lịch sử người dùng, profile bệnh lý.

---

## 3. Nhánh Kỹ thuật & Tối ưu (Technical & Optimization)

- **`feat/evals`**: Nhánh chuyên để đánh giá (Evaluation). Ví dụ: chạy các tập test để tính toán độ chính xác, tính nhất quán (Faithfulness) của Agent.
- **`feat/git-hooks-automation`**: Nơi bạn phát triển các công cụ tự động (như Git Hooks OpenAI bạn đang làm) để kiểm tra code hoặc format commit tự động.
- **`refactor/agent-logic`**: Tối ưu hóa lại code của các Agent hiện có mà không thay đổi tính năng.

---

## 4. Nhánh Khẩn cấp & Sửa lỗi (Fixes)

- **`fix/safety-bugs`**: Sửa các lỗi nghiêm trọng về an toàn thông tin hoặc phản hồi sai lệch của AI.
- **`fix/api-latency`**: Tối ưu hóa tốc độ phản hồi (như mục tiêu <5s bạn từng đặt ra).
- **`hotfix/...`**: Dùng để sửa trực tiếp lỗi trên `main` khi có vấn đề nghiêm trọng ở môi trường production.

---

## Bảng quy tắc đặt tên nhánh (Naming Convention)

| **Tiền tố (Prefix)** | **Mục đích** | **Ví dụ** |
| --- | --- | --- |
| `feat/` | Tính năng mới (Module lớn) | `feat/mental-health-scoring` |
| `fix/` | Sửa lỗi | `fix/memory-leak-in-graph` |
| `docs/` | Cập nhật tài liệu, README | `docs/agent-architecture` |
| `perf/` | Tối ưu hiệu năng (Latency, Token cost) | `perf/llm-streaming` |
| `test/` | Viết thêm Unit test hoặc Integration test | `test/agent-screening-logic` |

## Lời khuyên cho bạn:

Để tránh tình trạng "behind" hàng trăm commit như trong ảnh:

1. **Sử dụng Sub-tasks:** Nếu một module quá lớn (như `feat/agent-core`), bạn có thể chia nhỏ hơn một bậc như `feat/agent-core-memory`, nhưng sau khi xong hãy merge ngay vào `feat/agent-core`.
2. **Delete after merge:** Ngay sau khi một tính năng đã ổn định trên `develop`, hãy xóa nhánh feature đó để danh sách nhánh luôn gọn gàng.
3. **Atomic Commits:** Trong mỗi nhánh, hãy commit theo từng bước nhỏ kèm thông điệp rõ ràng, điều này quan trọng hơn việc chia quá nhiều nhánh vụn vặt.