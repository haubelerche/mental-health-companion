# Serene API (FastAPI)

Cấu hình: tạo `.env` ở **thư mục gốc repo** từ [`.env.example`](../.env.example) (ứng dụng nạp `../.env` trước, sau đó mới `backend/.env` nếu có).

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/health`. API có tiền tố `api_prefix` (mặc định `/v1`).
