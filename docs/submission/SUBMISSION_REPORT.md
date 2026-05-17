# Serene - Báo cáo tổng hợp nộp bài AI20K Build Phase

**Ngày cập nhật:** 17/05/2026  
**Repository:** `A20-App-039`  
**Trạng thái:** Sẵn sàng về mã nguồn, kiến trúc, nhật ký phát triển, bằng chứng đánh giá và tài liệu nộp bài; các liên kết Live URL, Video Demo và Pitch Deck cần được thay bằng đường dẫn công khai trước khi điền form chính thức.

## Context

Tài liệu này tổng hợp toàn bộ nội dung cần nộp theo `HUONGDANNOPBAI_full.md`, bao gồm source code, README, kiến trúc, AI logs, weekly journal, worklog, evaluation evidence, demo assets và checklist trước khi nộp. Báo cáo được viết theo góc nhìn sản phẩm và kỹ thuật để người chấm có thể kiểm tra nhanh cả năng lực triển khai lẫn mức độ tuân thủ quy định nộp bài.

| Hạng mục nộp bài | Trạng thái trong repository | Đường dẫn bằng chứng |
|---|---|---|
| Source code đầy đủ | Đã có frontend, backend, database migrations, AI/agent logic, API, eval runners và cấu hình deploy | `frontend/`, `backend/`, `evals/`, `scripts/`, `docker-compose.yml` |
| README gốc | Đã có mô tả dự án, mục tiêu, tính năng, công nghệ, cài đặt, chạy và hướng dẫn sử dụng | `README.md` |
| Architecture | Đã có tài liệu kiến trúc và luồng dữ liệu chính | `docs/ARCHITECTURE.md` |
| AI logs và hook | Đã có cấu hình hook cho các AI coding tools; không commit `.ai-log/*.jsonl` | `.codex/hooks.json`, `.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`, `scripts/setup_hooks.sh` |
| Weekly journal | Đã ghi quá trình theo tuần, kết quả, khó khăn, công cụ AI đã dùng và bài học | `JOURNAL.md` |
| Worklog | Đã ghi ADR, phân công, brainstorming và quyết định kỹ thuật | `WORKLOG.md` |
| Evaluation evidence | Đã có báo cáo test, eval, guardrail, RAGAS heuristic và AI security | `docs/EVALUATION_EVIDENCE.md`, `evals/reports/` |
| Pitch deck outline | Đã có nội dung nguồn để tạo slide 5-10 trang | `README_SLIDE_DECK.md` |
| Submission package | Đã bổ sung chỉ mục và hướng dẫn nộp cuối | `docs/SUBMISSION_PACKAGE.md` |

## Problem Statement Technical Deep-Dive

Serene giải quyết khoảng trống hỗ trợ tâm lý ban đầu cho sinh viên và người trẻ Việt Nam: người dùng thường có nhu cầu chia sẻ áp lực, lo âu, mệt mỏi hoặc dấu hiệu nguy cơ, nhưng trì hoãn tìm chuyên gia do kỳ thị xã hội, chi phí, thời gian, thiếu kênh riêng tư và thiếu sản phẩm hiểu ngữ cảnh tiếng Việt. Dự án không định vị là bác sĩ AI, không chẩn đoán bệnh và không thay thế chuyên gia; Serene là lớp emotional first-aid có guardrail, có khả năng lắng nghe, sàng lọc tín hiệu ban đầu, gợi ý hành động nhỏ và chuyển hướng tới hotline hoặc nguồn lực hỗ trợ khi vượt ngưỡng an toàn.

Rủi ro cốt lõi không nằm ở việc tạo thêm một chatbot, mà nằm ở việc quản trị tam giác kỹ thuật sau:

| Yếu tố | Yêu cầu | Cách Serene xử lý |
|---|---|---|
| Scalability | Chi phí LLM và side effects phải được kiểm soát khi số lượng người dùng tăng | Fast path cho greeting/small talk, outbox bất đồng bộ cho TTS/memory/Neo4j, eval heuristic có thể chạy trong CI |
| Reliability | Safety không được phụ thuộc hoàn toàn vào LLM không deterministic | SafetyGate rule-based trước mọi luồng LLM, SafetyFinalizer tách khỏi FriendNode, bộ test adversarial |
| Latency | Chat cảm xúc cần phản hồi nhanh nhưng không được bỏ qua safety | SafetyGate và response chính chạy đồng bộ; scoring, memory, TTS và graph sync chạy bất đồng bộ |

## Technical Deep-Dive

### 1. Kiến trúc sản phẩm và runtime

Serene dùng kiến trúc lightweight multi-agent trên FastAPI và LangGraph. Luồng chat chính:

```text
User -> React Frontend -> FastAPI Router -> SafetyGate
     -> Normal: DistressRouter -> AnalystNode nếu cần -> FriendNode -> Response
     -> SOS: SafetyFinalizer -> CrisisInterventionPlanner -> Hotline/Referral -> Response
     -> Async: Memory, TTS, Analyst batch, Neo4j sync, Dashboard insight
```

| Thành phần | Vai trò | File hoặc module tiêu biểu |
|---|---|---|
| Frontend | Chat, dashboard, reflect, resource hub, screening, rewards, admin | `frontend/src/components/pages/`, `frontend/src/components/dashboard/` |
| Backend API | Auth, chat, safety, dashboard, resources, notifications, admin | `backend/app/api/v1/routers/` |
| SafetyGate | Quy định route an toàn trước LLM | `backend/app/safety/`, `backend/app/services/langgraph_chat.py` |
| Analyst | Phân tích nội bộ, evidence refs, context loader, không user-facing | `backend/app/services/analyst_agent.py`, `backend/app/services/analyst_context_loader.py` |
| Friend | Phản hồi người dùng theo tone Serene và output policy | `backend/app/services/friend_agent.py` |
| Database | PostgreSQL/Alembic là source of truth; Neo4j chỉ là derived graph | `backend/app/services/db/models.py`, `backend/alembic/versions/` |
| Evaluation | Golden, guardrail, RAGAS, judge, AI security | `evals/`, `backend/tests/` |

