# API Spec (v1.0)

**Thông tin dự án:** Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
**Stack:** React.js + FastAPI + LangGraph + PostgreSQL + Redis + pgvector + Neo4j (Celery/outbox theo `BACKEND_PLAN.md`)

---

## Meta

**Base URL:** `$BASE_URL/v1` — giá trị cụ thể theo môi trường:
- Local dev: `http://localhost:8000/v1`
- Railway deploy: `https://<service-name>.railway.app/v1`

**Auth:** JWT Bearer token được đọc tự động từ `httpOnly` cookie (trình duyệt gửi kèm mọi same-origin request). Không dùng `Authorization: Bearer` header vì client-side JS không thể đọc httpOnly cookie.

**Token Storage:** Token **phải** được set qua `Set-Cookie` header với flags `HttpOnly; Secure; SameSite=Strict`. Không bao giờ trả token trong response body — JS không được phép đọc token (chống XSS).

**JWT Algorithm:** Bắt buộc dùng `RS256` (asymmetric). Middleware **phải từ chối** mọi JWT có `"alg": "none"` hoặc thuật toán đối xứng yếu (HS256 với secret ngắn). Algorithm phải được pin cứng trong config, không đọc từ JWT header.

**CSRF Protection:** Khi dùng cookie-based auth, mọi request thay đổi state (`POST`, `PATCH`, `DELETE`) phải kèm header `X-CSRF-Token`. Backend phát CSRF token qua `/auth/csrf-token` và validate ở middleware.

**Content-Type:** `application/json`

---

## Quy ước chung

**Tất cả response đều theo cấu trúc:**
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

**Khi có lỗi:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "STRING_CODE",
    "message": "mô tả lỗi"
  }
}
```

- Timestamp: ISO 8601 UTC.
- `user_id` trong mọi response luôn là hashed ID — không bao giờ là email hoặc tên thật.
- Endpoint không ghi rõ auth = yêu cầu JWT hợp lệ (mặc định).

---

## 1. Auth

### `POST /auth/signup`
Đăng ký tài khoản. Bắt buộc user tick disclaimer. Flow mới: tạo account chưa active và gửi email xác nhận.

```json
// Request
{
  "display_name": "Minh Anh",
  "email": "user@example.com",
  "password": "Password123!",
  "disclaimer_accepted": true
}

// Response 202
{
  "success": true,
  "data": {
    "user_id": "usr_xxx",
    "verification_required": true,
    "message": "Vui lòng kiểm tra email để xác nhận tài khoản"
  },
  "error": null
}
```

> Signup không set access_token/refresh_token.

**Error chính:**
- `DISCLAIMER_NOT_ACCEPTED` (400)
- `INVALID_PARAMETER` (400, email tồn tại)
- `RATE_LIMIT_AUTH` (429)

---

### `POST /auth/login`
```json
// Request
{
  "email": "user@example.com",
  "password": "Password123!"
}

// Response 200
{
  "success": true,
  "data": {
    "user_id": "usr_xxx",
    "expires_in": 3600
  },
  "error": null
}
// Header: Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Strict; Max-Age=3600
// Header: Set-Cookie: refresh_token=<rt>; HttpOnly; Secure; SameSite=Strict; Path=/v1/auth/refresh
```

**Error chính:**
- `AUTH_INVALID_TOKEN` (401) cho sai email/mật khẩu
- `AUTH_EMAIL_NOT_VERIFIED` (403) nếu đúng mật khẩu nhưng chưa xác nhận email
- `RATE_LIMIT_AUTH` (429)
- `AUTH_TOO_MANY_ATTEMPTS` (429)

---

### `GET /auth/verify-email?token=...`
Xác nhận email bằng one-time token. Khi thành công backend sẽ active user, set cookie auth và redirect về `FRONTEND_HOME_URL`.

- Response thành công: HTTP 302 redirect
- Set-Cookie: access_token, refresh_token, csrf_token

**Error chính:**
- `AUTH_VERIFY_TOKEN_INVALID` (400)
- `AUTH_VERIFY_TOKEN_EXPIRED` (400)

---

### `POST /auth/resend-verification`
Gửi lại email xác nhận cho account chưa active.

```json
// Request
{
  "email": "user@example.com"
}

// Response 200 (luôn message trung tính)
{
  "success": true,
  "data": {
    "resent": true,
    "message": "Nếu email tồn tại, chúng tôi đã gửi lại email xác nhận"
  },
  "error": null
}
```

> Có cooldown theo `AUTH_EMAIL_RESEND_COOLDOWN_SECONDS`.

---

### `POST /auth/forgot-password`
Tạo yêu cầu quên mật khẩu, gửi email reset link.

```json
// Request
{
  "email": "user@example.com"
}

// Response 200 (không tiết lộ email có tồn tại hay không)
{
  "success": true,
  "data": {
    "sent": true,
    "message": "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn đặt lại mật khẩu"
  },
  "error": null
}
```

---

### `POST /auth/reset-password`
Đặt mật khẩu mới bằng token từ email reset.

```json
// Request
{
  "token": "<one_time_reset_token>",
  "new_password": "NewPassword123!"
}

// Response 200
{
  "success": true,
  "data": {
    "reset": true,
    "message": "Đặt lại mật khẩu thành công"
  },
  "error": null
}
```

**Error chính:**
- `AUTH_RESET_TOKEN_INVALID` (400)
- `AUTH_RESET_TOKEN_USED` (400)
- `AUTH_RESET_TOKEN_EXPIRED` (400)

---

### `POST /auth/refresh`
Làm mới access token. Không có request body, đọc refresh token từ cookie.

```
// Request: không có body
// Header: X-CSRF-Token: <csrf_token>
// Cookie: refresh_token=<rt>

