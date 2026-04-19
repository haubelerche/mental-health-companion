# Serene API (FastAPI)


```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/health`. API có tiền tố `api_prefix` (mặc định `/v1`).

## Voice TTS Worker (proactive voice async)

Khi muốn chạy pipeline TTS tách process (production-style), mở terminal riêng:

```powershell
cd backend
python -m app.core.voice_tts_worker
```

Worker sẽ poll các event `voice.tts_request` trong `sync_outbox`, xử lý retry/stale recovery, và cập nhật trạng thái job.
