# OAuth API Google & Facebook

Tài liệu này mô tả các endpoint OAuth ở backend và cách frontend tích hợp để đăng nhập bằng Google / Facebook.

## Tổng quan
- Nhà cung cấp hỗ trợ: Google, Facebook.
- Luồng xử lý:
  - FE điều hướng người dùng đến backend `/auth/oauth/{provider}/start`.
  - Backend tạo `state` ngắn hạn, lưu Redis hoặc ký số, rồi redirect sang trang consent của nhà cung cấp.
  - Provider trả về backend callback `/auth/oauth/{provider}/callback`.
  - Backend kiểm tra `state`, đổi `code` lấy token, đọc profile, link hoặc tạo user, set cookie đăng nhập, rồi redirect về FE.

## Endpoint

### Google

- `GET /auth/oauth/google/start?return_to=<frontend_url>`
  - Query params:
    - `return_to` là URL frontend muốn quay về sau khi đăng nhập xong.
    - Nếu không truyền, backend dùng giá trị cấu hình `FRONTEND_AUTH_REDIRECT_URL`.
  - Response: redirect sang màn hình consent của Google.

- `GET /auth/oauth/google/callback?code=...&state=...`
  - Backend sẽ:
    - kiểm tra `state`;
    - đổi `code` lấy access token;
    - lấy thông tin người dùng từ Google;
    - tìm user hiện có theo `provider + provider_user_id`;
    - nếu chưa có identity, thử match theo email đã xác minh.
  - Hành vi:
    - Email đã xác minh và trùng user hiện có: link tài khoản và đăng nhập user đó.
    - Email đã xác minh nhưng chưa có user: tự tạo user mới, đánh dấu email đã xác minh, link identity, rồi đăng nhập.
    - Không có email đã xác minh: không tự tạo tài khoản; backend redirect về FE với `?oauth_missing_email=1&provider=google` để FE xử lý tiếp.
  - Khi thành công, backend set các cookie:
    - `access_token`
    - `refresh_token`
    - `csrf_token`
  - Sau đó redirect về `return_to`.

### Facebook

- `GET /auth/oauth/facebook/start?return_to=<frontend_url>`
  - Cách dùng giống Google.

- `GET /auth/oauth/facebook/callback?code=...&state=...`
  - Facebook có thể không trả về email.
  - Nếu có email, backend xử lý giống Google.
  - Nếu thiếu email hoặc email không đủ tin cậy, backend redirect về `return_to?oauth_missing_email=1&provider=facebook`.

## Cách FE tích hợp

- Khi user bấm nút “Tiếp tục với Google/Facebook”, FE phải mở một điều hướng cấp trang sang backend, không dùng XHR/fetch.
- FE gọi:

```text
http://localhost:8000/v1/auth/oauth/google/start?return_to=http://localhost:5173/auth/callback
```

hoặc:

```text
http://localhost:8000/v1/auth/oauth/facebook/start?return_to=http://localhost:5173/auth/callback
```

- Sau khi backend xử lý xong, browser sẽ được redirect về route FE `/auth/callback`.
- FE ở route này nên:
  - gọi `GET /v1/auth/me` để xác nhận user đã đăng nhập;
  - nếu thành công thì điều hướng vào app;
  - nếu URL có `oauth_missing_email=1`, hiển thị thông báo để user đăng nhập bằng email/password hoặc liên kết tài khoản thủ công.

## Mẫu luồng

1. FE mở `GET http://localhost:8000/v1/auth/oauth/google/start?return_to=http://localhost:5173/auth/callback`.
2. User đồng ý trên Google.
3. Google trả về `http://localhost:8000/v1/auth/oauth/google/callback`.
4. Backend set cookie đăng nhập và redirect về `http://localhost:5173/auth/callback`.
5. FE gọi `GET /v1/auth/me` để lấy trạng thái user.

## Giá trị cấu hình cần điền

### Local

- Authorized JavaScript origins:
  - `http://localhost:5173`
- Authorized redirect URIs:
  - `http://localhost:8000/v1/auth/oauth/google/callback`
  - `http://localhost:8000/v1/auth/oauth/facebook/callback`

### Production

- Authorized JavaScript origins:
  - `https://<frontend-domain>`
- Authorized redirect URIs:
  - `https://<backend-domain>/v1/auth/oauth/google/callback`
  - `https://<backend-domain>/v1/auth/oauth/facebook/callback`

## Lưu ý bảo mật

- `state` có thời hạn ngắn và được lưu server-side hoặc ký số để chống CSRF / replay.
- Chỉ tự động link tài khoản khi email từ provider đã xác minh.
- Với Facebook hoặc provider không trả email, cần yêu cầu user liên kết thủ công hoặc xác minh email trước khi tạo tài khoản.
