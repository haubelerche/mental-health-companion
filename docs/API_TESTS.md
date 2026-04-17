# API Test Guide (Current Backend Implementation)

Ngay tai lieu nay mo ta toan bo API hien co trong code, kem cach test bang Postman va ky vong ket qua.

## 1. Test Scope

Backend hien co cac nhom endpoint:
- Health: 1 endpoint
- Auth: 5 endpoints
- Chat: 4 endpoints
- Home/Mood: 3 endpoints
- Reflect: 5 endpoints
- Resources: 6 endpoints
- Connect: 2 endpoints
- Admin: 3 endpoints

Tong cong: 29 endpoints.

## 2. Base URL va Response Format

- Base URL API: `http://127.0.0.1:8000/v1`
- Health endpoint: `http://127.0.0.1:8000/health`

Tat ca API business tra theo envelope:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Khi loi:

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

Tao 1 environment voi cac bien:

- `baseUrl` = `http://127.0.0.1:8000`
- `csrfToken` = (rong)
- `userEmail` = `tester@example.com`
- `userPassword` = `Password123!`
- `sessionId` = (rong)
- `checkinId` = (rong)
- `resourceId` = `res_001` (hoac id that trong DB)

Luu y:
- Postman phai bat cookie jar mac dinh.
- Cac request POST/PATCH/DELETE phia user can header `X-CSRF-Token: {{csrfToken}}`.

## 4. Thu Tu Chay De Tranh Loi Bien

1. Health
2. Auth -> csrf-token
3. Auth -> signup
4. Auth -> login
5. Chat -> message (lay `sessionId`)
6. Chat -> sessions
7. Chat -> session messages
8. Home -> mood checkin (lay `checkinId`)
9. Home -> patch checkin
10. Home -> feed
11. Reflect -> mood-trend
12. Reflect -> weekly-note
13. Reflect -> journal
14. Reflect -> journals
15. Reflect -> journal-prompts
16. Resources -> categories
17. Resources -> list by category
18. Resources -> detail
19. Resources -> play-event
20. Resources -> bookmark create
21. Resources -> bookmark delete
22. Connect -> hotlines
23. Connect -> clinics
24. Admin -> auth login
25. Admin -> crisis-logs
26. Admin -> dashboard
27. Auth -> refresh
28. Auth -> logout

## 5. Test Cases Chi Tiet Theo Endpoint

## 5.1 Health

### GET /health
- URL: `{{baseUrl}}/health`
- Auth: Khong
- Ky vong:
  - HTTP 200
  - Body co `status = "ok"`

## 5.2 Auth

### GET /v1/auth/csrf-token
- URL: `{{baseUrl}}/v1/auth/csrf-token`
- Auth: Khong
- Ky vong:
  - HTTP 200
  - `success = true`
  - `data.csrf_token` co gia tri
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

- Ky vong pass:
  - HTTP 201
  - `success = true`
  - `data.user_id` co gia tri
  - Cookie `access_token`, `refresh_token`, `csrf_token` duoc set
- Ky vong fail:
  - disclaimer false -> 400 `DISCLAIMER_NOT_ACCEPTED`
  - email ton tai -> 400 `INVALID_PARAMETER`
  - vuot gioi han -> 429 `RATE_LIMIT_AUTH`

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

- Ky vong pass:
  - HTTP 200
  - `success = true`
  - `data.user_id`, `data.expires_in`
- Ky vong fail:
  - sai thong tin -> 401 `AUTH_INVALID_TOKEN`
  - sai nhieu lan -> 429 `AUTH_TOO_MANY_ATTEMPTS`
  - vuot gioi han theo IP -> 429 `RATE_LIMIT_AUTH`

### POST /v1/auth/refresh
- URL: `{{baseUrl}}/v1/auth/refresh`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Cookie: refresh token da co tu login/signup
- Ky vong pass:
  - HTTP 200
  - `data.expires_in`
