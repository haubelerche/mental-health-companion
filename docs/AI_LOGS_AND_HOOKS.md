# Serene - AI logs và hook logging

## Context

Theo guideline của dự án, prompt được logging tự động khi sử dụng các AI coding tools được hỗ trợ. Agent không cần cập nhật `PROMPT_LOG.md` thủ công và không được yêu cầu người dùng log prompt bằng tay. Tài liệu này mô tả cách repository đáp ứng yêu cầu AI logs trong `HUONGDANNOPBAI_full.md` và `AGENTS.md`.

## Problem Statement Technical Deep-Dive

Yêu cầu logging không nhằm tạo thêm thủ tục hành chính, mà nhằm bảo đảm traceability của quá trình phát triển có sử dụng AI. Với một dự án agentic mental-health có safety boundary, traceability giúp reviewer hiểu AI được dùng ở đâu, thay đổi nào do agent đề xuất và hook nào đảm bảo log được nộp tự động khi push.

| Tool | File cấu hình hook | Trạng thái |
|---|---|---|
| Claude Code | `.claude/settings.json` | Đã có |
| Cursor | `.cursor/hooks.json` hoặc `.cursor/settings.json` tùy phiên bản | Đã có cấu hình Cursor trong repository |
| OpenAI Codex | `.codex/hooks.json` | Đã có |
| Gemini CLI | `.gemini/settings.json` nếu dùng | Có trong guideline; kiểm tra nếu team dùng Gemini |
| GitHub Copilot | `.github/hooks/hooks.json` | Đã có |

## Technical Deep-Dive

### Cơ chế hoạt động

```text
AI tool prompt/session
        -> hook config
        -> scripts/log_hook.py
        -> .ai-log/session.jsonl
        -> git pre-push hook
        -> scripts/submit_log.py
        -> AI_LOG_SERVER
```

| Thành phần | Vai trò |
|---|---|
| `scripts/setup_hooks.sh` | Cài hook Git pre-push một lần |
| `scripts/log_hook.py` | Nhận payload từ AI tool hook và ghi JSONL |
| `scripts/submit_log.py` | Gửi log khi push |
| `.ai-log/session.jsonl` | File log local tự sinh, không commit |
| `.env.example` | Chứa biến mẫu `AI_LOG_SERVER` và `AI_LOG_API_KEY` |

### Quy trình bắt buộc trước PR hoặc push

```bash
bash scripts/setup_hooks.sh
```

Sau khi hook được cài, team có thể làm việc bình thường. Khi push, pre-push hook sẽ submit log theo cấu hình. Không cần và không nên tạo PR nếu chưa đảm bảo hook đã được cài.

### Chính sách commit

| Loại file | Có commit không | Lý do |
|---|---|---|
| `.codex/hooks.json` | Có | Cấu hình logging cần review |
| `.claude/settings.json` | Có | Cấu hình logging cần review |
| `.github/hooks/hooks.json` | Có | Cấu hình logging cần review |
| `scripts/log_hook.py` | Có | Logic ghi log cần review |
| `scripts/submit_log.py` | Có | Logic submit log cần review |
| `.ai-log/*.jsonl` | Không | Log local, có thể chứa prompt/session nhạy cảm, đã gitignore |

## Strategic Recommendations

| Rủi ro | Tác động | Kiểm soát |
|---|---|---|
| Quên chạy setup hook | Không đáp ứng yêu cầu trước PR/push | Chạy `bash scripts/setup_hooks.sh` trước push cuối |
| Commit nhầm `.ai-log` | Rò rỉ prompt/session local | Kiểm tra `git status --short` và `.gitignore` |
| Dùng AI tool chưa cấu hình hook | Thiếu traceability | Bổ sung hook config trước khi dùng tool đó cho thay đổi lớn |
| Cấu hình token thật trong repo | Rò rỉ credential | Chỉ commit `.env.example`, không commit `.env` |

## Prompt mẫu minh họa

Các prompt mẫu dưới đây thể hiện loại công việc AI agent được phép hỗ trợ, không thay thế log tự động:

```text
Hãy review luồng SafetyGate và xác định edge case có thể gây false negative trên các câu tiếng Việt mơ hồ.
```

```text
Hãy viết test regression để đảm bảo AnalystBundle không rò rỉ các trường internal ra public chat response.
```

```text
Hãy cập nhật tài liệu kiến trúc để mô tả rõ luồng User -> Frontend -> Backend/API -> Database -> AI Agent/LLM -> External Services.
```
