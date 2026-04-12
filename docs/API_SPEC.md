# Serene API Spec (v1.0)

**Thông tin dự án:** Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
**Stack:** React.js + FastAPI + LangGraph + PostgreSQL + pgvector
**Ngày:** 2026-04-12

---

## Meta

**Base URL:** `$BASE_URL/v1` — giá trị cụ thể theo môi trường:
- Local dev: `http://localhost:8000/v1`
- Railway deploy: `https://<service-name>.railway.app/v1`

**Auth:** JWT Bearer token trong header `Authorization: Bearer <token>` (trừ endpoint auth).

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
Đăng ký tài khoản. Bắt buộc user tick disclaimer "Serene là AI, không thay thế chuyên gia tâm lý".

```json
// Request
{
  "email": "user@example.com",
  "password": "••••••••",
  "disclaimer_accepted": true
}

// Response 201
{
  "success": true,
  "data": {
    "user_id": "hashed_abc123",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "rt_xyz...",
    "expires_in": 3600
  },
  "error": null
}
```

> Nếu `disclaimer_accepted = false` → trả lỗi `DISCLAIMER_NOT_ACCEPTED` (400).

---

### `POST /auth/login`
```json
// Request
{
  "email": "user@example.com",
  "password": "••••••••"
}

// Response 200
{
  "success": true,
  "data": {
    "user_id": "hashed_abc123",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "rt_xyz...",
    "expires_in": 3600
  },
  "error": null
}
```

---

### `POST /auth/refresh`
Làm mới access token bằng refresh token. Không cần Authorization header.

```json
// Request
{
  "refresh_token": "rt_xyz..."
}

// Response 200
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  },
  "error": null
}
```

---

### `POST /auth/logout`
Thu hồi refresh token hiện tại.

```json
// Request
{
  "refresh_token": "rt_xyz..."
}

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
Gửi 1 tin nhắn, nhận phản hồi từ Serene. Endpoint này chạy toàn bộ LangGraph pipeline:
Middleware → Supervisor → Analyst (nếu cần) → Friend → Output Guardrails.

```json
// Request
{
  "message": "Dạo này áp lực quá, không ngủ được...",
  "session_id": "sess_xyz"
}
// session_id optional — nếu null hệ thống tự tạo phiên mới
```

**Response bình thường (`sos_triggered = false`):**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
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

**Response khi SOS kích hoạt (`sos_triggered = true`):**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_xyz",
    "reply": null,
    "sos_triggered": true,
    "sos_card": {
      "muc_do": "cao",
      "message": "Mình thấy bạn đang trải qua điều rất nặng nề. Bạn không phải một mình — có người sẵn sàng lắng nghe ngay bây giờ.",
      "hotline": {
        "name": "Đường dây hỗ trợ sức khỏe tâm thần",
        "number": "1800-599-920",
        "available": "24/7"
      },
      "bai_tap_grounding": {
        "id": "ground_54321",
        "title": "Kỹ thuật 5-4-3-2-1",
        "instruction": "Nhìn quanh và tìm 5 thứ bạn thấy, 4 thứ bạn chạm được..."
      },
      "suggest_clinic": true
    }
  },
  "error": null
}
```

**Lưu ý cho FE:**
- Kiểm tra `sos_triggered` **trước** khi render `reply`.
- Khi `sos_triggered = true`: override toàn bộ UI bằng `sos_card`, ẩn input box, không cho gõ tiếp.
- `tone_cam_xuc` nhận các giá trị: `"ho_tro"`, `"xac_nhan"`, `"vui_tuoi"`, `"lam_diu"`.

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

### `GET /chat/sessions/{session_id}/messages?limit=20&offset=0`
Lấy lịch sử tin nhắn của 1 phiên. Sắp xếp cũ → mới.

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
Xóa phiên chat (soft delete — nội dung ẩn với user, hệ thống giữ summary ẩn danh cho analytics).

```json
// Response 200
{
  "success": true,
  "data": { "deleted_at": "2026-04-12T15:00:00Z" },
  "error": null
}
```

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

