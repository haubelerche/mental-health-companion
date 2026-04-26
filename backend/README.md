# Serene API (FastAPI)

Cài dependency (từ thư mục gốc repo):

```powershell
pip install -r backend/requirements.txt
```

Chạy server:

**Cách chuẩn** (đặt cwd là `backend/` để import `app` đúng):

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Từ thư mục gốc repo** (không `cd backend`) — set `PYTHONPATH` trỏ vào `backend`:

```powershell
$env:PYTHONPATH = "$PWD\backend"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Nếu bỏ qua bước này và chạy uvicorn ở repo root **không** có `PYTHONPATH`, sẽ gặp `ModuleNotFoundError: No module named 'app'`.

Health: `GET http://127.0.0.1:8000/health`. API có tiền tố `api_prefix` (mặc định `/v1`).

**Auth trên máy local:** trong `.env` đặt `JWT_DEV_SECRET` (chuỗi ≥ 16 ký tự) để ký JWT bằng HS256 khi chưa có `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`. Nếu `DATABASE_URL` để trống, ứng dụng dùng SQLite `serene_local.db` trong cwd (thường là `backend/`) và có thể tự tạo bảng khi `AUTO_CREATE_SCHEMA=true` (mặc định trong trường hợp đó).

## Tests (pytest)

- Từ **thư mục gốc repo**: `pytest backend/tests -q` (đúng với CI).
- Từ **thư mục `backend/`**: `pytest tests -q` — không dùng `pytest backend/tests` vì đường dẫn đó chỉ tồn tại khi cwd là repo root.
