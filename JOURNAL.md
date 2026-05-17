# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

### Tuần 1 — 05/04/2026

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

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

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

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

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng
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

**Thành viên:** Lương Thanh Hậu, Lê Hoàng Đạt, Lương Tiến Dũng

#### Đã làm (đối chiếu theo GitHub source graph)
- **Lương Thanh Hậu / `haubelerche`**:
  - PR #247 `feat/greetings-screening-results`, merge bởi **Hau Luong** lúc 17/05/2026 10:30: thêm khu vực tài nguyên cá nhân hóa cho trang Resource thông qua `backend/app/api/v1/routers/resources.py`, `frontend/src/components/pages/resource/ForYouSection.tsx`, `ResourceGrid.tsx`, `Resources.tsx`, và `frontend/src/services/resourceService.ts` (`e473f6f0`).
  - Dọn các tài liệu markdown/report ra khỏi nhánh review để giảm nhiễu khi merge tính năng (`f48eed78`).
  - Sửa render fallback voice trong lịch sử chat ở `frontend/src/components/pages/chat/Chat.tsx`, được merge vào PR #249 bởi **eltad2003** (`3178f3c1` / `ffab9828`).
  - Map persona voice sang biến môi trường ElevenLabs tường minh và bổ sung test hồi quy `backend/tests/test_tts_voice_id_resolution.py` (`54e06026`).
- **Lê Hoàng Đạt / `eltad2003`**:
  - Cập nhật journal sau PR #248 `feat/page-serene`, commit `docs: update journal doc` (`766214fd`), sau đó merge PR #248 vào `main` lúc 17/05/2026 10:46 (`afc6d733`).
  - Merge PR #249 `feat/greetings-screening-results` lúc 17/05/2026 11:49 để đưa fix voice fallback vào `main` (`b56dc64d`).
  - Trước đó trong cùng giai đoạn 16-17/05, xử lý các chỉnh sửa UI trên `feat/page-serene`: cấu hình Vercel (`8dcafe3e`), sửa text size (`7cbecbc2`), bỏ dark class và chỉnh wrapping mood chip (`0d578720`, `f3f596f2`, `fb342de9`, `8e671055`).

#### Khó nhất tuần này
- Git graph có nhiều merge song song giữa `feat/page-serene` và `feat/greetings-screening-results`, nên nhật ký phải phân biệt rõ **author của commit chức năng** với **người merge PR** để không gán nhầm công việc.
- PR #247 có một commit dọn tài liệu quy mô lớn bên cạnh thay đổi Resource; khi ghi log cần tách thay đổi sản phẩm thật khỏi thao tác giảm nhiễu review.
- Voice fallback phát sinh ở cả frontend chat history và backend TTS/persona voice mapping, nên cần ghi thành hai lớp fix riêng thay vì gom chung thành một mục "voice".

#### Kế hoạch tuần tới
- Kiểm tra lại trải nghiệm Resource personalization sau khi merge PR #247, đặc biệt dữ liệu gợi ý cá nhân hóa và fallback khi chưa đủ metadata.
- Chạy lại regression cho chat history voice fallback và TTS voice-id resolution trước khi demo.
- Chuẩn hóa journal/worklog theo Git graph sau mỗi PR để giảm rủi ro sai attribution giữa author và merger.

---

## Phụ lục attribution 7 tuần theo source graph

**Nguyên tắc ghi nhận:** Phần này ưu tiên GitHub source graph / local Git graph. Tên `haubelerche` và `Hau Luong` được xem là cùng một contributor khi email/handle trong graph trỏ về cùng tài khoản. Tên `dungltcn272` và `Lương Tiến Dũng` được gom cùng một contributor. Với tuần không có authored commit của một người trong graph, log ghi rõ trạng thái đó thay vì gán công việc không có bằng chứng.

**Kiểm tra tỷ trọng contribution:** Rà soát lại bằng `git shortlog` và `git log --branches --remotes --numstat` cho giai đoạn 31/03/2026 → 17/05/2026 cho thấy `haubelerche`/Hau Luong là contributor chính: 1.305 commit trong branch/remote graph, 293.163 insertions, 85.024 deletions, 378.187 dòng churn, tương đương khoảng 80,8% tổng churn đo được trong repository ở giai đoạn này. Vì raw Git metrics không chứng minh đúng con số 90%, journal ghi nhận `haubelerche` là người làm phần lớn hạ tầng, backend, agent runtime, safety/eval, CI và documentation core; các contributor còn lại được ghi theo phạm vi commit thực tế của họ.

