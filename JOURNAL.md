# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

### Tuần 1 — 05/04/2026

**Thành viên:** Lê Hoàng Đạt, Lương Tiến Dũng, Lương Thanh Hậu

#### Đã làm
- Nghiên cứu và tích hợp Anthropic Tool Use API vào agent loop
- Xây dựng vòng lặp agent: model gọi tool → app xử lý → trả kết quả → model tiếp tục
- Setup dự án TypeScript, cấu hình type và schema cho tool input với `zod`
- Debug và sửa lỗi format message history khi dùng `tool_result`
- Thêm timeout cho các lời gọi API

#### Khó nhất tuần này
- Tool call response của Claude trả về sai format — mất 2 tiếng debug mới phát hiện ra thiếu `"type": "tool_result"` trong message history.
- Lần đầu dùng TypeScript nên type error khá nhiều, phải học cách dùng `as` và generic.


#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Giải thích Anthropic tool use API, debug message format | Giải quyết được bug trong 15 phút |
| Cursor | Autocomplete TypeScript types | Tiết kiệm khoảng 30% thời gian gõ |

#### Học được
- Tool use trong Claude hoạt động theo vòng lặp: model gọi tool → app trả kết quả → model tiếp tục. Cần giữ đúng message history.
- `zod` rất hữu ích để validate tool input schema.
- Nên đặt timeout cho API call ngay từ đầu, không để sau mới thêm.

#### Nếu làm lại, sẽ làm khác

#### Kế hoạch tuần tới
- Lựa chọn techstack sao cho phù hợp với dự án 






### Tuần 2 — 12/04/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng
#### Đã làm
- Xác định techstack chính thức: **React.js + FastAPI + LangGraph + PostgreSQL + pgvector**, deploy trên Railway
- Thiết kế kiến trúc Multi-Agent gồm 3 agent + 1 Safety Guardrail: Supervisor (GPT-4o-mini), Analyst (GPT-4o-mini + fewshot), Friend (GPT-4o), SOS Layer (rule-based)
- Định nghĩa toàn bộ State Schema (`TrangThaiSerene`) và output schema cho từng agent (`QuyetDinhDinhTuyen`, `KetQuaLamSang`, `PhanHoiHoiThoai`, `HanhDongCuuHo`)
- Vẽ và hoàn thiện 4 sơ đồ hệ thống: Flowchart tổng quan, Sequential Chart (1 lượt chat), State Diagram, User Journey
- Soạn PRD đầy đủ: User Stories, Acceptance Criteria, KPI metrics, chiến lược Sync/Async
- Soạn MVP Canvas: xác định target user (sinh viên Gen Z), job-to-be-done, pain points, 4 agent MVP và validation metrics
- Soạn Problem Brief: phân tích thị trường VN, phân tích đối thủ (Vmood, SnS, MindCare), xác định khoảng trống thị trường
- Tổ chức lại cấu trúc tài liệu vào thư mục `docs/` với các file: ARCHITECTURE.md, PRD.md, MVP_CANVAS.md, PROBLEM_BRIEF.md, DATA_DESCRIPTION.md, FRONTEND_PLAN.md

#### Khó nhất tuần này
- Cân bằng giữa độ phức tạp kỹ thuật (LangGraph orchestration, async clinical scoring) và trải nghiệm người dùng mượt mà (<3s latency). Giải pháp: tách luồng Sync (Friend response) và Async (Analyst scoring, PII masking).
- Quyết định ranh giới giữa các agent — Analyst không được nói trực tiếp với user để giữ tone nhất quán, mọi output lâm sàng phải đi qua Friend. Mất khá nhiều thời gian thảo luận để thống nhất nguyên tắc này.
- Thiết kế PHQ-9 scoring ngầm (implicit) mà không làm người dùng cảm thấy bị "hỏi cung" — phải nghĩ cách lồng câu hỏi khai thác vào hội thoại tự nhiên.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Hỗ trợ thiết kế State Schema, review kiến trúc LangGraph, góp ý PRD | Rút ngắn thời gian thiết kế khoảng 40%, phát hiện edge case recursion guard |
| ChatGPT | Brainstorm user journey, tham khảo cách đối thủ (Wysa, Woebot) xây flow | Có thêm góc nhìn về UX pattern cho mental health app |
| Cursor | Viết boilerplate Python schema (FastAPI + Pydantic), prototype React component | Tăng tốc viết code mẫu |

