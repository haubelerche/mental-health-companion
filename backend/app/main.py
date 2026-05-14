from contextlib import asynccontextmanager
import os
import threading
import time
import warnings
from urllib.parse import urlparse

# Suppress LangChain/LangGraph internal deprecation warnings
warnings.filterwarnings("ignore", message=".*allowed_objects.*", category=DeprecationWarning)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.errors import AppError, humanize_validation_errors
from app.core.responses import fail
from app.services.db.init_db import init_db
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

settings = get_settings()


def _idle_loop() -> None:
    from app.services.idle_sessions import summarize_idle_sessions

    while True:
        time.sleep(120)
        try:
            summarize_idle_sessions()
        except Exception:
            pass


def _outbox_loop() -> None:
    from app.services.outbox_worker import run_outbox_worker_loop

    run_outbox_worker_loop(poll_seconds=10)


def _voice_tts_loop() -> None:
    from app.core.voice_tts_worker import run_forever

    run_forever(poll_seconds=2, batch_size=20)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Register the main event loop for notification_service to use in thread-safe pushes
    import asyncio
    from app.services.notification_service import register_main_loop
    register_main_loop(asyncio.get_running_loop())

    if settings.auto_create_schema:
        init_db()
    if os.environ.get("SERENE_BACKEND_TESTING") != "1" and settings.background_workers_enabled:
        if settings.idle_summarizer_enabled:
            threading.Thread(target=_idle_loop, daemon=True).start()
        if settings.notification_outbox_worker_enabled:
            threading.Thread(target=_outbox_loop, daemon=True).start()
        if settings.voice_tts_worker_enabled:
            threading.Thread(target=_voice_tts_loop, daemon=True).start()
    yield



app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:5500",
]
_extra = [o.strip() for o in settings.cors_extra_origins.split(",") if o.strip()]
_from_settings_urls = []
for candidate in (settings.frontend_home_url, settings.frontend_auth_redirect_url):
    parsed = urlparse(candidate or "")
    if parsed.scheme and parsed.netloc:
        _from_settings_urls.append(f"{parsed.scheme}://{parsed.netloc}")
origins = list(dict.fromkeys(_default_origins + _extra + _from_settings_urls))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT...
    allow_headers=["*"],   # Authorization, Content-Type...
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
def app_error_handler(_: Request, exc: AppError):
    return fail(exc.code, exc.message, exc.status_code)


@app.exception_handler(RequestValidationError)
def validation_error_handler(_: Request, exc: RequestValidationError):
    return fail("INVALID_PARAMETER", humanize_validation_errors(exc), 400)


@app.exception_handler(Exception)
def fallback_handler(_: Request, __: Exception):
    return fail("SCHEMA_VALIDATION_FAILED", "Đã xảy ra lỗi nội bộ", 500)


@app.exception_handler(OperationalError)
def db_unavailable_handler(_: Request, __: OperationalError):
    return fail("DATABASE_UNAVAILABLE", "Database is temporarily unavailable. Please retry shortly.", 503)


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