### Tuần 1 — 31/03 → 05/04/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Xây hệ thống AI logging và AI PR review: pre-commit security checks, AI PR review bot, ignore `.ai-log`, mở rộng secret regex, tăng giới hạn diff, sửa command injection trong `run_git()`, sửa fallback staged diff, smart truncation theo ranh giới file, cập nhật model review, xử lý conflict nhánh hook, cập nhật `JOURNAL.md` tuần 1. Nguồn commit tiêu biểu: `5320d46f`, `af0f9b55`, `bd232e2b`, `532b5c61`, `c9a6664d`, `0966d9d6`, `f437fa24`, `c3b8bacb`, `b3ad9125`. |
| Lê Hoàng Đạt / `eltad2003` | Không thấy authored commit trong source graph ở mốc tuần 1. |
| Lương Tiến Dũng / `dungltcn272` | Không thấy authored commit trong source graph ở mốc tuần 1. |

### Tuần 2 — 06/04 → 12/04/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Hoàn thiện hook logging trước khi sang planning: thêm `log_manual.py`, enforce AI log check trong pre-push, sửa Python detection cho Anaconda/Miniconda, chuẩn hóa LF qua `.gitattributes`, sửa bug pre-hook, thêm test cho hook review. Đồng thời tạo bộ tài liệu Week 2 gồm architecture/planning docs, `WORKLOG`, API spec, frontend plan, DB schema Mermaid/mock data, cập nhật journal, xử lý các phát hiện security/schema từ AI review. Nguồn commit tiêu biểu: `a5b416fa`, `d2e70b3e`, `5c371393`, `804a6a48`, `cb1fb110`, `7261b6eb`, `178e1c3c`, `9450fc71`, `b024c69a`, `a57fafce`, `6ad7d671`, `227cbc78`, `88ec0f35`. |
| Lê Hoàng Đạt / `eltad2003` | Không thấy authored commit trong source graph ở mốc tuần 2. |
| Lương Tiến Dũng / `dungltcn272` | Bổ sung Problem Brief / phân tích vấn đề sản phẩm mental health theo commit `a9b2ef64` (`docs: Add Problem Brief`). |

### Tuần 3 — 13/04 → 19/04/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Mở rộng tài liệu kỹ thuật và backend foundation: cập nhật DB schema, problem brief, frontend/API/backend plan, sequence diagrams, data pipeline DSM/Neo4j/Postgres, Supabase database singleton, background worker, profile/session summarizer, test DB và Neo4j schema, FastAPI routers/schemas cho auth/chat/mood/journal/clinics/resources/safety/screening, cấu hình repo/docker/gitignore. Nguồn commit tiêu biểu: `dcebd6e6`, `5478b5ad`, `a41a95e1`, `59c64732`, `45cc57c9`, `c00308c3`, `df19fbe1`, `e40b048a`, `c7fe264d`, `e76424a5`, `25bde0d6`, `0730966d`, `757295ba`, `653845f8`, `c71d04c8`, `15d1a99c` đến `f8f3b8e2`. |
| Lê Hoàng Đạt / `eltad2003` | Xây frontend auth và shell ban đầu: login page, register page, route login/register, strong password validation, toast validation, CSS base directives, home/landing sections, sidebar/header/footer, routing sang chat, chat page mock-data, emoji picker, auto-scroll, register/login fixes. Nguồn commit tiêu biểu: `d6b0186f`, `8eab0c95`, `cba857c2`, `32cb6c49`, `dff369fe`, `983ebd41`, `1ac8c2a1`, `c945f627`, `dfcca5f3`, `484e0125`, `1919787e`, `5ee27c67`, `c3b35d56`, `339cb1f3`. |
| Lương Tiến Dũng / `dungltcn272` | Xây base backend độc lập: scaffold backend, app config/env contract, response envelope/error model, database session/lazy engine, core data models, Alembic migration workflow, security primitives/cookie helpers, auth endpoint atomic signup, Redis rate limiting, home/reflect/resources/connect/admin routes, audit logging, backend run guide và API test guide; sửa các lỗi security trọng yếu như admin auth bypass, hardcoded secrets, CSRF bypass, insecure defaults. Nguồn commit tiêu biểu: `00eacfdf`, `6fd13b6e`, `d3f75438`, `388b7c8d`, `1df700b9`, `d17a3316`, `2da99c12`, `57f8bc2f`, `c03a8d9a`, `d6db22c7`, `3a832efe`, `b5987f27`, `3974c9fc`, `27e94075`, merge PR #15 `3e26b587`. |