- Ky vong fail:
  - thieu cookie refresh -> 401 `AUTH_REFRESH_MALFORMED`
  - token revoked -> 401 `AUTH_REFRESH_REVOKED`
  - token expired -> 401 `AUTH_REFRESH_EXPIRED`

### POST /v1/auth/logout
- URL: `{{baseUrl}}/v1/auth/logout`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Ky vong pass:
  - HTTP 200
  - `data.logged_out_at`
  - cookie auth bi clear

## 5.3 Chat

### POST /v1/chat/message
- URL: `{{baseUrl}}/v1/chat/message`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Body (tao session moi):

```json
{
  "message": "Hom nay minh rat met",
  "session_id": null
}
```

- Ky vong pass:
  - HTTP 200
  - `data.session_id` co gia tri
  - `sos_triggered` la true/false
- Postman Tests:

```javascript
const body = pm.response.json();
pm.environment.set("sessionId", body.data.session_id);
```

- Ky vong fail:
  - session_id sai owner -> 404 `SESSION_NOT_FOUND`
  - vuot gioi han -> 429 `RATE_LIMIT_EXCEEDED`

### GET /v1/chat/sessions
- URL: `{{baseUrl}}/v1/chat/sessions`
- Auth: Cookie user
- Ky vong:
  - HTTP 200
  - `data.sessions` la array

### GET /v1/chat/sessions/{session_id}/messages
- URL: `{{baseUrl}}/v1/chat/sessions/{{sessionId}}/messages?limit=20&offset=0`
- Ky vong:
  - HTTP 200
  - `data.messages`, `data.total`, `data.has_more`

### DELETE /v1/chat/sessions/{session_id}
- URL: `{{baseUrl}}/v1/chat/sessions/{{sessionId}}`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Optional hard delete:
  - `{{baseUrl}}/v1/chat/sessions/{{sessionId}}?hard=true`
- Ky vong:
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

- Ky vong pass:
  - HTTP 201
  - `data.checkin_id`, `data.logged_at`
- Ky vong fail:
  - da checkin hom nay -> 409 `MOOD_ALREADY_LOGGED`
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

- Ky vong pass:
  - HTTP 200
  - `data.updated_at`
- Ky vong fail:
  - checkin khong ton tai/sai owner -> 404 `CHECKIN_NOT_FOUND`
  - khong phai checkin hom nay -> 409 `CHECKIN_NOT_EDITABLE`

### GET /v1/home/feed
- URL: `{{baseUrl}}/v1/home/feed`
- Ky vong:
  - HTTP 200
  - Co du cac block: quote_of_day, suggested_meditation, mood_today

## 5.5 Reflect

### GET /v1/reflect/mood-trend?days=7
- URL: `{{baseUrl}}/v1/reflect/mood-trend?days=7`
- Ky vong pass:
  - HTTP 200
  - Co `period`, `points`, `days_missing`
- Ky vong fail:
  - days ngoai [1..90] -> 400 `INVALID_PARAMETER`

### GET /v1/reflect/weekly-note
- URL: `{{baseUrl}}/v1/reflect/weekly-note`
- Ky vong:
  - HTTP 200
  - Co `week_of`, `content`, `generated_at`

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

- Ky vong pass:
  - HTTP 201
  - Co `journal_id`
- Ky vong fail:
  - prompt_id khong hop le -> 400 `INVALID_PARAMETER`

### GET /v1/reflect/journals?limit=20&offset=0
- URL: `{{baseUrl}}/v1/reflect/journals?limit=20&offset=0`
- Ky vong:
  - HTTP 200
  - Co `journals`, `total`, `has_more`

### GET /v1/reflect/journal-prompts
- URL: `{{baseUrl}}/v1/reflect/journal-prompts`
- Ky vong:
  - HTTP 200
  - Co `prompts` array

## 5.6 Resources

### GET /v1/resources/categories
- URL: `{{baseUrl}}/v1/resources/categories`
- Ky vong:
  - HTTP 200
  - Co 6 category