#### Học được
- LangGraph phù hợp cho stateful multi-agent hơn các framework khác vì có built-in checkpointing — critical cho mental health app cần giữ context dài.
- Với safety-critical system, luôn ưu tiên **Recall over Precision**: thà báo nhầm còn hơn bỏ sót ca khủng hoảng.
- Tách tài liệu ra từng file (PRD, Architecture, Canvas) thay vì gom chung giúp team dễ review và ít conflict hơn khi làm song song.
- `pgvector` + PostgreSQL đủ dùng cho RAG ở quy mô MVP, không cần thêm Pinecone hay Weaviate — giảm complexity đáng kể.

#### Nếu làm lại, sẽ làm khác
- Nên vẽ State Diagram trước rồi mới viết schema — thứ tự ngược lại khiến phải refactor schema nhiều lần.
- Nên prototype prompt Analyst sớm hơn để kiểm tra xem implicit PHQ-9 scoring có thực sự hoạt động không, thay vì chỉ thiết kế trên giấy.

#### Kế hoạch tuần tới
- Setup project structure: FastAPI + LangGraph boilerplate, kết nối PostgreSQL
- Implement Supervisor node và routing logic cơ bản
- Viết prompt đầu tiên cho Friend agent, test với vài scenario thực tế
- Setup NeMo Guardrails cho input/output filtering
- Dựng React UI skeleton: chat interface + quick replies component

### Tuần 3 — 19/04/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

#### Đã làm
- Hoàn thiện core orchestration theo mốc G3-W3: thêm node `supervisor` vào LangGraph (`START -> supervisor -> analyst|friend -> END`) với routing tối thiểu cho greeting/distress.
- Giữ chuẩn safety flow theo sequence diagram: `decide_sos` chạy trước graph; khi SOS thì không invoke LangGraph trong cùng request.
- Bổ sung bộ test backend cho core agent:
  - `backend/tests/test_langgraph_chat.py`
  - `backend/tests/test_safety_and_sos.py`
  - `backend/tests/test_chat_router_integration.py`
- Kết quả test: `pytest backend/tests -q` => **9 passed**.
- Cập nhật CI tại `.github/workflows/review-pr.yml`: thêm job `backend-tests` chạy pytest trước job review.

#### Bottleneck tuần này
- Điểm nghẽn lớn nhất là thiếu test tự động cho chat/agent khiến khó chứng minh DoD "tests passing".
- Độ phức tạp của integration test (phụ thuộc DB/deps) được giảm bằng cách dùng dependency override + monkeypatch cho nhánh core cần xác minh.

#### Kịch bản đã verify
- Non-SOS message đi qua graph và trả về envelope chuẩn (`success=true`, `sos_triggered=false`).
- SOS message đi nhánh emergency, ghi side effects, và **không chạy** graph trong request đó.
- Supervisor routing:
  - greeting nhẹ có thể skip analyst để giảm latency
  - distress cao hoặc mood căng thẳng sẽ qua analyst trước khi friend phản hồi
  - analyst cap được tôn trọng.

#### Học được
- Thiết kế fallback no-API-key rất hữu ích để giữ test ổn định trong CI.
- Tách rõ "functional path" và "safety path" giúp debugging nhanh hơn và giảm regression ở giai đoạn MVP.

#### Kế hoạch tuần tới
- Mở rộng routing intent của supervisor (chi tiết hơn cho distress vs normal chat) và chuẩn hóa schema output giữa các node.
- Nâng integration test fidelity bằng test DB thật (test container hoặc DB test riêng) khi hạ tầng sẵn sàng.
