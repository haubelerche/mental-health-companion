# API Test Guide (Current Backend Implementation)

Tài liệu này mô tả toàn bộ API hiện có trong code, kèm cách test bằng Postman và kỳ vọng kết quả.

## 1. Test Scope

Backend hiện có các nhóm endpoint:
- Health: 1 endpoint
- Auth: 9 endpoints
- Chat: 4 endpoints
- Home/Mood: 3 endpoints
- Reflect: 5 endpoints
- Resources: 6 endpoints
- Connect: 2 endpoints
- Admin: 7 endpoints

Tổng cộng: 37 endpoints.

## 2. Base URL và Response Format

- Base URL API: `http://127.0.0.1:8000/v1`
- Health endpoint: `http://127.0.0.1:8000/health`

Tất cả API business trả theo envelope:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Khi lỗi:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SOME_CODE",
    "message": "..."
  }
}
```

## 3. Postman Environment

Tạo 1 environment với các biến:

- `baseUrl` = `http://127.0.0.1:8000`
- `csrfToken` = (rỗng)
- `userEmail` = `tester@example.com`
- `userPassword` = `Password123!`
- `verifyToken` = (copy token từ email verify)
- `resetToken` = (copy token từ email reset password)
- `sessionId` = (rỗng)
- `checkinId` = (rỗng)
- `resourceId` = `res_001` (hoặc id thật trong DB)
- `adminResourceId` = (rỗng)

Lưu ý:
- Postman phải bật cookie jar mặc định.
- Các request POST/PATCH/DELETE phía user cần header `X-CSRF-Token: {{csrfToken}}`.

## 4. Thứ Tự Chạy Để Tránh Lỗi Biến

1. Health
2. Auth -> csrf-token
3. Auth -> signup
4. Auth -> login trước verify (expect AUTH_EMAIL_NOT_VERIFIED)
5. Auth -> verify-email (từ link trong email)
6. Auth -> login sau verify
7. Auth -> resend-verification (test cooldown)
8. Auth -> forgot-password
9. Auth -> reset-password (từ link trong email)
10. Chat -> message (lấy `sessionId`)
11. Chat -> sessions
12. Chat -> session messages
13. Home -> mood checkin (lấy `checkinId`)
14. Home -> patch checkin
15. Home -> feed
16. Reflect -> mood-trend
17. Reflect -> weekly-note
18. Reflect -> journal
19. Reflect -> journals
20. Reflect -> journal-prompts
21. Resources -> categories
22. Resources -> list by category
23. Resources -> detail
24. Resources -> play-event
25. Resources -> bookmark create
26. Resources -> bookmark delete
27. Connect -> hotlines
28. Connect -> clinics
29. Admin -> auth login
30. Admin -> crisis-logs
31. Admin -> dashboard
32. Admin -> resources list
33. Admin -> resources create (lấy `adminResourceId`)
34. Admin -> resources patch
35. Admin -> resources delete
36. Auth -> refresh
37. Auth -> logout

## 5. Test Cases Chi Tiết Theo Endpoint

## 5.1 Health

### GET /health
- URL: `{{baseUrl}}/health`
- Auth: Không
- Kỳ vọng:
  - HTTP 200
  - Body có `status = "ok"`

## 5.2 Auth

### GET /v1/auth/csrf-token
- URL: `{{baseUrl}}/v1/auth/csrf-token`
- Auth: Không
- Kỳ vọng:
  - HTTP 200
  - `success = true`
  - `data.csrf_token` có giá trị
- Postman Tests:

```javascript
const body = pm.response.json();
pm.environment.set("csrfToken", body.data.csrf_token);
```

### POST /v1/auth/signup
- URL: `{{baseUrl}}/v1/auth/signup`
- Header:
  - `Content-Type: application/json`
- Body:

```json
{
  "display_name": "Tester",
  "email": "{{userEmail}}",
  "password": "{{userPassword}}",
  "disclaimer_accepted": true
}
```

- Kỳ vọng pass:
  - HTTP 202
  - `success = true`
  - `data.user_id` có giá trị
  - `data.verification_required = true`
  - Không set cookie `access_token`/`refresh_token` (chưa login)
- Kỳ vọng fail:
  - disclaimer false -> 400 `DISCLAIMER_NOT_ACCEPTED`
  - email tồn tại -> 400 `INVALID_PARAMETER`
  - vượt giới hạn -> 429 `RATE_LIMIT_AUTH`

