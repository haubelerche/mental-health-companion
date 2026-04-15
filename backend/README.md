# Serene FastAPI Backend

## Tổng Quan Nhanh

Đây là backend FastAPI cho ứng dụng hỗ trợ sức khỏe tinh thần. Dự án bao gồm đầy đủ các nhóm API chính:
- Auth: đăng ký, đăng nhập, refresh, logout, CSRF  
- Chat: gửi tin nhắn, lịch sử phiên chat, xóa phiên  
- Home/Mood: check-in tâm trạng, sửa check-in, home feed  
- Reflect: nhật ký (journal), xu hướng tâm trạng (mood trend), ghi chú tuần (weekly note), prompts  
- Resources: danh sách nội dung, chi tiết, play event, bookmark  
- Connect: hotline, phòng khám  
- Admin: crisis logs, dashboard, admin login  

## Điểm Nổi Bật

- Xác thực bằng cookie httpOnly + CSRF, không trả token trong body  
- Rate limit và lockout sử dụng Redis  
- Schema database được quản lý bằng Alembic migration  
- Hỗ trợ PostgreSQL/Supabase thông qua `DATABASE_URL` trong file `.env`  
- Tài liệu test chi tiết nằm trong [docs/API_TESTS.md](../docs/API_TESTS.md)  

Nếu muốn test nhanh, hãy đọc theo thứ tự trong file API TEST và chạy backend theo các lệnh ở phần dưới.

## Sau Khi Clone Về Cần Bổ Sung Gì?

1. Tạo file `.env` ở thư mục gốc repository (copy từ `backend/.env.example`)  
2. Điền tối thiểu các biến:
   - `DATABASE_URL`  
   - `REDIS_URL`  
   - `ADMIN_ALLOWED_IPS`  
3. Tùy chọn cho môi trường dev: `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY` có thể để trống  

## Chạy Backend (Đúng Thứ Tự)

1. Kích hoạt virtual environment (Windows):

```powershell
venv\Scripts\Activate.ps1