// Response 200
{
  "success": true,
  "data": { "expires_in": 3600 },
  "error": null
}
```

**Error chính:**
- `AUTH_REFRESH_MALFORMED` (401)
- `AUTH_REFRESH_REVOKED` (401)
- `AUTH_REFRESH_EXPIRED` (401)

---

### `POST /auth/logout`
Thu hồi refresh token và xóa cookie auth.

```
// Request: không có body
// Header: X-CSRF-Token: <csrf_token>
// Cookie: refresh_token=<rt>

// Response 200
{
  "success": true,
  "data": { "logged_out_at": "2026-04-12T08:00:00Z" },
  "error": null
}
```

---

## 2. Chat (Core)

### `POST /chat/message`
Gửi 1 tin nhắn, nhận phản hồi agent. Path triển khai theo blueprint: **`POST /v1/chat/message`** (document này bỏ tiền tố `/v1` trong heading cho gọn; mọi path dưới đây hiểu là dưới `$BASE_URL/v1`).

Endpoint chạy LangGraph: Middleware → Supervisor → Analyst (nếu cần) → Friend → Output Guardrails; nhánh crisis → **SOS Handler (rule-based)** theo `SEQUENCE_DIAGRAMS` Diagram 4 và `BACKEND_PLAN.md` §6.3 / §7.

```json
// Request
{
  "message": "Dạo này áp lực quá, không ngủ được...",
  "session_id": "sess_xyz"
}
// session_id optional — nếu null hệ thống tự tạo phiên mới
```

> **Validation:** `message` tối đa **2,000 ký tự**. Vượt → `PAYLOAD_TOO_LARGE` (422). `session_id` nếu được cung cấp, backend **phải xác minh** thuộc `user_id` trong JWT — trả `SESSION_NOT_FOUND` (404) nếu không khớp (không dùng 403 để tránh enumeration).

**Response bình thường (`sos_triggered = false`):**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "conversation_mode": "normal",
    "distress_score": 0.18,
    "safety_tier": "normal",
    "voice_session_offered": false,
    "suggest_voice": false,
    "emergency_actions": null,
    "reply": "Nghe có vẻ bạn đang gồng gánh nhiều thứ một lúc. Áp lực đến mức không ngủ được thì mệt lắm rồi...",
    "tone_cam_xuc": "xac_nhan",
    "goi_y_nhanh": [
      "Kể thêm đi",
      "Mình nên làm gì bây giờ?",
      "Chỉ cần lắng nghe thôi"
    ],
    "the_dinh_kem": [
      {
        "type": "breathing_exercise",
        "id": "breath_478",
        "title": "Thở 4-7-8 — Giảm căng thẳng ngay"
      }
    ],
    "sos_triggered": false
  },
  "error": null
}
```

**Ví dụ khi có dấu hiệu (chưa SOS)** — `safety_tier: "elevated"`, vẫn `sos_triggered: false`, đổi tone / `conversation_mode` (tuỳ policy):

```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "conversation_mode": "supportive",
    "distress_score": 0.52,
    "safety_tier": "elevated",
    "voice_session_offered": false,
    "suggest_voice": false,
    "emergency_actions": null,
    "reply": "…",
    "sos_triggered": false
  },
  "error": null
}
```

**Ví dụ bậc gợi thoại (≥ 0.8)** — `safety_tier: "voice_recommended"` (`BACKEND_PLAN.md` §7.9):

```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "conversation_mode": "supportive",
    "distress_score": 0.84,
    "safety_tier": "voice_recommended",
    "voice_session_offered": true,
    "suggest_voice": true,
    "voice_hint": "Bạn có thể bấm gọi để nói chuyện trực tiếp với Mây / tổng đài — mình vẫn ở đây trong lúc bạn cân nhắc.",
    "emergency_actions": null,
    "reply": "…",
    "sos_triggered": false
  },
  "error": null
}
```

**Response khi SOS / crisis kích hoạt (`sos_triggered = true`)** — **khớp `BACKEND_PLAN.md` §7.2** (de-escalation, dual-focus, không chỉ một hotline đơn); **thang điểm / bậc an toàn** — **§7.9**:

```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "sos_triggered": true,
    "conversation_mode": "de_escalation",
    "distress_score": 0.94,
    "safety_tier": "critical",
    "voice_session_offered": true,
    "suggest_voice": true,
    "emergency_actions": {
      "outbound_call_to_user_queued": true,
      "trusted_contact_notification_queued": true,
      "user_alert_sent": true
    },
    "risk_level": 5,
    "agent_display_name": "Mây",
    "reply": null,
    "assistant_text": "Mình đang ở đây với bạn. Mình muốn giúp bạn an toàn ngay lúc này — nếu được, mình muốn bạn thử một việc nhỏ cùng mình trong lúc bạn cân nhắc thêm bước tiếp theo.",
    "assistant_strategy": {
      "keep_engaged": true,
      "encourage_external_help": true,
      "avoid_hard_stop": true
    },
    "micro_actions": [
      {
        "type": "grounding",
        "label": "Nhìn quanh và kể tên 5 thứ bạn thấy"
      },
      {
        "type": "breathing",
        "label": "Hít vào 4 giây, giữ 4 giây, thở ra 6 giây"
      }
    ],
    "hotline_cards": [
      {"label": "Cấp cứu trầm cảm — BV Tâm thần TP.HCM (24/7)", "phone": "1900 1267"},
      {"label": "Dự án Ngày Mai — 13h–20h30 (Thứ 4, 6, 7, CN)", "phone": "096 306 1414"},
      {"label": "Cấp cứu y tế khẩn cấp", "phone": "115"}
    ],
    "grounding_actions": [
      {"id": "grounding_54321"},
      {"id": "breath_478"}
    ],
    "referral_options": [
      {"type": "counselor"},
      {"type": "trusted_contact"}
    ],
    "followup_priority": true
  },
  "error": null
}
```