### POST /v1/auth/login
- URL: `{{baseUrl}}/v1/auth/login`
- Header:
  - `Content-Type: application/json`
- Body:

```json
{
  "email": "test4@gmai.com",
  "password": "12345678"
}
```

- Kỳ vọng pass:
  - HTTP 200
  - `success = true`
  - `data.user_id`, `data.expires_in`
- Kỳ vọng fail:
  - sai thông tin -> 401 `AUTH_INVALID_TOKEN`
  - đúng mật khẩu nhưng chưa verify -> 403 `AUTH_EMAIL_NOT_VERIFIED`
  - sai nhiều lần -> 429 `AUTH_TOO_MANY_ATTEMPTS`
  - vượt giới hạn theo IP -> 429 `RATE_LIMIT_AUTH`

### GET /v1/auth/verify-email
- URL: `{{baseUrl}}/v1/auth/verify-email?token={{verifyToken}}`
- Auth: Không
- Kỳ vọng pass:
  - HTTP 302 redirect về `FRONTEND_HOME_URL`
  - Cookie `access_token`, `refresh_token`, `csrf_token` được set
- Kỳ vọng fail:
  - token sai -> 400 `AUTH_VERIFY_TOKEN_INVALID`
  - token hết hạn -> 400 `AUTH_VERIFY_TOKEN_EXPIRED`

### POST /v1/auth/resend-verification
- URL: `{{baseUrl}}/v1/auth/resend-verification`
- Header:
  - `Content-Type: application/json`
- Body:

```json
{
  "email": "{{userEmail}}"
}
```

- Kỳ vọng:
  - HTTP 200
  - response trung tính (không lộ account enumeration)
  - `data.resent = true`
  - `data.message` kiểu: "Nếu email tồn tại, chúng tôi đã gửi lại email xác nhận"
- Lưu ý:
  - Có resend cooldown theo `AUTH_EMAIL_RESEND_COOLDOWN_SECONDS`

### POST /v1/auth/forgot-password
- URL: `{{baseUrl}}/v1/auth/forgot-password`
- Header:
  - `Content-Type: application/json`
- Body:

```json
{
  "email": "{{userEmail}}"
}
```

- Kỳ vọng:
  - HTTP 200
  - response trung tính (không lộ account enumeration)
  - `data.sent = true`

### POST /v1/auth/reset-password
- URL: `{{baseUrl}}/v1/auth/reset-password`
- Header:
  - `Content-Type: application/json`
- Body:

```json
{
  "token": "{{resetToken}}",
  "new_password": "NewPassword123!"
}
```

- Kỳ vọng pass:
  - HTTP 200
  - `data.reset = true`
  - refresh token cũ bị revoke
- Kỳ vọng fail:
  - token sai -> 400 `AUTH_RESET_TOKEN_INVALID`
  - token đã dùng -> 400 `AUTH_RESET_TOKEN_USED`
  - token hết hạn -> 400 `AUTH_RESET_TOKEN_EXPIRED`

### POST /v1/auth/refresh
- URL: `{{baseUrl}}/v1/auth/refresh`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Cookie: refresh token đã có từ login/verify-email
- Kỳ vọng pass:
  - HTTP 200
  - `data.expires_in`
- Kỳ vọng fail:
  - thiếu cookie refresh -> 401 `AUTH_REFRESH_MALFORMED`
  - token revoked -> 401 `AUTH_REFRESH_REVOKED`
  - token expired -> 401 `AUTH_REFRESH_EXPIRED`

### POST /v1/auth/logout
- URL: `{{baseUrl}}/v1/auth/logout`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Kỳ vọng pass:
  - HTTP 200
  - `data.logged_out_at`
  - cookie auth bị clear

## 5.3 Chat

### POST /v1/chat/message
- URL: `{{baseUrl}}/v1/chat/message`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body (tạo session mới):

```json
{
  "message": "Hom nay minh rat met",
  "session_id": null
}
```

- Kỳ vọng pass:
  - HTTP 200
  - `data.session_id` có giá trị
  - `sos_triggered` là true/false
- Postman Tests:

```javascript
const body = pm.response.json();
pm.environment.set("sessionId", body.data.session_id);
```

- Kỳ vọng fail:
  - session_id sai owner -> 404 `SESSION_NOT_FOUND`
  - vượt giới hạn -> 429 `RATE_LIMIT_EXCEEDED`

### GET /v1/chat/sessions
- URL: `{{baseUrl}}/v1/chat/sessions`
- Auth: Cookie user
- Kỳ vọng:
  - HTTP 200
  - `data.sessions` là array

