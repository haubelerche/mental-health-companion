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

---

### Tuần 4 — 26/04/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

#### Đã làm
- Hoàn thiện toàn bộ **DistressRouter** và **AnalystNode**: routing có điều kiện dựa trên `distress_score`, `AnalystBundle` chỉ đến `FriendNode` dưới dạng system prompt context — không bao giờ xuất hiện trực tiếp với user
- Implement **Memory Cards system**: CRUD đầy đủ, long-term summary, pgvector embedding cho RAG retrieval
- Build **SafetyFinalizer** + **CrisisInterventionPlanner**: crisis payload với `visible_text` và `voice_script` riêng, `CrisisLog` + `AdminAuditLog` ghi sync khi SOS
- Setup **Alembic migrations**: 30+ migration files, hoàn thiện toàn bộ DB schema
- Frontend: hoàn thiện Chat interface, Memory Cards UI, Persona Selector
- Viết thêm ~150 backend tests, tổng đạt **~600 passed**

#### Khó nhất tuần này
- `AnalystBundle` sanitization — phát hiện "rewrite-before-filter" pattern quan trọng: phải rewrite clinical language trước, sau đó mới filter để tránh bỏ mất context hữu ích. Mất 1 ngày để thiết kế đúng logic.
- Async TTS pipeline — phát hiện TTS không được block chat response. Thiết kế lại với outbox worker + dedup hash.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Review AnalystBundle sanitization logic, design CrisisInterventionPlan schema | Phát hiện edge case khi `clinical_note` bị pass nguyên sang FriendNode |
| Claude Code | Debug async TTS pipeline, thiết kế dedup strategy | Giảm duplicate TTS calls ~90% |

#### Học được
- "Rewrite trước, filter sau" là pattern đúng cho clinical language sanitization — ngược lại sẽ mất context hữu ích.
- Dedup hash `voice_script + style_id` là cách đơn giản và hiệu quả để tránh TTS flooding.
- `CrisisLog` phải ghi sync (không async) — không được để side effect delay khi có nguy cơ sinh mạng.

#### Kế hoạch tuần tới
- Implement PHQ-9/GAD-7 screening endpoint + frontend flow
- Build Resource Hub (wellness resources + YouTube integration)
- Thêm AutoCBT module
- Dashboard: mood chart, lifestyle rhythm, streak

---

### Tuần 5 — 03/05/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

#### Đã làm
- Hoàn thiện **PHQ-9/GAD-7 screening** backend: `POST /screenings/submit` → lưu `ClinicalProfile`, `GET /screenings/latest` → trả `severity_label` (không expose raw score)
- Frontend `syncScreeningResultsFromBackend()`: sync từ backend mỗi lần mount, fallback localStorage nếu API lỗi
- Build **Resource Hub**: `resource_library_service` + YouTube integration + wellness categories
- Implement **AutoCBT module**: CBT exercise flow với hướng dẫn từng bước
- Build **Dashboard**: mood chart (Recharts), lifestyle rhythm panel, streak tracker, memory summary
- **Push Notifications**: SSE endpoint + outbox worker + frontend notification handler
- Viết bộ security tests (`test_safety_bypass_adversarial.py`, `test_no_internal_leaks.py`, `test_idor_bola.py`, và 9 file khác)
- Tổng tests đạt **~850 passed**

#### Khó nhất tuần này
- Backend-authoritative screening — phát hiện race condition khi `syncScreeningResultsFromBackend()` gọi ngay lúc submit. Fix: so sánh `assessment_updated_at` timestamp, chỉ sync khi backend có record mới hơn.
- AutoCBT state machine — phức tạp hơn dự kiến do người dùng có thể skip, undo, hoặc abandon. Giải pháp: event-sourced state thay vì mutable step counter.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Design PHQ-9 backend schema, review timestamp comparison logic | Phát hiện race condition trong sync flow |
| Claude Code | Viết 12 security test files với 180+ assertions | Tiết kiệm ~2 ngày viết test |
| Claude Code | Debug AutoCBT state machine edge cases | Resolve 4 edge cases quan trọng |