**Safety ladder — field trong `data` (§7.9, mọi response `POST /chat/message`):**

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `distress_score` | `number` | Điểm nghiêm trọng tình huống **0.0–1.0** (từ khóa + classifier theo policy). Luôn có khi backend đã bật scoring. |
| `safety_tier` | `string` | Bậc điều phối UI / agent: `"normal"` (A), `"elevated"` (B), `"voice_recommended"` (C — gợi thoại, thường `distress_score >= 0.8`), `"critical"` (D — khẩn, thường `> 0.9` + gói SOS). |
| `voice_session_offered` | `boolean` | Backend gợi hiển thị CTA **gọi thoại / WebRTC / nhận cuộc gọi lại** (bậc C trở lên hoặc policy). |
| `suggest_voice` | `boolean` | Trùng ý với `voice_session_offered` (có thể luôn bằng nhau); giữ để tương thích client cũ / A-B test label. |
| `voice_hint` | `string \| null` | Một dòng copy gợi ý thoại (tuỳ chọn); không thay `assistant_text` khi SOS. |
| `emergency_actions` | `object \| null` | Chỉ bậc **critical** / khi job nền được enqueue: `outbound_call_to_user_queued`, `trusted_contact_notification_queued`, `user_alert_sent` (tin hotline/khẩn tới user). Giá trị `false` nếu user chưa consent hoặc chưa tích hợp — **không** coi `true` là đã gọi xong; chỉ “đã xếp hàng / đã kích hoạt luồng”. |
| `conversation_mode` | `string` | Mở rộng: `"normal"` \| `"supportive"` (khuyên nhủ, chưa SOS) \| `"de_escalation"` |
| `intervention` | `object \| null` | Can thiệp chủ động ngoài reply chính. MVP hiện có `type = "proactive_voice"` khi safety layer kích hoạt voice async. |

**`intervention.proactive_voice` (MVP async):**

```json
{
  "type": "proactive_voice",
  "trigger_reason": "threshold_crossed",
  "trigger_snapshot": {
    "distress_score": 0.92,
    "risk_level": 5,
    "safety_tier": "critical",
    "rolling_window_turns": 4,
    "delta_score": 0.31
  },
  "cooldown": { "active": false, "seconds_remaining": 0 },
  "voice": {
    "provider": "blaze",
    "tts_job_id": "tts_123",
    "audio_url": null,
    "status": "queued",
    "model_id": "blaze-tts-1"
  },
  "voice_script": "Mình đang ở đây với cậu...",
  "copy_ngan": "Mình gửi cậu một lời nhắn thoại ngắn để đồng hành ngay lúc này.",
  "crisis_footer": {
    "show_once": true,
    "text": "Nếu cậu đang có ý định tự hại ngay lúc này, hãy bấm để kết nối hỗ trợ khẩn cấp.",
    "hotline_cta": {"label": "Gọi hỗ trợ khẩn cấp", "action": "open_hotline_sheet"}
  },
  "next_actions": [
    {"id": "continue_voice", "label": "Nói chuyện tiếp", "action": "open_voice_session_placeholder"}
  ]
}
```

**Quan hệ với `risk_level` (0–5):** backend map thống nhất `distress_score` ↔ `risk_level` (bảng nội bộ); cả hai có thể xuất hiện. Khi `sos_triggered === true`, ưu tiên payload §7.2 + `safety_tier === "critical"` nếu vượt ngưỡng D.

- **`assistant_text`**: nội dung chính khi crisis (thay thế `reply`); có thể do template rule-based hoặc copy đã kiểm soát — tránh từ chối cứng kiểu “không thể giúp” (`BACKEND_PLAN.md` §7.5–§7.7).
- **`micro_actions`**: nhãn hiển thị cho user (grounding/thở); **`grounding_actions`**: id tham chiếu catalog / deep-link / analytics — có thể map 1–1 ở service.
- Response bình thường có thể thêm `conversation_mode: "normal"` (optional) để FE thống nhất component.

**Lưu ý cho FE:**
- Theo **`safety_tier`**: `normal` → UI chat thường; `elevated` → tone hỗ trợ / khuyên nhủ; `voice_recommended` → hiển thị CTA thoại nếu `voice_session_offered`; `critical` → §7.2 + `emergency_actions` (và không giả định mọi cờ đều `true` nếu chưa consent).
- Kiểm tra `sos_triggered` **trước** khi render `reply` như chat thường; khi `true`, ưu tiên **`assistant_text`** + block crisis (hotline, `micro_actions`, `referral_options`).
- Khi `assistant_strategy.avoid_hard_stop === true` (mặc định crisis): **không** coi “fullscreen duy nhất + ẩn input vĩnh viễn” là bắt buộc — ưu tiên **dual-focus**: vừa hiển thị nội dung an toàn, vừa luôn có hotline + hành động nhỏ (`BACKEND_PLAN.md` §7.6). Có thể hạn chế input (ví dụ chỉ quick-replies an toàn) thay vì khóa hoàn toàn, trừ policy sản phẩm bắt buộc khác.
- `tone_cam_xuc` (khi không SOS): `"ho_tro"`, `"xac_nhan"`, `"vui_tuoi"`, `"lam_diu"`.

**Rate limit:** 30 messages/phút/user. Vượt → lỗi `RATE_LIMIT_EXCEEDED`.

---

### `GET /chat/sessions`
Danh sách các phiên chat của user, sắp xếp mới nhất trước.

```json
// Response 200
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "sess_xyz",
        "last_message_at": "2026-04-12T14:30:00Z",
        "preview": "Dạo này áp lực quá, không ngủ được..."
      },
      {
        "session_id": "sess_abc",
        "last_message_at": "2026-04-10T09:00:00Z",
        "preview": "Mình vừa thi xong, nhẹ hơn rồi..."
      }
    ]
  },
  "error": null
}
```

