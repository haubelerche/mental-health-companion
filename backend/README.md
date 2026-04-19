# Serene API (FastAPI)


```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/health`. API có tiền tố `api_prefix` (mặc định `/v1`).
