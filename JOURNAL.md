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

### Tuần 4 — 26/04/2026

**Thành viên:** Lê Hoàng Đạt, Lương Tiến Dũng, Lương Thanh Hậu

#### Đã làm (dựa trên Pull Requests)
- `feat/frontend-v2-complete`: Hoàn thiện giao diện frontend V2.
- `feat/chat-realtime-guest-flow` & `feat/guest-chat-countdown`: Cập nhật luồng chat realtime và đếm ngược cho người dùng guest.
- `feat/auth-latency-core` & `feat/auth-latency-test-files`: Tối ưu và test độ trễ xác thực.
- `feat/friend-empathy-and-voice-safety`: Cập nhật logic empathy và safety cho Friend agent.
- `feat/page-chat`, `feat/page-forget`, `feat/page-setting`, `feat/page-reflect`, `feat/page-login`: Dựng và hoàn thiện các trang chính của ứng dụng.
- `feat/auth-me-csrf-loopback` & `feat/email-confirmation`: Nâng cấp bảo mật CSRF và xác nhận email.
- `feat/resources-management-for-admin`: Bắt đầu tính năng quản lý tài nguyên cho admin.

#### Khó nhất tuần này
- Đồng bộ giao diện frontend V2 với luồng dữ liệu mới.
- Xử lý các edge cases trong luồng auth và chat realtime.

#### Kế hoạch tuần tới
- Refactor code và cải thiện layout, data routing.

### Tuần 5 — 03/05/2026

**Thành viên:** Lê Hoàng Đạt, Lương Tiến Dũng, Lương Thanh Hậu

#### Đã làm (dựa trên Pull Requests)
- `pr/4-pages-refactor` & `pr/2-data-and-layout`: Refactor toàn diện 4 trang chính, data binding và layout.
- `feat/main-wellness-suite-xp-v2` & `feat/main-data-layout-xp`: Tích hợp Wellness Suite experience v2 và tối ưu layout dữ liệu.
- `feat/pr01-data-routing-wellness-foundation`: Thiết lập foundation cho data routing của Wellness.

#### Khó nhất tuần này
- Refactor cấu trúc data và layout đảm bảo không phá vỡ các chức năng hiện tại.

#### Kế hoạch tuần tới
- Tiếp tục phát triển và hoàn thiện các luồng dữ liệu liên quan đến Wellness.

### Tuần 6 — 10/05/2026

**Thành viên:** Lê Hoàng Đạt, Lương Tiến Dũng, Lương Thanh Hậu

#### Đã làm
- Tập trung vào nghiên cứu và lên kế hoạch cho các tính năng đánh giá tâm lý (Screening) và AutoCBT.
- Chuẩn bị tài liệu và PRD cho persona "Dũng".

#### Kế hoạch tuần tới
- Triển khai trang Serene, AutoCBT và các bài test tâm lý (DASS-21, MQD, PCL-5).

### Tuần 7 — 17/05/2026

**Thành viên:** Lê Hoàng Đạt, Lương Tiến Dũng, Lương Thanh Hậu

#### Đã làm (dựa trên Pull Requests)
- `feat/page-serene`: Phát triển và hoàn thiện trang Serene.
- `feat/greetings-screening-results`: Tích hợp kết quả screening vào luồng chào hỏi và onboarding.
- `feat/autocbt-prd-dung-persona-docs` & `feat/autocbt-audit-and-tests`: Thêm PRD, tài liệu cho persona Dũng và các audit/test cho AutoCBT.
- `feat/add-dass21-mqd-pcl5-questions`: Tích hợp bộ câu hỏi đánh giá tâm lý (DASS-21, MQD, PCL-5).
- `feat/remaining-risks-fix`: Khắc phục các rủi ro còn tồn đọng từ các tính năng trước.

#### Khó nhất tuần này
- Đảm bảo logic chấm điểm các bài test tâm lý chính xác và tích hợp mượt mà vào trải nghiệm chatbot.
- Kiểm thử luồng AutoCBT với các kịch bản safety phức tạp.

#### Kế hoạch tuần tới
- Chuẩn bị báo cáo tiến độ và demo các tính năng mới nhất.