#### Học được
- Backend-authoritative data cần timestamp comparison — client không được tự quyết định overwrite.
- Event-sourced state cho multi-step flows dễ debug và rollback hơn mutable counter.
- Security tests phải chạy được không cần live LLM — mock/stub LLM calls cho tất cả security assertions.

#### Kế hoạch tuần tới
- Xây dựng eval infrastructure: golden dataset, adversarial dataset, RAGAS, LLM-as-Judge
- Wire structured JSON logging + Prometheus metrics
- Tổng hợp báo cáo đánh giá cuối kỳ
- Polish UI + fix remaining bugs trước deadline

---

### Tuần 6 — 10/05/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

#### Đã làm
- Xây toàn bộ **eval infrastructure**:
  - Golden dataset: 30 → **88 cases** (thêm multi_turn, cultural_context, behavioral_activation)
  - Adversarial dataset: 20 → **50 cases** (thêm jailbreak_roleplay, multilingual_bypass, social_engineering)
  - RAGAS runner với BM25 heuristic (không cần OPENAI_API_KEY cho CI)
  - LLM-as-Judge với rubric 9 trục đánh giá
- Wire **Structured JSON logging** (python-json-logger) + **Prometheus** `/metrics` endpoint
- Hoàn thiện `AnalystSanitizer` — 23 tests, `rewrite-before-filter` pattern production-ready
- Viết AI Security test suite: 130 adversarial cases × 14 threat class, 12 backend security test files
- Fix SOS keyword heuristic: remove over-broad "không muốn sống", add "không muốn sống nữa" + "cut tay" (bilingual), add "lên kế hoạch rồi"
- Tổng tests đạt **901 passed, 0 failed**
- Blueprint score: **98.5/100 PASS**

#### Khó nhất tuần này
- SOS keyword tuning — "không muốn sống" quá broad, trigger false positive cho "không muốn sống như này nữa". Phải hiểu rõ Python substring matching để phân biệt đúng. Mất nửa ngày debug.
- RAGAS heuristic — token overlap cho tiếng Việt cho kết quả thấp do semantic gap. Giải pháp: BM25 + Vietnamese stopwords, tách hard-fail threshold (0.05) khỏi soft-review threshold (0.75).
- Linter tự động sửa file trong khi đang edit → Edit tool bị reject. Học được phải read lại file sau khi linter can thiệp.

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Toàn bộ eval infrastructure, SOS keyword tuning, observability wiring | Hoàn thành 6 tuần phát triển đúng deadline |
| Claude Code | Viết ARCHITECTURE.md, EVALUATION_EVIDENCE.md, README.md | Documentation đầy đủ cho nộp bài |
| Claude Code | Debug RAGAS heuristic, fix gate alias mapping | 88/88 golden PASS, 59/59 RAGAS PASS |

#### Học được
- Substring matching trong Python: `"không muốn sống nữa" in "không muốn sống như này nữa"` → False (substring không khớp khi có "như này" ở giữa). Đây là key insight để phân biệt SOS vs HIGH_DISTRESS.
- Eval infrastructure phải được build song song với product — không để đến cuối mới làm, sẽ không có đủ thời gian.
- BM25 tốt hơn token overlap cho Vietnamese NLP vì xử lý được term frequency + stopwords.

#### Nếu làm lại, sẽ làm khác
- Build eval suite từ tuần 2 thay vì tuần 6 — phát hiện vấn đề sớm hơn nhiều.
- Setup Prometheus từ đầu để có metrics trong toàn bộ development phase.
- Viết golden test cases ngay khi thiết kế feature — "eval-driven development".

#### Tổng kết dự án
Sau 6 tuần, Serene đạt:
- **901 backend tests** — 0 failed
- **88/88 golden eval cases** — 100% accuracy
- **0% P0 guardrail failures** — tất cả attack nguy hiểm bị block
- **98.5/100 blueprint score** — PASS
- Một AI companion tiếng Việt với safety system production-ready