### GET /v1/resources?category=meditate&limit=20&offset=0
- URL: `{{baseUrl}}/v1/resources?category=meditate&limit=20&offset=0`
- Ky vong pass:
  - HTTP 200
  - Co `items`, `total`, `has_more`
- Ky vong fail:
  - category sai -> 400 `INVALID_PARAMETER`

### GET /v1/resources/{resource_id}
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}`
- Ky vong pass:
  - HTTP 200
  - Co `url`, `url_expires_at`
- Ky vong fail:
  - id khong ton tai -> 404 `RESOURCE_NOT_FOUND`

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

- Ky vong pass:
  - HTTP 200
  - Co `tracked_at`
- Ky vong fail:
  - event sai -> 400 `INVALID_PARAMETER`
  - duration qua lon -> 400 `INVALID_PARAMETER`
  - resource khong ton tai -> 404 `RESOURCE_NOT_FOUND`

### POST /v1/resources/{resource_id}/bookmark
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}/bookmark`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Ky vong:
  - HTTP 201
  - Co `bookmarked_at`

### DELETE /v1/resources/{resource_id}/bookmark
- URL: `{{baseUrl}}/v1/resources/{{resourceId}}/bookmark`
- Header:
  - `X-CSRF-Token: {{csrfToken}}`
- Ky vong:
  - HTTP 200
  - Co `removed_at`

## 5.7 Connect

### GET /v1/connect/hotlines
- URL: `{{baseUrl}}/v1/connect/hotlines`
- Ky vong:
  - HTTP 200
  - Co danh sach hotlines

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

- Ky vong:
  - HTTP 200
  - Header response co `Cache-Control: no-store`
  - Co `clinics` array

## 5.8 Admin

Dieu kien:
- `ADMIN_ALLOWED_IPS` phai cho phep IP local (vi du 127.0.0.1/32)

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

- Ky vong:
  - HTTP 200
  - Co `admin_id`, `expires_in`

### GET /v1/admin/crisis-logs
- URL: `{{baseUrl}}/v1/admin/crisis-logs`
- Ky vong pass:
  - HTTP 200
  - Co `logs`, `total`, `has_more`
- Ky vong fail:
  - sai role/IP -> 403 `ADMIN_FORBIDDEN`

### GET /v1/admin/dashboard/aggregate
- URL: `{{baseUrl}}/v1/admin/dashboard/aggregate`
- Ky vong:
  - HTTP 200
  - Co cac truong aggregate

## 6. Negative Test Nen Chay Them

- Signup disclaimer false -> 400 `DISCLAIMER_NOT_ACCEPTED`
- Login sai mat khau lien tiep de kich lockout -> 429 `AUTH_TOO_MANY_ATTEMPTS`
- Spam /chat/message -> 429 `RATE_LIMIT_EXCEEDED`
- Tao mood checkin lan 2 trong ngay -> 409 `MOOD_ALREADY_LOGGED`
- PATCH checkin cua ngay cu -> 409 `CHECKIN_NOT_EDITABLE`
- Reflect mood-trend voi `days=0` hoac `days=91` -> 400 `INVALID_PARAMETER`
- Resources category sai -> 400 `INVALID_PARAMETER`
- Resources detail id sai -> 404 `RESOURCE_NOT_FOUND`

## 7. Quick Postman Test Scripts (Optional)

Script check envelope chung cho moi request trong tab Tests:

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

Script cho request can status code cu the:

```javascript
pm.test("status is expected", function () {
  pm.response.to.have.status(200);
});
```

## 8. Notes Ve Du Lieu

- Cac endpoint can auth phu thuoc cookie access token.
- Neu test bang user moi, can chay lai csrf -> signup/login -> endpoint business.
- Neu signup tung fail o version cu, email co the da ton tai trong DB. Kiem tra bang SQL:

```sql
select email, created_at from users order by created_at desc;
```