---

### `GET /chat/voice-jobs/{tts_job_id}`
Lấy trạng thái job TTS async cho proactive voice.

```json
{
  "success": true,
  "data": {
    "tts_job_id": "tts_123",
    "status": "queued",
    "audio_url": null,
    "trigger_reason": "threshold_crossed"
  },
  "error": null
}
```

### `GET /chat/voice-jobs/{tts_job_id}/events`
SSE stream trạng thái voice job (`queued` → `processing` → `ready|failed`).

- `Content-Type: text/event-stream`
- Event name: `status`
- Data: JSON payload cùng shape như `GET /chat/voice-jobs/{tts_job_id}`.

### `GET /chat/voice-jobs/{tts_job_id}/audio`
Trả file mp3 khi job đã `ready`. Nếu chưa sẵn sàng trả lỗi `VOICE_AUDIO_NOT_READY` (404).

---

### `GET /chat/sessions/{session_id}/messages?limit=20&offset=0`
Lấy lịch sử tin nhắn của 1 phiên. Sắp xếp cũ → mới.

> **Authorization:** Backend phải xác minh `session_id` thuộc `user_id` trong JWT trước khi trả dữ liệu. Nếu sai owner → trả `SESSION_NOT_FOUND` (404, không dùng 403 để tránh enumeration). `limit` tối đa 100, `offset` vượt `total` → trả list rỗng, không lỗi.

```json
// Response 200
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "messages": [
      {
        "message_id": "msg_001",
        "role": "user",
        "content": "Dạo này áp lực quá, không ngủ được...",
        "created_at": "2026-04-12T14:28:00Z"
      },
      {
        "message_id": "msg_002",
        "role": "assistant",
        "content": "Nghe có vẻ bạn đang gồng gánh nhiều thứ một lúc...",
        "tone_cam_xuc": "xac_nhan",
        "the_dinh_kem": [],
        "created_at": "2026-04-12T14:28:03Z"
      }
    ],
    "total": 12,
    "has_more": false
  },
  "error": null
}
```

---

### `DELETE /chat/sessions/{session_id}`
Xóa phiên chat. Mặc định là soft delete — nội dung ẩn với user, hệ thống giữ **summary ẩn danh** (không PII) cho analytics trong **90 ngày**, sau đó tự động xóa vĩnh viễn.

```json
// Response 200
{
  "success": true,
  "data": { "deleted_at": "2026-04-12T15:00:00Z", "hard_delete_at": "2026-07-11T15:00:00Z" },
  "error": null
}
```

> **GDPR / PDPA Right to Erasure:** User có quyền yêu cầu xóa vĩnh viễn ngay lập tức qua `DELETE /chat/sessions/{session_id}?hard=true`. Hard delete xóa cả summary, không giữ lại gì. Chính sách lưu trữ phải được hiển thị rõ trong phần Privacy Policy khi signup.

**Summary được giữ lại chỉ bao gồm:** thống kê ẩn danh (số turn, tone cảm xúc tổng quát) — không bao gồm nội dung hội thoại, tên, hay bất kỳ thông tin có thể định danh.

---

## 3. Home

### `POST /mood/checkin`
Ghi nhận mood hằng ngày. Không gọi LLM — ghi thẳng vào `lich_su_tam_trang`.

```json
// Request
{
  "mood": "stressed",
  "emoji": "😮‍💨",
  "note": "Deadline đồ án dồn cùng lúc"
}

// Response 201
{
  "success": true,
  "data": {
    "checkin_id": "mc_789",
    "logged_at": "2026-04-12T08:30:00Z"
  },
  "error": null
}
```

> Mỗi ngày chỉ cho phép 1 lần checkin. "Ngày" được tính theo **UTC+7 (Asia/Ho_Chi_Minh)**. Nếu đã có → trả lỗi `MOOD_ALREADY_LOGGED` (409). FE hiện nút "Cập nhật" dùng `PATCH /mood/checkin/{checkin_id}` thay thế.

---

### `PATCH /mood/checkin/{checkin_id}`
Cập nhật mood checkin trong ngày (nếu user muốn sửa).

```json
// Request
{ "mood": "okay", "emoji": "😐", "note": null }

// Response 200
{
  "success": true,
  "data": { "updated_at": "2026-04-12T10:00:00Z" },
  "error": null
}
```

> **Authorization:** Backend phải xác minh `checkin_id` thuộc `user_id` trong JWT — không được chỉ lookup bằng ID mà không check ownership (chống cross-user modification). Nếu sai owner → trả `CHECKIN_NOT_FOUND` (404, không dùng 403 để tránh enumeration).
> **Giới hạn thời gian:** Chỉ cho phép PATCH checkin của **ngày hôm nay** (UTC+7). Checkin của ngày trước → trả lỗi `CHECKIN_NOT_EDITABLE` (409).

---

### `GET /home/feed`
Lấy toàn bộ dữ liệu hiển thị màn hình Home. Gọi 1 lần khi mở app.

```json
// Response 200
{
  "success": true,
  "data": {
    "quote_of_day": {
      "text": "Bạn không cần phải hoàn hảo để xứng đáng được yêu thương.",
      "author": "Brené Brown"
    },
    "suggested_meditation": {
      "id": "med_01",
      "title": "Bắt đầu tập trung",
      "duration_sec": 300,
      "thumbnail": "https://cdn.example.com/thumb/med_01.jpg"
    },
    "last_session": {
      "session_id": "sess_xyz",
      "preview": "Dạo này áp lực quá...",
      "last_message_at": "2026-04-12T14:30:00Z"
    },
    "dynamic_suggestion": {
      "type": "sleep",
      "reason": "late_night",
      "message": "Đã khuya rồi, thử bài thở ngủ ngon nhé?"
    },
    "mood_today": {
      "checked_in": true,
      "mood": "stressed",
      "emoji": "😮‍💨"
    }
  },
  "error": null
}
```

