# Serene - Chỉ mục gói tài liệu nộp bài

**Mục tiêu:** Gom toàn bộ tài liệu cần nộp theo `HUONGDANNOPBAI_full.md` vào một chỉ mục duy nhất để người chấm có thể kiểm tra nhanh repository, sản phẩm, kiến trúc, nhật ký phát triển và bằng chứng đánh giá.

## Context

BTC yêu cầu dự án được đánh giá song song qua GitHub Repository và Form nộp bài. GitHub dùng để đánh giá kỹ thuật, mã nguồn, kiến trúc và tiến độ phát triển; Form dùng để tổng hợp Live URL, video demo, pitch deck và link tài liệu. Chỉ mục này là bản đồ điều hướng cho cả hai kênh.

| Nhóm tài liệu | File chính | Vai trò khi nộp bài |
|---|---|---|
| Báo cáo tổng hợp | `SUBMISSION_REPORT.md` | Tóm tắt toàn bộ sản phẩm, kiến trúc, evidence và checklist |
| README | `README.md` | Điểm vào chính của repository, cần cập nhật link công khai |
| Kiến trúc | `docs/ARCHITECTURE.md` | Mô tả User, Frontend, Backend/API, Database, AI/LLM và luồng dữ liệu |
| Minh chứng đánh giá | `docs/EVALUATION_EVIDENCE.md` | Test results, eval metrics, guardrail evidence và risk còn lại |
| Nhật ký theo tuần | `JOURNAL.md` | Mục tiêu, kết quả, khó khăn và cách giải quyết theo từng tuần |
| Worklog | `WORKLOG.md` | Phân công, ADR, brainstorming và trạng thái công việc |
| AI logs | `docs/AI_LOGS_AND_HOOKS.md` | Cách hook logging hoạt động và quy định không commit `.ai-log` |
| Chuẩn bị form | `docs/FORM_SUBMISSION_PREP.md` | Danh sách trường cần điền trong form và trạng thái từng link |
| Kịch bản demo | `docs/DEMO_SCRIPT.md` | Kịch bản video demo 3-5 phút |
| Checklist cuối | `docs/FINAL_SUBMISSION_CHECKLIST.md` | Checklist operational trước khi bấm submit |
| Pitch deck source | `README_SLIDE_DECK.md` | Nội dung nguồn để dựng slide 5-10 trang |

## Problem Statement Technical Deep-Dive

Bài nộp không chỉ cần chạy được phần mềm, mà cần chứng minh được ba năng lực: xây dựng sản phẩm có vấn đề rõ ràng, thiết kế kiến trúc AI có guardrail và lưu lại quá trình phát triển đủ minh bạch. Serene đáp ứng cấu trúc đó bằng việc tách bạch repository thành bốn lớp kiểm chứng:

| Lớp kiểm chứng | Nội dung | Bằng chứng |
|---|---|---|
| Product viability | Problem brief, PRD, pitch narrative, demo script | `docs/PRD.md`, `docs/PROBLEM_BRIEF.md`, `README_SLIDE_DECK.md`, `docs/DEMO_SCRIPT.md` |
| Technical architecture | Runtime flow, data flow, database, API, safety invariants | `docs/ARCHITECTURE.md`, `docs/DATABASE_ARCHITECTURE.md`, `docs/API_SPEC.md` |
| Development process | Journal, worklog, ADR, changelog | `JOURNAL.md`, `WORKLOG.md`, `CHANGELOG.md` |
| Evaluation rigor | Unit/integration tests, golden eval, guardrails, RAGAS, AI security | `docs/EVALUATION_EVIDENCE.md`, `evals/`, `backend/tests/` |

## Technical Deep-Dive

### Repository evidence map

```text
A20-App-039/
├── README.md
├── SUBMISSION_REPORT.md
├── JOURNAL.md
├── WORKLOG.md
├── README_SLIDE_DECK.md
├── docs/
│   ├── SUBMISSION_PACKAGE.md
│   ├── ARCHITECTURE.md
│   ├── EVALUATION_EVIDENCE.md
│   ├── AI_LOGS_AND_HOOKS.md
│   ├── FORM_SUBMISSION_PREP.md
│   ├── DEMO_SCRIPT.md
│   └── FINAL_SUBMISSION_CHECKLIST.md
├── backend/
├── frontend/
├── evals/
└── scripts/
```

### Mapping theo yêu cầu BTC

| Yêu cầu trong `HUONGDANNOPBAI_full.md` | Tài liệu hoặc thư mục đáp ứng | Trạng thái |
|---|---|---|
| Source code đầy đủ | `frontend/`, `backend/`, `backend/alembic/`, `evals/`, `scripts/` | Đã có |
| README ở thư mục gốc | `README.md` | Đã có |
| Sơ đồ kiến trúc | `docs/ARCHITECTURE.md` | Đã có |
| Luồng dữ liệu chính | `docs/ARCHITECTURE.md`, `docs/SEQUENCE_DIAGRAMS.md` | Đã có |
| AI logs, prompt mẫu, webhook config | `.codex/hooks.json`, `.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`, `docs/AI_LOGS_AND_HOOKS.md` | Đã có |
| Weekly journal | `JOURNAL.md` | Đã có |
| Worklog | `WORKLOG.md` | Đã có |
| Evaluation evidence | `docs/EVALUATION_EVIDENCE.md`, `eval_report.md`, `evals/reports/` | Đã có |
| Bộ câu hỏi kiểm thử | `evals/datasets/`, `backend/tests/` | Đã có |
| Metrics | `eval_report.md`, `docs/EVALUATION_EVIDENCE.md` | Đã có |
| Video demo | `docs/DEMO_SCRIPT.md` | Cần quay và cập nhật link |
| Pitch deck 5-10 trang | `README_SLIDE_DECK.md` | Cần xuất slide và cập nhật link |
| Live URL | `README.md`, `docs/FORM_SUBMISSION_PREP.md` | Cần cập nhật link deploy |

## Strategic Recommendations

Trước khi nộp, nhóm nên mở `docs/FINAL_SUBMISSION_CHECKLIST.md` và đi từ trên xuống dưới. Cách làm này giảm xác suất thiếu link công khai, quên chạy hook logging hoặc nộp nhầm trạng thái chưa deploy.

| Rủi ro nộp bài | Tác động | Kiểm soát đề xuất |
|---|---|---|
| README còn placeholder link | Người chấm không truy cập được demo hoặc slide | Cập nhật link ở cả `README.md` và `docs/FORM_SUBMISSION_PREP.md` |
| Chưa chạy `scripts/setup_hooks.sh` | Không đáp ứng rule AI prompt logging trước PR/push | Chạy hook trước push cuối |
| Commit file local DB hoặc AI log | Rò rỉ dữ liệu, repo nhiễu | Kiểm tra `git status --short` trước commit |
| Evidence mô tả quá mức | Người chấm hiểu nhầm kết quả heuristic là clinical validation | Ghi rõ kết quả là engineering regression evidence |
| Video demo quá dài hoặc thiếu AI flow | Mất điểm form nộp bài | Theo `docs/DEMO_SCRIPT.md` và giữ trong 3-5 phút |
