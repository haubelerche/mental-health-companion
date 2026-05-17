# Serene - Chuẩn bị nội dung Form nộp bài

## Context

Form nộp bài dùng để tổng hợp các link có thể truy cập công khai: Live URL, video demo, pitch deck và tài liệu. Tài liệu này là bản chuẩn bị nội dung để nhóm điền form nhất quán, tránh tình trạng link trong README, slide và form lệch nhau.

## Problem Statement Technical Deep-Dive

Rủi ro lớn nhất của kênh Form không phải thiếu mã nguồn, mà là thiếu khả năng truy cập công khai hoặc điền link không đồng nhất. Vì bài được đánh giá song song qua GitHub và Form, một repository tốt vẫn có thể bị chấm thấp nếu video, slide hoặc Live URL bị khóa quyền xem.

| Trường form | Nội dung cần điền | Trạng thái | Nơi cập nhật đồng bộ |
|---|---|---|---|
| Tên dự án | Serene - AI Mental-Health Companion cho sinh viên Việt Nam | Sẵn sàng | README, slide deck |
| Mã team hoặc repo | A20-App-039 | Sẵn sàng | GitHub repository |
| GitHub Repository | `<thay bằng link GitHub public/private được BTC cấp quyền>` | Cần cập nhật | README, form |
| Live URL | `<thay bằng URL deploy public>` | Cần cập nhật | README, form, slide cuối |
| Video Demo | `<thay bằng link YouTube/Drive public>` | Cần cập nhật | README, form |
| Pitch Deck | `<thay bằng link Google Slides/PDF public>` | Cần cập nhật | README, form |
| Architecture | `docs/ARCHITECTURE.md` | Sẵn sàng | README, form nếu có |
| Evaluation Evidence | `docs/EVALUATION_EVIDENCE.md` | Sẵn sàng | README, form nếu có |
| Journal | `JOURNAL.md` | Sẵn sàng | README, form nếu có |
| Worklog | `WORKLOG.md` | Sẵn sàng | README, form nếu có |
| AI logs/hook evidence | `docs/AI_LOGS_AND_HOOKS.md` | Sẵn sàng | README, form nếu có |

## Technical Deep-Dive

### Nội dung mô tả ngắn cho form

Serene là AI companion hỗ trợ sức khỏe tinh thần bằng tiếng Việt dành cho sinh viên và người trẻ. Sản phẩm cung cấp chat đồng cảm, check-in cảm xúc, screening PHQ-9/GAD-7, dashboard insight, resource hub, memory có kiểm soát và luồng SOS an toàn. Hệ thống dùng SafetyGate trước mọi luồng LLM, tách Analyst nội bộ khỏi phản hồi người dùng, không chẩn đoán và không thay thế chuyên gia.

### Nội dung mô tả kỹ thuật cho form

Serene sử dụng React 19/Vite/Tailwind cho frontend, FastAPI/Python 3.11 cho backend, LangGraph cho orchestration, PostgreSQL/Alembic làm source of truth, Redis/outbox cho tác vụ bất đồng bộ, Neo4j cho derived pattern graph không lưu PII và OpenAI-compatible LLM cho các node hội thoại. Evaluation suite gồm backend tests, golden dataset, adversarial guardrails, LLM-as-Judge heuristic, RAGAS heuristic và AI security checks.

### Nội dung mô tả demo cho form

Video demo dài 3-5 phút, trình bày bài toán hỗ trợ tâm lý ban đầu cho người trẻ Việt Nam, các luồng chính gồm onboarding, chat, check-in, dashboard, resource hub và SOS path. Phần AI Agent Flow giải thích SafetyGate, AnalystNode, FriendNode, SafetyFinalizer và các side effects bất đồng bộ như memory, TTS, dashboard insight.

## Strategic Recommendations

| Việc cần kiểm tra | Tiêu chí đạt |
|---|---|
| Live URL | Mở được ở cửa sổ ẩn danh, không phụ thuộc máy local, không yêu cầu tài khoản nội bộ nếu demo cần public |
| Video demo | Link YouTube/Drive ở chế độ anyone with the link can view, thời lượng 3-5 phút |
| Pitch deck | Link Google Slides/PDF public, 5-10 trang, có problem, solution, technology, results |
| README | Có link quan trọng ở phần đầu, không để placeholder trước khi submit |
| GitHub | Source code mới nhất đã push; không commit `.ai-log/*.jsonl`, DB local hoặc artifact tạm |
| AI log hook | Đã chạy `bash scripts/setup_hooks.sh` trước push/PR |