> `last_session` = `null` nếu user chưa có phiên chat nào. `mood_today.checked_in = false` nếu chưa checkin hôm nay → FE hiện mood picker.

---

## 4. Reflect

### `GET /reflect/mood-trend?days=7`
Biểu đồ xu hướng mood. Không trả điểm PHQ-9/GAD-7 thô ra FE.

> **Validation:** `days` phải trong khoảng **1–90**. Giá trị ngoài khoảng → `INVALID_PARAMETER` (400). Default: 7.

```json
// Response 200
{
  "success": true,
  "data": {
    "period": { "from": "2026-04-06", "to": "2026-04-12" },
    "points": [
      { "date": "2026-04-06", "mood_score": 3, "label": "ổn", "emoji": "🙂" },
      { "date": "2026-04-07", "mood_score": 2, "label": "hơi mệt", "emoji": "😔" },
      { "date": "2026-04-08", "mood_score": 1, "label": "khó khăn", "emoji": "😞" },
      { "date": "2026-04-09", "mood_score": 3, "label": "ổn", "emoji": "🙂" },
      { "date": "2026-04-12", "mood_score": 4, "label": "tốt", "emoji": "😊" }
    ],
    "days_missing": ["2026-04-10", "2026-04-11"],
    "summary": "Tuần này bạn có xu hướng tốt hơn so với tuần trước"
  },
  "error": null
}
```

> `days_missing` = các ngày không có mood checkin. FE có thể render chấm rỗng.

---

### `GET /reflect/weekly-note`
Lời nhắn tổng kết tuần (batch job: Analyst tổng hợp → Friend rewrite, chạy mỗi Chủ nhật 23:00).

```json
// Response 200
{
  "success": true,
  "data": {
    "week_of": "2026-04-06",
    "content": "Tuần này bạn đã vượt qua được kha khá áp lực. Mình thấy bạn hay nhắc đến deadline và giấc ngủ — hai thứ đó có liên quan đến nhau đó...",
    "generated_at": "2026-04-12T23:05:00Z"
  },
  "error": null
}
```

> Nếu tuần hiện tại chưa đến Chủ nhật hoặc batch chưa chạy → trả `data: null`, FE hiện placeholder "Lời nhắn sẽ xuất hiện cuối tuần".

---

### `POST /reflect/journal`
Lưu bài viết nhật ký.

```json
// Request
{
  "content": "Hôm nay mình thấy mọi thứ đang dần ổn hơn...",
  "prompt_id": "prompt_03"
}
// prompt_id optional — null nếu user tự viết không dùng gợi ý
// content: tối đa 10,000 ký tự. Vượt → PAYLOAD_TOO_LARGE (422)

// Response 201
{
  "success": true,
  "data": {
    "journal_id": "j_123",
    "created_at": "2026-04-12T22:00:00Z"
  },
  "error": null
}
```

---

### `GET /reflect/journals?limit=20&offset=0`
Danh sách bài journal, mới nhất trước.

```json
// Response 200
{
  "success": true,
  "data": {
    "journals": [
      {
        "journal_id": "j_123",
        "content_preview": "Hôm nay mình thấy mọi thứ đang dần...",
        "prompt_id": "prompt_03",
        "created_at": "2026-04-12T22:00:00Z"
      }
    ],
    "total": 8,
    "has_more": false
  },
  "error": null
}
```

---

### `GET /reflect/journal-prompts`
Lấy danh sách gợi ý prompt viết journal từ Knowledge Base.

```json
// Response 200
{
  "success": true,
  "data": {
    "prompts": [
      { "id": "prompt_01", "text": "Hôm nay điều gì khiến bạn cảm thấy tự hào về bản thân?" },
      { "id": "prompt_02", "text": "Điều gì đang chiếm nhiều năng lượng nhất của bạn tuần này?" },
      { "id": "prompt_03", "text": "Nếu nói chuyện với bản thân 1 năm trước, bạn sẽ nói gì?" }
    ]
  },
  "error": null
}
```

---

## 5. Resources

### `GET /resources/categories`
```json
// Response 200
{
  "success": true,
  "data": {
    "categories": [
      { "id": "meditate", "label": "Thiền định", "icon": "🧘" },
      { "id": "sleep", "label": "Ngủ ngon", "icon": "🌙" },
      { "id": "music", "label": "Âm nhạc", "icon": "🎵" },
      { "id": "work_study", "label": "Tập trung học", "icon": "📚" },
      { "id": "wisdom", "label": "Kiến thức tâm lý", "icon": "💡" },
      { "id": "movement", "label": "Vận động nhẹ", "icon": "🏃" }
    ]
  },
  "error": null
}
```

---

### `GET /resources?category=meditate&limit=20&offset=0`
Danh sách nội dung theo category. `category` phải là một trong các giá trị từ `GET /resources/categories`. Giá trị không hợp lệ → `INVALID_PARAMETER` (400).

```json
// Response 200
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "med_042",
        "category": "meditate",
        "title": "Thiền cho người lo âu",
        "duration_sec": 600,
        "format": "audio",
        "url": "https://cdn.example.com/audio/med_042.mp3?X-Amz-Expires=3600&X-Amz-Signature=...",
        "url_expires_at": "2026-04-12T16:30:00Z",
        "thumbnail": "https://cdn.example.com/thumb/med_042.jpg",
        "bookmarked": false
      }
    ],
    "total": 24,
    "has_more": true
  },
  "error": null
}
```