### GET /v1/chat/sessions/{session_id}/messages
- URL: `{{baseUrl}}/v1/chat/sessions/{{sessionId}}/messages?limit=20&offset=0`
- Kỳ vọng:
  - HTTP 200
  - `data.messages`, `data.total`, `data.has_more`

### DELETE /v1/chat/sessions/{session_id}
- URL: `{{baseUrl}}/v1/chat/sessions/{{sessionId}}`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Optional hard delete:
  - `{{baseUrl}}/v1/chat/sessions/{{sessionId}}?hard=true`
- Kỳ vọng:
  - HTTP 200
  - `data.deleted_at`, `data.hard_delete_at`

## 5.4 Home / Mood

### POST /v1/mood/checkin
- URL: `{{baseUrl}}/v1/mood/checkin`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body:

```json
{
  "mood": "stressed",
  "emoji": ":(",
  "note": "deadline"
}
```

- Kỳ vọng pass:
  - HTTP 201
  - `data.checkin_id`, `data.logged_at`
- Kỳ vọng fail:
  - đã checkin hôm nay -> 409 `MOOD_ALREADY_LOGGED`
- Postman Tests:

```javascript
const body = pm.response.json();
pm.environment.set("checkinId", body.data.checkin_id);
```

### PATCH /v1/mood/checkin/{checkin_id}
- URL: `{{baseUrl}}/v1/mood/checkin/{{checkinId}}`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body:

```json
{
  "mood": "okay",
  "emoji": ":|",
  "note": null
}
```

- Kỳ vọng pass:
  - HTTP 200
  - `data.updated_at`
- Kỳ vọng fail:
  - checkin không tồn tại/sai owner -> 404 `CHECKIN_NOT_FOUND`
  - không phải checkin hôm nay -> 409 `CHECKIN_NOT_EDITABLE`

### GET /v1/home/feed
- URL: `{{baseUrl}}/v1/home/feed`
- Kỳ vọng:
  - HTTP 200
  - Có đủ các block: quote_of_day, suggested_meditation, mood_today

## 5.5 Reflect

### GET /v1/reflect/mood-trend?days=7
- URL: `{{baseUrl}}/v1/reflect/mood-trend?days=7`
- Kỳ vọng pass:
  - HTTP 200
  - Có `period`, `points`, `days_missing`
- Kỳ vọng fail:
  - days ngoài [1..90] -> 400 `INVALID_PARAMETER`

### GET /v1/reflect/weekly-note
- URL: `{{baseUrl}}/v1/reflect/weekly-note`
- Kỳ vọng:
  - HTTP 200
  - Có `week_of`, `content`, `generated_at`

### POST /v1/reflect/journal
- URL: `{{baseUrl}}/v1/reflect/journal`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body:

```json
{
  "content": "Hom nay tot hon hom qua",
  "prompt_id": null
}
```

- Kỳ vọng pass:
  - HTTP 201
  - Có `journal_id`
- Kỳ vọng fail:
  - prompt_id không hợp lệ -> 400 `INVALID_PARAMETER`

### GET /v1/reflect/journals?limit=20&offset=0
- URL: `{{baseUrl}}/v1/reflect/journals?limit=20&offset=0`
- Kỳ vọng:
  - HTTP 200
  - Có `journals`, `total`, `has_more`

### GET /v1/reflect/journal-prompts
- URL: `{{baseUrl}}/v1/reflect/journal-prompts`
- Kỳ vọng:
  - HTTP 200
  - Có `prompts` array

## 5.6 Resources

### GET /v1/resources/categories
- URL: `{{baseUrl}}/v1/resources/categories`
- Kỳ vọng:
  - HTTP 200
  - Có 6 category

### GET /v1/resources?category=meditate&limit=20&offset=0
- URL: `{{baseUrl}}/v1/resources?category=meditate&limit=20&offset=0`
- Kỳ vọng pass:
  - HTTP 200
  - Có `items`, `total`, `has_more`
- Kỳ vọng fail:
  - category sai -> 400 `INVALID_PARAMETER`

### GET /v1/resources/{resource_id}
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}`
- Kỳ vọng pass:
  - HTTP 200
  - Có `url`, `url_expires_at`
- Kỳ vọng fail:
  - id không tồn tại -> 404 `RESOURCE_NOT_FOUND`

### POST /v1/resources/{resource_id}/play-event
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}/play-event`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body:

```json
{
  "event": "completed",
  "duration_sec": 120,
  "percent": 80
}
```

- Kỳ vọng pass:
  - HTTP 200
  - Có `tracked_at`
- Kỳ vọng fail:
  - event sai -> 400 `INVALID_PARAMETER`
  - duration quá lớn -> 400 `INVALID_PARAMETER`
  - resource không tồn tại -> 404 `RESOURCE_NOT_FOUND`

### POST /v1/resources/{resource_id}/bookmark
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}/bookmark`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Kỳ vọng:
  - HTTP 201
  - Có `bookmarked_at`

### DELETE /v1/resources/{resource_id}/bookmark
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}/bookmark`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Kỳ vọng:
  - HTTP 200
  - Có `removed_at`

## 5.7 Connect

### GET /v1/connect/hotlines
- URL: `{{baseUrl}}/v1/connect/hotlines`
- Kỳ vọng:
  - HTTP 200
  - Có danh sách hotlines

### POST /v1/connect/clinics
- URL: `{{baseUrl}}/v1/connect/clinics`
- Body:

```json
{
  "lat": 21.03,
  "lng": 105.85,
  "radius_km": 10
}
```

- Kỳ vọng:
  - HTTP 200
  - Header response có `Cache-Control: no-store`
  - Có `clinics` array

## 5.8 Admin

Điều kiện:
- `ADMIN_ALLOWED_IPS` phải cho phép IP local (ví dụ 127.0.0.1/32)

### POST /v1/admin/auth/login
- URL: `{{baseUrl}}/v1/admin/auth/login`
- Body:

```json
{
  "email": "admin@example.com",
  "password": "Password123!",
  "totp_code": "123456"
}
```

- Kỳ vọng:
  - HTTP 200
  - Có `admin_id`, `expires_in`

### GET /v1/admin/crisis-logs
- URL: `{{baseUrl}}/v1/admin/crisis-logs`
- Kỳ vọng pass:
  - HTTP 200
  - Có `logs`, `total`, `has_more`
- Kỳ vọng fail:
  - sai role/IP -> 403 `ADMIN_FORBIDDEN`

### GET /v1/admin/dashboard/aggregate
- URL: `{{baseUrl}}/v1/admin/dashboard/aggregate`
- Kỳ vọng:
  - HTTP 200
  - Có các trường aggregate

### GET /v1/admin/resources?category=meditate&include_inactive=true&limit=20&offset=0
- URL: `{{baseUrl}}/v1/admin/resources?category=meditate&include_inactive=true&limit=20&offset=0`
- Kỳ vọng pass:
  - HTTP 200
  - Có `items`, `total`, `has_more`
- Kỳ vọng fail:
  - category sai -> 400 `INVALID_PARAMETER`
  - limit/offset sai -> 400 `INVALID_PARAMETER`

### POST /v1/admin/resources
- URL: `{{baseUrl}}/v1/admin/resources`
- Body:

```json
{
  "category": "meditate",
  "title": "Thiền thở 5 phút",
  "description": "Bài thở ngắn",
  "format": "audio",
  "duration_sec": 300,
  "storage_key": "audio/med_100.mp3",
  "thumbnail_key": "thumb/med_100.jpg",
  "tags": ["beginner", "calm"],
  "is_active": true
}
```

- Kỳ vọng pass:
  - HTTP 201
  - Có `data.resource_id`, `data.created_at`
- Kỳ vọng fail:
  - category/format sai -> 400 `INVALID_PARAMETER`

- Postman Tests:

```javascript
const body = pm.response.json();
pm.environment.set("adminResourceId", body.data.resource_id);
```

### PATCH /v1/admin/resources/{resource_id}
- URL: `{{baseUrl}}/v1/admin/resources/{{adminResourceId}}`
- Body:

```json
{
  "title": "Thiền thở 5 phút (cập nhật)",
  "is_active": false
}
```

- Kỳ vọng pass:
  - HTTP 200
  - Có `data.resource_id`, `data.updated_at`
- Kỳ vọng fail:
  - id sai -> 404 `RESOURCE_NOT_FOUND`

### DELETE /v1/admin/resources/{resource_id}
- URL: `{{baseUrl}}/v1/admin/resources/{{adminResourceId}}`
- Kỳ vọng pass:
  - HTTP 200
  - Có `data.resource_id`, `data.deleted_at`
- Kỳ vọng fail:
  - id sai -> 404 `RESOURCE_NOT_FOUND`
  - resource đang có dữ liệu liên quan -> 409 `RESOURCE_IN_USE`