> Mỗi ngày chỉ cho phép 1 lần checkin. Nếu đã có → trả lỗi `MOOD_ALREADY_LOGGED` (409). FE hiện nút "Cập nhật" dùng `PATCH /mood/checkin/{checkin_id}` thay thế.

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
Danh sách nội dung theo category.

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
        "url": "https://cdn.example.com/audio/med_042.mp3",
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

---

### `GET /resources/{id}`
Chi tiết 1 nội dung.

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
    "url": "https://cdn.example.com/audio/med_042.mp3",
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
        "name": "Đường dây hỗ trợ sức khỏe tâm thần quốc gia",
        "number": "1800-599-920",
        "available": "24/7",
        "note": "Miễn phí"
      },
      {
        "name": "Tổng đài hỗ trợ trẻ em",
        "number": "111",
        "available": "24/7",
        "note": "Miễn phí"
      }
    ]
  },
  "error": null
}
```

---

### `GET /connect/clinics?lat=21.03&lng=105.85&radius_km=10`
Danh sách phòng khám/trung tâm tư vấn gần vị trí user.

```json
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
    ],
    "query": { "lat": 21.03, "lng": 105.85, "radius_km": 10 }
  },
  "error": null
}
```

> Nếu user **không cấp quyền location**: FE bỏ `lat`/`lng`, gọi `GET /connect/clinics` không có params — API trả danh sách mặc định (Hà Nội). Không trả lỗi.

---

## 7. Admin / Internal

> Các endpoint này **không expose ra FE user**. Bảo vệ bằng JWT có `role: "admin"` — kiểm tra ở middleware FastAPI.

### `GET /admin/crisis-logs?from=2026-04-01&to=2026-04-12`
Danh sách sự kiện SOS để admin review.

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
    "total": 3
  },
  "error": null
}
```

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
| `DISCLAIMER_NOT_ACCEPTED` | 400 | Signup thiếu tick disclaimer |
| `MOOD_ALREADY_LOGGED` | 409 | Đã checkin mood hôm nay |
| `SESSION_NOT_FOUND` | 404 | Sai hoặc không có quyền truy cập session_id |
| `RESOURCE_NOT_FOUND` | 404 | ID nội dung không tồn tại |
| `GUARDRAIL_INPUT_BLOCKED` | 422 | Input bị NeMo chặn (prompt injection, toxic) |
| `LLM_TIMEOUT` | 504 | LangGraph pipeline > 10s — FE nên retry 1 lần |
| `SCHEMA_VALIDATION_FAILED` | 500 | Agent trả sai schema, đã fallback safe reply |
| `RATE_LIMIT_EXCEEDED` | 429 | Vượt 30 msg/phút tại `/chat/message` |
| `ADMIN_FORBIDDEN` | 403 | JWT không có role admin |

---

## Ghi chú kỹ thuật

### PII Masking
Xảy ra ở middleware FastAPI **trước khi** request vào LangGraph. FE không cần xử lý. Mọi dữ liệu lưu DB đều đã được mask.

### SOS Override (bắt buộc)
FE **phải** kiểm tra `sos_triggered` trước khi render bất kỳ nội dung nào từ `/chat/message`. Khi `sos_triggered = true`:
1. Render `sos_card` thay thế toàn bộ reply
2. Ẩn input box — không cho user gõ thêm
3. Hiển thị nút gọi hotline và nút xem phòng khám

### Streaming (Roadmap)
MVP dùng REST sync. Nếu latency P95 > 5s ở Phase 2, nâng cấp lên endpoint `/chat/stream` (SSE). FE thiết kế component chat có thể swap giữa sync và streaming.

### Rate Limit
- `/chat/message`: 30 req/phút/user
- Tất cả endpoint khác: 100 req/phút/user
- Header response khi gần giới hạn: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Admin Auth
Endpoint `/admin/*` yêu cầu JWT có claim `role: "admin"`. Kiểm tra tại FastAPI middleware — không phân biệt bằng endpoint riêng hay API key tách biệt.