> **Pre-signed URLs:** `url` là presigned URL có thời hạn 1 giờ (`url_expires_at`). FE phải re-fetch khi URL hết hạn. Không hardcode URL — URL thay đổi mỗi lần gọi API để chống enumeration và unauthorized direct access.

---

### `GET /resources/{id}`
Chi tiết 1 nội dung. Trả presigned URL mới (TTL 1 giờ).

```json
// Response 200
{
  "success": true,
  "data": {
    "id": "med_042",
    "category": "meditate",
    "title": "Thiền cho người lo âu",
    "description": "Bài thiền 10 phút giúp bình tĩnh khi lo âu leo thang...",
    "duration_sec": 600,
    "format": "audio",
    "url": "https://cdn.example.com/audio/med_042.mp3?X-Amz-Expires=3600&X-Amz-Signature=...",
    "url_expires_at": "2026-04-12T16:30:00Z",
    "thumbnail": "https://cdn.example.com/thumb/med_042.jpg",
    "bookmarked": true,
    "tags": ["lo_au", "beginner", "10_phut"]
  },
  "error": null
}
```

---

### `POST /resources/{id}/play-event`
Tracking hành vi tiêu thụ nội dung (phục vụ Analyst batch + gợi ý cá nhân hóa).

```json
// Request
{
  "event": "completed",
  "duration_sec": 598,
  "percent": 99
}
// event: "started" | "paused" | "completed"
// percent: 0–100 (vượt 100 → INVALID_PARAMETER 422)
// duration_sec: không được vượt duration_sec của resource (server validate và clamp nếu lệch nhẹ, reject nếu > 2x)

// Response 200
{
  "success": true,
  "data": { "tracked_at": "2026-04-12T15:30:00Z" },
  "error": null
}
```

---

### `POST /resources/{id}/bookmark`
Bookmark nội dung.
```json
// Response 201
{
  "success": true,
  "data": { "bookmarked_at": "2026-04-12T15:35:00Z" },
  "error": null
}
```

### `DELETE /resources/{id}/bookmark`
Bỏ bookmark.
```json
// Response 200
{
  "success": true,
  "data": { "removed_at": "2026-04-12T15:36:00Z" },
  "error": null
}
```

---

## 6. Connect

### `GET /connect/hotlines`
Danh sách đường dây hỗ trợ tâm lý. Static data, không cần auth.

```json
// Response 200
{
  "success": true,
  "data": {
    "hotlines": [
      {
        "name": "Cấp cứu trầm cảm — Bệnh viện Tâm thần TP.HCM",
        "number": "1900 1267",
        "available": "24/7",
        "note": "Kết nối chuyên gia y tế hỗ trợ trầm cảm hoặc nguy cơ tự sát."
      },
      {
        "name": "Đường dây nóng Ngày Mai",
        "number": "096 306 1414",
        "available": "13:00–20:30 (Thứ 4, 6, 7, Chủ nhật)",
        "note": "Dự án hỗ trợ người trẻ trầm cảm."
      }
    ]
  },
  "error": null
}
```

---

### `POST /connect/clinics`
Danh sách phòng khám/trung tâm tư vấn gần vị trí user. Dùng POST body thay vì query params để tọa độ GPS không bị ghi vào server logs, browser history, hay CDN access logs.

```json
// Request
{
  "lat": 21.03,
  "lng": 105.85,
  "radius_km": 10
}
// lat/lng optional — nếu không truyền → trả danh sách mặc định

// Response 200
{
  "success": true,
  "data": {
    "clinics": [
      {
        "id": "c_01",
        "name": "Trung tâm Tư vấn Tâm lý ABC",
        "address": "12 Nguyễn Trãi, Hà Nội",
        "lat": 21.028,
        "lng": 105.851,
        "phone": "024-1234-5678",
        "hours": "8:00–17:00, Thứ 2–Thứ 6",
        "distance_km": 1.2
      }
    ]
  },
  "error": null
}
```

> **Không log, không lưu** tọa độ GPS vào database. Tọa độ chỉ dùng để tính khoảng cách trong memory, không persist. Endpoint này **phải được loại trừ khỏi request body logging middleware** (standard access log có thể capture POST body).
> **TLS bắt buộc** — endpoint chỉ hoạt động qua HTTPS. Response phải có header `Cache-Control: no-store` để tránh proxy/CDN cache tọa độ.
> **Validation:** `lat` phải trong [-90, 90], `lng` trong [-180, 180], `radius_km` trong [1, 50]. Giá trị ngoài khoảng → `INVALID_PARAMETER` (400).
> Nếu user **không cấp quyền location**: FE gọi POST với body rỗng `{}` — API trả danh sách mặc định (Hà Nội). Không trả lỗi.

---

## 7. Admin / Internal

> Các endpoint này **không expose ra FE user**. Bảo vệ bằng luồng auth riêng biệt — xem chi tiết bên dưới.

#### Admin Auth Flow (tách biệt hoàn toàn khỏi user auth)

1. **Xác thực 2 lớp (MFA bắt buộc):** Admin login qua `POST /admin/auth/login` (endpoint riêng) với `email + password + TOTP code`. Không dùng cùng endpoint với user.
2. **Admin-scoped token ngắn hạn:** Token admin có TTL **15 phút** (không phải 1 giờ), không có refresh token. Hết hạn → phải xác thực lại.
3. **IP Allowlist:** Middleware kiểm tra IP request có nằm trong whitelist cấu hình qua env `ADMIN_ALLOWED_IPS` (định dạng CIDR comma-separated, ví dụ: `"203.0.113.0/24,10.0.0.5/32"`). IP không hợp lệ → 403 ngay cả khi token hợp lệ. **Fail-closed:** Nếu `ADMIN_ALLOWED_IPS` không được set hoặc rỗng → **từ chối toàn bộ** admin access (không fail-open). Triển khai phải có health-check startup để cảnh báo nếu biến này chưa được cấu hình.
4. **Audit log bắt buộc:** Mọi request đến `/admin/*` phải được ghi log với `admin_id`, `action`, `timestamp`, `ip`, `resource_accessed` vào bảng `admin_audit_log` — không thể tắt.
5. **Claim separation:** Token admin có `role: "admin"` và `scope: "admin_only"` — không thể tạo từ user token thông thường, phải issue riêng từ admin auth endpoint.

