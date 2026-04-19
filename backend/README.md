# Serene API (FastAPI)

Cài dependency (từ thư mục gốc repo):

```powershell
pip install -r backend/requirements.txt
```

Chạy server:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/health`. API có tiền tố `api_prefix` (mặc định `/v1`).

## Tests (pytest)

- Từ **thư mục gốc repo**: `pytest backend/tests -q` (đúng với CI).
- Từ **thư mục `backend/`**: `pytest tests -q` — không dùng `pytest backend/tests` vì đường dẫn đó chỉ tồn tại khi cwd là repo root.