### 2. Tính năng chính đã có

| Nhóm tính năng | Nội dung |
|---|---|
| Chat AI tiếng Việt | Hội thoại tự nhiên với persona Serene, có fast path cho small talk và advisor-assisted path khi cần |
| Safety/SOS | Phát hiện nguy cơ, block persona không phù hợp, sinh crisis payload, hotline/referral, crisis/audit log |
| Screening | PHQ-9/GAD-7 và các trường mở rộng trong `ClinicalProfile`; frontend đồng bộ với backend |
| Dashboard | Mood trend, mood by period, lifestyle rhythm, data quality badge, insight cards |
| Memory | Memory cards, mem0 repository, session summary, context recall |
| Resource Hub | Tài nguyên wellness, YouTube/resource candidate injection, seed script |
| Voice/TTS | Voice policy, TTS worker, dedup và tách `visible_text` với `voice_script` |
| Admin/Observability | Admin routes, audit log, Langfuse tracing, structured logging, Prometheus metrics |

### 3. Bằng chứng đánh giá

| Bộ đánh giá | Quy mô | Kết quả hiện tại |
|---|---:|---|
| Backend pytest | 901 tests theo báo cáo hiện có | 901 passed, 0 failed trong `docs/EVALUATION_EVIDENCE.md` |
| Golden conversation eval | 88 cases | 88 pass, 0 fail |
| Adversarial guardrails | 50 cases | 44 pass, 6 skip cần live backend, 0 fail |
| LLM-as-Judge heuristic | 50 cases | 50 pass |
| RAGAS heuristic | 59 questions | 59 review, 0 hard fail |
| AI security offline | 130 adversarial cases | Báo cáo tại `evals/reports/latest_ai_security_report.md` |

Các kết quả trên là bằng chứng regression engineering và guardrail coverage, không phải clinical validation. Khi trình bày, nhóm cần nói rõ ranh giới này để tránh gây hiểu nhầm rằng hệ thống đã được kiểm định y khoa.

### 4. AI logs và quá trình phát triển

Repository đã có cơ chế logging prompt tự động qua hooks cho Claude Code, Cursor, Codex, Gemini CLI và GitHub Copilot. Theo guideline dự án, agent không cần và không nên commit `.ai-log/*.jsonl`; các file này được gitignore và submit tự động khi `git push` nếu hook đã cài.

| Thành phần | Mục đích |
|---|---|
| `scripts/setup_hooks.sh` | Cài pre-push hook một lần trước khi PR hoặc push |
| `scripts/log_hook.py` | Ghi prompt/session vào `.ai-log/session.jsonl` |
| `scripts/submit_log.py` | Gửi log tự động khi push |
| `.codex/hooks.json` | Cấu hình OpenAI Codex hook |
| `.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json` | Cấu hình các AI tool khác |

## Strategic Recommendations

### Ưu tiên trước khi nộp form

| Ưu tiên | Việc cần làm | Lý do |
|---:|---|---|
| 1 | Thay placeholder `Live URL`, `Video Demo`, `Pitch Deck` ở đầu `README.md` | Đây là điểm đầu tiên người chấm và form nộp bài cần |
| 2 | Chạy `bash scripts/setup_hooks.sh` trước khi push hoặc tạo PR | Đây là yêu cầu bắt buộc trong `AGENTS.md` |
| 3 | Chạy test/eval tối thiểu nếu có thời gian | Xác minh worktree cuối không phá regression |
| 4 | Không commit `.ai-log/*.jsonl`, DB local hoặc artifact tạm | Giữ repository sạch và đúng chính sách dữ liệu |
| 5 | Ghi rõ các case `SKIP` cần live backend trong evidence | Tránh biến kết quả offline thành kết quả runtime chưa verify |

### Checklist nộp bài

| Mục | Trạng thái | Ghi chú |
|---|---|---|
| README có mô tả, mục tiêu, tính năng, công nghệ, cài đặt, chạy, sử dụng | Đã có | Cần thay placeholder link |
| Architecture có User, Frontend, Backend/API, Database, AI/LLM, External Services | Đã có | `docs/ARCHITECTURE.md` |
| Journal theo tuần | Đã có | `JOURNAL.md` |
| Worklog có phân công, công việc, thời gian, trạng thái | Đã có | `WORKLOG.md` |
| Evaluation evidence có test, datasets, metrics, reports | Đã có | `docs/EVALUATION_EVIDENCE.md`, `evals/reports/` |
| AI logs/hook config | Đã có | Cần chạy setup hook trước push |
| Video demo | Cần tạo | 3-5 phút |
| Pitch deck | Có nội dung nguồn, cần xuất slide | 5-10 trang |
| Public access cho Drive/YouTube/Slide | Cần kiểm tra | Bắt buộc trước submit |

## Kết luận

Serene hiện có đầy đủ các lớp cần thiết cho một bài nộp AI20K Build Phase nghiêm túc: sản phẩm frontend, backend agentic runtime, database migrations, safety-first architecture, evaluation suite, AI security evidence, worklog/journal và tài liệu architecture. Điểm cần hoàn thiện cuối cùng không phải logic code chính, mà là hygiene nộp bài: cập nhật link công khai, chạy hook logging, push bản mới nhất và ghi rõ ranh giới giữa kết quả offline heuristic với kết quả live demo.