### `GET /admin/crisis-logs?from=2026-04-01&to=2026-04-12&limit=50&offset=0`
Danh sách sự kiện SOS để admin review. **Có pagination bắt buộc** — không trả toàn bộ log không giới hạn.

```json
// Response 200
{
  "success": true,
  "data": {
    "logs": [
      {
        "log_id": "cl_001",
        "session_id": "sess_xyz",
        "triggered_at": "2026-04-10T02:30:00Z",
        "muc_do": "cao",
        "reviewed": false
      }
    ],
    "total": 3,
    "has_more": false
  },
  "error": null
}
```

> `limit` tối đa 100. Khoảng thời gian `from`→`to` tối đa 90 ngày mỗi request.

### `GET /admin/dashboard/aggregate`
Số liệu ẩn danh cho B2B dashboard (trường học, tổ chức).

```json
// Response 200
{
  "success": true,
  "data": {
    "period": { "from": "2026-04-01", "to": "2026-04-12" },
    "total_sessions": 142,
    "avg_session_depth": 8.3,
    "mood_distribution": {
      "great": 18,
      "okay": 45,
      "stressed": 61,
      "struggling": 18
    },
    "sos_events": 3,
    "top_resource_categories": ["meditate", "sleep"]
  },
  "error": null
}
```

---

## Error Codes

| Code | HTTP | Ý nghĩa |
|---|---|---|
| `AUTH_INVALID_TOKEN` | 401 | JWT hết hạn hoặc sai |
| `AUTH_REFRESH_EXPIRED` | 401 | Refresh token hết hạn, cần login lại |
| `AUTH_TOO_MANY_ATTEMPTS` | 429 | Sai mật khẩu quá 5 lần, khóa 15 phút |
| `CSRF_TOKEN_INVALID` | 403 | CSRF token thiếu hoặc không khớp |
| `DISCLAIMER_NOT_ACCEPTED` | 400 | Signup thiếu tick disclaimer |
| `MOOD_ALREADY_LOGGED` | 409 | Đã checkin mood hôm nay |
| `CHECKIN_NOT_FOUND` | 404 | checkin_id không tồn tại hoặc không thuộc user này |
| `CHECKIN_NOT_EDITABLE` | 409 | Chỉ được sửa checkin của ngày hôm nay |
| `SESSION_NOT_FOUND` | 404 | Sai hoặc không có quyền truy cập session_id |
| `RESOURCE_NOT_FOUND` | 404 | ID nội dung không tồn tại |
| `GUARDRAIL_INPUT_BLOCKED` | 422 | Input bị NeMo chặn (prompt injection, toxic) |
| `LLM_TIMEOUT` | 504 | LangGraph pipeline > 10s — FE nên retry 1 lần |
| `SCHEMA_VALIDATION_FAILED` | 500 | Agent trả sai schema, đã fallback safe reply |
| `RATE_LIMIT_EXCEEDED` | 429 | Vượt 30 msg/phút tại `/chat/message` |
| `RATE_LIMIT_AUTH` | 429 | Vượt 5 lần/phút tại auth endpoints |
| `AUTH_REFRESH_REVOKED` | 401 | Refresh token đã bị thu hồi (đã logout) |
| `AUTH_REFRESH_MALFORMED` | 401 | Refresh token không hợp lệ |
| `ADMIN_FORBIDDEN` | 403 | Token không hợp lệ hoặc IP không trong whitelist |
| `INVALID_PARAMETER` | 400 | Tham số đầu vào ngoài khoảng hợp lệ |
| `PAYLOAD_TOO_LARGE` | 422 | Nội dung vượt giới hạn ký tự |

---

## Ghi chú kỹ thuật

### PII Masking
Xảy ra ở middleware FastAPI **trước khi** request vào LangGraph. FE không cần xử lý. Mọi dữ liệu lưu DB đều đã được mask.

### SOS / crisis (bắt buộc — khớp `BACKEND_PLAN.md` §7)
FE **phải** kiểm tra `sos_triggered` trước khi render `reply` như tin nhắn thường. Khi `sos_triggered = true`:
1. Render **`assistant_text`** và các khối **`hotline_cards`**, **`micro_actions`**, **`grounding_actions`** (nếu có), **`referral_options`** theo `conversation_mode: de_escalation`.
2. Tôn trọng **`assistant_strategy`**: nếu `avoid_hard_stop` — ưu tiên UI **dual-focus** (chat an toàn + hotline + micro-actions), không ép một pattern “chỉ fullscreen / chỉ số điện thoại” (`BACKEND_PLAN.md` §7.5–§7.7).
3. Hiển thị nút gọi hotline / liên hệ hỗ trợ; map `followup_priority` nếu có màn hình follow-up.
4. Đọc **`distress_score`**, **`safety_tier`**, **`voice_session_offered`** / **`voice_hint`**; nếu `emergency_actions` khác `null`, hiển thị trạng thái “đã kích hoạt luồng” (không hiển thị PII người tin cậy) — xem bảng mục **`POST /chat/message`**.