### Tuần 4 — 20/04 → 26/04/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Không thấy authored commit chính trong source graph ở mốc tuần 4; phần backend nền tảng của contributor này tập trung dày ở cuối tuần 3 và các tuần 6-7. |
| Lê Hoàng Đạt / `eltad2003` | Hoàn thiện các trang chính frontend: login flow, reflect page với mood trend chart dùng Recharts, setting page với profile/general settings, save localStorage, logout, switch Radix, chat page dropdown/debug/voice controls, accessibility/dropdown clipping, forget/reset password page. Nguồn commit/PR tiêu biểu: PR #44 `fcfb1377`, PR #47 `14174298`, PR #51 `5035bd4a`, PR #52 `6a0a9be7`, PR #53 `677d4163`, commits `b3a3c761`, `da5817df`, `51620a57`, `af60cb86`, `a3832604`, `b2b2b48d`, `712600ae`. |
| Lương Tiến Dũng / `dungltcn272` | Bổ sung email confirmation/forgot password backend: email config, verification token table, payload resend/forgot password, one-time token generation/hash, auth API update, DB/API docs, backend dependencies; thêm resource API cho admin, time formatting, security-time fix và admin request model cho quản trị tài nguyên. Nguồn commit tiêu biểu: `166474da`, `8cfbf17a`, `28d23ab1`, `253ebc44`, `98ffad9c`, `7afa3d95`, `f8015edb`, `743d34e4`, `0ca459e7`, `329c40a1`, `2fcfad6e`, `c0761683`, `ea6c917b`, `b8606116`, `780671ed`. |

### Tuần 5 — 27/04 → 03/05/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Không thấy authored commit chính trong source graph ở mốc tuần 5. |
| Lê Hoàng Đạt / `eltad2003` | Đẩy mạnh frontend product surface: chat history modal, settings logout/theme persistence, admin login layout, resource YouTube popup và expand list, onboarding/profile UI, landing animation/responsive navigation/logout, letter report modal/category/status, theme system/dark mode toàn app cho Home/Reflect/Connect/Nutrition/Profile/Setting/Chat/Resources/BeachMessage/global styles. Nguồn commit/PR tiêu biểu: PR #93 `083c6036`, PR #94 `77bd1b52`, PR #97 `b1cadb94`, PR #99 `3659d048`, PR #100 `1a2b6ae3`, PR #101 `1f686f44`, PR #102 `ef397c6f`, PR #103 `10076037`, commits `a6e95439`, `df34d640`, `ccdc8853`, `dafda365`, `47d0cf95`, `c05af5b5`, `637d5ff5`, `47fb908f`, `babb5cf2`. |
| Lương Tiến Dũng / `dungltcn272` | Xây Bamboo/letter backend và admin resource: Bamboo message table/API/model/test, dynamic anonymous names, reply threading, resource API/model/UI fixes, admin login/main/sidebar/crisis/resource/service, inbox table/API/send/seen logic/UI, backend mail/letter logic, report logic, notification model/WebSocket manager/auth/dispatcher/context/toast/setup, OAuth Google/Facebook backend/frontend, notification worker và letter notification. Nguồn commit/PR tiêu biểu: `36fded8a`, `ecabb81c`, `0104b62c`, `c9ded4fe`, `c625721f`, `d9ddb39b`, `d59e4b54`, `bbb57f6e`, `5dfa9129`, `928ae884`, `30afac25`, PR #98 `9d5224a5`, `79de0e7b`, `36710080`, `f8a4bcca`, `c2fdc6dd`, PR #129 `5574c1a8`, PR #130 `5f6ec182`. |

### Tuần 6 — 04/05 → 10/05/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Không thấy authored commit chính trong source graph ở mốc tuần 6. |
| Lê Hoàng Đạt / `eltad2003` | Hoàn thiện dark mode, resource/exercise/home/checkin/reflect/chat UI, auth refresh-token UI integration, GIF background system, reward page, sidebar/mobile nav, nutrition popup, streak/checkin logic, chat session persistence/history, notification popup, page reorganization, env URL handling. Nguồn commit/PR tiêu biểu: PR #127 `146bb117`, PR #128 `dae9d48c`, PR #131 `57fb5513`, PR #138 `d476d6a7`, PR #139 `e4bc6af0`, PR #149 `b034fadc`, PR #150 `89158b35`, PR #151 `3f49865c`, PR #152 `6426be40`, PR #154 `c0035ef3`, PR #155 `1728aaf1`, PR #156 `1262a40e`, PR #157 `0b840994`, PR #163 `3cd8426d`. |
| Lương Tiến Dũng / `dungltcn272` | Hoàn thiện notification/admin automation/resource agent: notification type/toast/WebSocket, letter/notification worker, admin resource management, YouTube/resource crawl endpoint và FE agent crawl, admin UI dashboard/audit/crisis/letter/notification/resource/user/analyst, worker manager/service/store/cards, admin automation, Docker multi-stage build, admin IP enforcement, SameSite cookie lax, API base URL refactor, fix pytest/admin timeout/time-notification. Nguồn commit/PR tiêu biểu: PR #153 `8c5c5015`, `b8e6e31c`, `c1470304`, `ae0d1fe0`, `72edc772`, `d08a2864`, `f675a03a`, `94652b27`, `6315e7fc`, `e44aab93`, `0c61d4ff`, PR #161 `3d8ab5fe`, PR #164 `e3565277`, PR #165 `46b9a9c3`, `5e7cfbf0`, `d801011b`, `c4c4aca4`. |

