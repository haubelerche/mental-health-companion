# Serene - Checklist cuối trước khi nộp bài

## Context

Checklist này chuyển yêu cầu trong `HUONGDANNOPBAI_full.md` thành các bước kiểm tra operational trước khi bấm submit. Mục tiêu là giảm lỗi do thiếu link công khai, thiếu hook logging, tài liệu chưa đồng bộ hoặc repository còn file local không nên commit.

## Problem Statement Technical Deep-Dive

Ở giai đoạn nộp bài, rủi ro lớn nhất là coordination risk: mã nguồn và tài liệu có thể đã đủ, nhưng form lại thiếu Live URL, video bị khóa quyền xem, pitch deck chưa public hoặc README vẫn còn placeholder. Vì deadline đóng vào 23:59 ngày 17/05/2026, checklist cần ưu tiên các hạng mục có khả năng gây mất điểm trực tiếp.

## Technical Deep-Dive

### A. GitHub Repository

| Kiểm tra | Trạng thái | Ghi chú |
|---|---|---|
| Source code frontend/backend đầy đủ | Cần xác nhận trước commit cuối | `frontend/`, `backend/` |
| Database migrations đầy đủ | Cần xác nhận trước commit cuối | `backend/alembic/versions/` |
| AI/agent logic đầy đủ | Cần xác nhận trước commit cuối | `backend/app/services/`, `backend/app/safety/`, `backend/app/analyst/` |
| API đầy đủ | Cần xác nhận trước commit cuối | `backend/app/api/v1/routers/` |
| README ở thư mục gốc | Đã có | Cần cập nhật link |
| Architecture document | Đã có | `docs/ARCHITECTURE.md` |
| Evaluation evidence | Đã có | `docs/EVALUATION_EVIDENCE.md` |
| Journal | Đã có | `JOURNAL.md` |
| Worklog | Đã có | `WORKLOG.md` |
| AI logs hook config | Đã có | Cần chạy setup hook trước push |

### B. Form nộp bài

| Kiểm tra | Trạng thái | Hành động |
|---|---|---|
| Live URL public | Cần cập nhật | Mở bằng cửa sổ ẩn danh |
| Video demo 3-5 phút | Cần tạo/cập nhật | Theo `docs/DEMO_SCRIPT.md` |
| Pitch deck 5-10 trang | Cần xuất slide | Dựa trên `README_SLIDE_DECK.md` |
| Link Drive/YouTube/Slide public | Cần kiểm tra | Anyone with the link can view |
| Link GitHub đúng repository | Cần kiểm tra | Không dùng nhầm worktree hoặc fork private không cấp quyền |

### C. Kiểm tra kỹ thuật tối thiểu

| Lệnh | Mục tiêu |
|---|---|
| `git status --short` | Xem file thay đổi, tránh commit file local hoặc artifact |
| `bash scripts/setup_hooks.sh` | Cài hook logging trước push hoặc PR |
| `pytest backend/tests -q` | Chạy regression backend nếu còn thời gian |
| `npm --prefix frontend run build` | Xác minh frontend build nếu còn thời gian |
| `python evals/run_golden.py` | Xác minh golden routing nếu còn thời gian |

### D. File không nên commit

| Pattern | Lý do |
|---|---|
| `.ai-log/*.jsonl` | Log local, tự submit qua hook |
| `.env` | Chứa secret |
| `serene_local.db` | Database local |
| `backend/_alembic_test.db` | Database test local |
| `.pytest_cache/`, `.pytest_tmp/` | Artifact test |
| `node_modules/` | Dependency local |

## Strategic Recommendations

| Thứ tự | Hành động cuối | Kết quả mong muốn |
|---:|---|---|
| 1 | Cập nhật Live URL, Video Demo, Pitch Deck trong `README.md` và `docs/FORM_SUBMISSION_PREP.md` | Link thống nhất trên mọi tài liệu |
| 2 | Kiểm tra public access của toàn bộ link bằng cửa sổ ẩn danh | Không có lỗi quyền truy cập khi người chấm mở |
| 3 | Chạy `bash scripts/setup_hooks.sh` | Đáp ứng yêu cầu AI prompt logging |
| 4 | Chạy test/eval tối thiểu theo thời gian còn lại | Giảm rủi ro regression cuối |
| 5 | Kiểm tra `git status --short` | Không commit file local hoặc secret |
| 6 | Push bản mới nhất lên GitHub | Repository phản ánh đúng bài nộp |
| 7 | Điền form và kiểm tra lại toàn bộ link | Hoàn tất nộp trước 23:59 ngày 17/05/2026 |