### Proactive voice async (MVP)
- Trigger do safety layer quyết định, không do Friend tự ý bật.
- Job lifecycle:
  - `queued`/`processing`/`ready`/`failed`.
  - FE có thể poll `GET /chat/voice-jobs/{tts_job_id}` hoặc nghe SSE từ `GET /chat/voice-jobs/{tts_job_id}/events`.
  - Khi `ready`, phát từ `GET /chat/voice-jobs/{tts_job_id}/audio`.
- Nếu TTS fail, chat response chính vẫn thành công; FE dùng `voice_script`/`copy_ngan` fallback.

### Trusted contact outbound (legal-dependent)
- Quản lý danh bạ:
  - `GET /safety/trusted-contacts`
  - `POST /safety/trusted-contacts`
  - `POST /safety/trusted-contacts/opt-in`
- Escalation nội bộ:
  - `POST /safety/escalate`
- Outbound thực tế chỉ enqueue khi đồng thời:
  - `trusted_contact_outbound_enabled = true` (config legal gate),
  - user đã opt-in,
  - có trusted contact hợp lệ.

### Streaming (Roadmap)
MVP dùng REST sync. Nếu latency P95 > 5s ở Phase 2, nâng cấp lên endpoint `/chat/stream` (SSE). FE thiết kế component chat có thể swap giữa sync và streaming.

### Rate Limit
- `/chat/message`: 30 req/phút/user
- Tất cả endpoint khác: 100 req/phút/user
- Header response khi gần giới hạn: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Admin Auth
Endpoint `/admin/*` yêu cầu token từ luồng `POST /admin/auth/login` (MFA bắt buộc, TTL 15 phút, không có refresh). Middleware kiểm tra đồng thời: JWT claim `role: "admin" + scope: "admin_only"` và IP request có trong `ADMIN_ALLOWED_IPS`. Thiếu một trong hai → 403. Mọi request được ghi vào `admin_audit_log` không thể tắt.

---

## Đối chiếu `BACKEND_PLAN.md` và `SEQUENCE_DIAGRAMS.md`

Tài liệu mục trên mô tả **MVP API**; backend hiện mount thêm các nhóm dưới tiền tố `/v1` (xem `backend/app/api/v1/api.py`). Bảng sau phản ánh **trạng thái triển khai** (cập nhật theo code), không chỉ nội dung cũ của chính file spec này:

| Chủ đề | `BACKEND_PLAN` / `SEQUENCE_DIAGRAMS` | Code hiện tại (`/v1/...`) | Kết luận |
|---|---|---|---|
| Guest trial | `POST .../guest/session/start`, `heartbeat`, `choice`, `convert` | `POST /guest/session/start`, `POST /guest/session/heartbeat`, `POST /guest/choice`, `POST /guest/convert` | **Có** — `convert` placeholder (401/400 theo policy đăng ký) |
| Safety gate (intake) | `POST .../intake/safety-check` | `POST /intake/safety-check` | **Có** — trả `risk_score`, `risk_level`, `should_route_crisis`, `recommended_next_step` |
| Policy gate | `GET .../policies/current`, `POST .../policies/acknowledge` | `GET /policies/current`, `POST /policies/acknowledge` + dependency `ensure_policy_acknowledged` trên một số route | **Có** — cần mở rộng mục chi tiết trong spec nếu muốn FE-only đọc một chỗ |
| Screening | `GET .../screenings/catalog`, `POST .../screenings/submit` | `GET /screenings/catalog`, `POST /screenings/submit` (PHQ-9 / GAD-7 demo) | **Có** |
| Check-in “An” / mood | `POST .../checkin/quick` và/hoặc mood legacy | `POST /checkin/quick` **và** các route `/mood/*` trong spec (home) | **Song song** — FE chọn contract; nên mô tả rõ trong mục Home/Check-in khi refactor |
| Chat path | `POST .../chat/message` | `POST /chat/message` | **Khớp** (cùng base `/v1`) |
| Crisis / SOS trong chat | §7.2 + ladder §7.9 | Như mục Chat trong spec | **Khớp tinh thần** — kiểm chứng field từng bản build |
| Hotline / referral (REST tách) | `GET .../safety/hotlines`, `.../referrals/options` | `GET /safety/hotlines`, `GET /safety/referrals/options` **và** `GET /connect/hotlines`, `POST /connect/clinics` | **Trùng ý, hai nhóm path** — có thể chuẩn hoá tên sau |
| Dashboard “Gương” | `overview`, `mood-trend`, `history`, `follow-up` | `GET /dashboard/overview`, `/dashboard/mood-trend`, `/dashboard/history`, `/dashboard/follow-up` | **Có** — `follow-up` hiện trả danh sách rỗng (stub) |
| Nội bộ an toàn | `POST .../safety/escalate` (internal) | `POST /safety/escalate` | **Có route** — hiện bị chặn bởi legal gate (`trusted_contact_outbound_enabled`) + user opt-in |
| `user_id` | Plan: `usr_` + hex | DB: `make_id("usr")` → `usr_` + 10 ký tự an toàn | **Khớp code/DB** — ví dụ JSON cũ trong spec nên dần thay bằng `usr_...` |

**Ghi chú nhỏ:** Trong `BACKEND_PLAN` §5.5, câu “Quy trình theo Diagram 1” cho chat nên hiểu là **diagram chat / pipeline message** trong `SEQUENCE_DIAGRAMS` (Diagram 2 — Chat message), không phải Diagram 1 (guest-first).

**Khuyến nghị tiếp:** (1) Bổ sung trong spec các section riêng cho `/guest/*`, `/intake/*`, `/policies/*`, `/screenings/*`, `/checkin/*`, `/dashboard/*`, `/safety/*` (hoặc gộp bảng tóm tắt OpenAPI); (2) quyết định giữ hay deprecate mood path cũ so với `/checkin/quick`; (3) mô tả rõ legal gate và quy trình vận hành cho `POST /safety/escalate` trước khi bật outbound thật.