### Tuần 7 — 11/05 → 17/05/2026

| Thành viên | Việc đã làm theo source graph |
|---|---|
| Lương Thanh Hậu / `haubelerche` | Runtime/agent/safety/eval trọng tâm: chat orchestration và safety services, advisor retrieval/pool, mem0 memory migration, persona progression/unlock, app shell/client services, backend chat/safety regression tests, frontend/admin/assistant/wellness refresh, Serene runtime memory/analyst/SOS, privacy-preserving insight pipeline, SOS popup/crisis runtime, advisor/exercise support, ultra-fast chat path, Dũng persona AutoCBT docs/media, greetings/screening result actions, AutoCBT audit/test closures, LLM voice script generation, latency tuning, Supabase CI, Vietnamese mojibake fixes, LLM-as-Judge rubric, golden/guardrail eval runners, observability/Langfuse traces, analyst pipeline regression, personalized Resource section, chat history voice fallback, persona voice env mapping and TTS voice-id test. Nguồn commit/PR tiêu biểu: `66ab0089`, `c4409f6c`, `f09daeb9`, `b54ff8de`, `8e454667`, `832b2a8d`, `22ef4fd0`, `3c4d0305`, `99985e9b`, `5bc5269c`, `9f9ef5d4`, `819f8bda`, `d314f557`, `de2bcedf`, `44436841`, `5730c90e`, `c41987f8`, `ce123ceb`, `3d3c19cd`, `6a0a1f9e`, `fe9e303d`, `cc5b9e7c`, `e473f6f0`, `3178f3c1`, `54e06026`. |
| Lê Hoàng Đạt / `eltad2003` | Trang Serene/landing/exercise/screening/UI polish: landing page layout/sections/GIF/header/footer/CTA/persona/journey/why/feature, Vercel setup, exercise page layout/cards, nutrition meal check-in service/history, screening flow/result UI, health monitoring section, chat/letter/setting notification UI, mobile sidebar, login Google redirect fixes, insight UI, Reflect/Home/Setting/BeachMessage component updates, Logo component, route protection for auth/guest, guest session expiration, clear chat sessions on logout, build fixes, mood chip wrapping, text size fixes, merge PR #248/#249. Nguồn commit/PR tiêu biểu: `d329f004`, `1a87beaa`, `890262ff`, `84848808`, `dfdad8a8`, PR #200 `d2c58156`, `d6f811eb`, PR #205 `41c39772`, PR #206 `9949fd1`, `ceb3e4c5`, `3a2fc53c`, `286aafec`, `9dcc074e`, `38334275`, `891bbfa9`, `e3834466`, `b37bf900`, `ddb482e8`, `34c06fd8`, `3cb0d64a`, `7cbecbc2`, `8e671055`, `766214fd`, `afc6d733`, `b56dc64d`. |
| Lương Tiến Dũng / `dungltcn272` | Admin/notification/privacy/screening package: update admin automation, admin analysis/log UI/time fixes, notification immediate/seen/admin/letter fixes, ambient sound hook, exercise/admin update, letter fixes, eval-score v1/v2, remove OAuth test-user logic, verify-signup SMTP/resend fixes, meal check-in validation, privacy policy page, delete-user-description page, loading asset, DASS-21/MQD/PCL-5 question set. Nguồn commit/PR tiêu biểu: `875479c8`, `e22ab004`, `73d9c353`, `54e21cf1`, `22a56a52`, `46f794a5`, `1cdf07cb`, `28a839d8`, `4a3cd02e`, `5ae3481c`, `0d9875e7`, `8e734d8b`, `a24d8b24`, `4351f8f0`, `6dc4226f`, PR #227 `9086aa3b`, PR #229 `4865c122`, `13186f3e`, `ce3e1c49`, `d548fc1a`, PR #238 `67673bf6`. |