## 6. Negative Test Nên Chạy Thêm

- Signup disclaimer false -> 400 `DISCLAIMER_NOT_ACCEPTED`
- Login sai mật khẩu liên tiếp để kích lockout -> 429 `AUTH_TOO_MANY_ATTEMPTS`
- Spam /chat/message -> 429 `RATE_LIMIT_EXCEEDED`
- Tạo mood checkin lần 2 trong ngày -> 409 `MOOD_ALREADY_LOGGED`
- PATCH checkin của ngày cũ -> 409 `CHECKIN_NOT_EDITABLE`
- Reflect mood-trend với `days=0` hoặc `days=91` -> 400 `INVALID_PARAMETER`
- Resources category sai -> 400 `INVALID_PARAMETER`
- Resources detail id sai -> 404 `RESOURCE_NOT_FOUND`
- Admin resources category sai -> 400 `INVALID_PARAMETER`
- Admin delete resource đang được bookmark/play-event -> 409 `RESOURCE_IN_USE`

## 7. Quick Postman Test Scripts (Optional)

Script check envelope chung cho mỗi request trong tab Tests:

```javascript
const body = pm.response.json();
pm.test("has success field", function () {
  pm.expect(body).to.have.property("success");
});
pm.test("has data field", function () {
  pm.expect(body).to.have.property("data");
});
pm.test("has error field", function () {
  pm.expect(body).to.have.property("error");
});
```

Script cho request cần status code cụ thể:

```javascript
pm.test("status is expected", function () {
  pm.response.to.have.status(200);
});
```

## 8. Notes Về Dữ Liệu

- Các endpoint cần auth phụ thuộc cookie access token.
- Nếu test bằng user mới, cần chạy lại csrf -> signup/login -> endpoint business.
- Nếu signup từng fail ở version cũ, email có thể đã tồn tại trong DB. Kiểm tra bằng SQL:

```sql
select email, created_at from users order by created_at desc;
```

## 9. Bamboo API (Thư ẩn danh) - Test Spec

Base path: `{{baseUrl}}/v1/bamboo`

Auth: cookie `access_token` + header `X-CSRF-Token: {{csrfToken}}`. User phải `policy_acknowledged`.

### POST /v1/bamboo/send
- Body: `content` (1-2000 chars), optional `topic`, `tone`.
- Expected: HTTP 201, data includes `message_id`, `status` = `pending`, `sent_at`.

Example request:
```json
{
  "content": "Hôm nay mình muốn gửi một lời chúc...",
  "topic": "encouragement",
  "tone": "gentle"
}
```

### GET /v1/bamboo/inbox
- Returns public feed of approved letters.
- Expected: HTTP 200, `data.messages` array with `message_id`, `anonymous_name`, `content`, `topic`, `tone`, `received_at`, `pass_count`, `reply_count`.

### GET /v1/bamboo/storage
- Returns user's sent and received (approved) letters.
- Expected: HTTP 200, `data.letters` array with `message_id`, `direction`, `status`, `content`, `topic`, `tone`, `created_at`.

### GET /v1/bamboo/letters/{message_id}
- Returns details for a letter. Only returns approved letters to other users; owner can view own pending.
- Expected: HTTP 200, detailed letter object.

### POST /v1/bamboo/reply
- Body: `message_id`, `content`, optional `topic`.
- Creates a reply (treated as a new pending message). Expected: HTTP 201, `reply_id`, `message_id`, `status` = `pending`.

### POST /v1/bamboo/pass
- Body: `message_id`.
- Increments `pass_count` for an approved message. Expected: HTTP 200 with updated `pass_count` and `passed_at`.

### GET /v1/bamboo/moderation/queue (admin)
- Admin-only. Expected: HTTP 200, `items` list of pending items.

### PATCH /v1/bamboo/moderation/{message_id} (admin)
- Body: `{ "status": "approved" | "rejected" | "archived", "reason": null|str }`.
- Expected: HTTP 200 and message `status` updated.

Negative tests to include:
- Send without auth -> 401 `AUTH_INVALID_TOKEN`.
- Send with missing CSRF -> 403 `CSRF_TOKEN_INVALID`.
- Send content exceeding max length -> 422 `PAYLOAD_TOO_LARGE`.
- Reply to non-existent or non-approved message -> 404 `BAMBOO_MESSAGE_NOT_FOUND`.
- Admin moderation without admin token/IP -> 403 `ADMIN_FORBIDDEN`.
