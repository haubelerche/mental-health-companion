from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import fail
from app.db.init_db import init_db

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup_event():
    if settings.auto_create_schema:
        init_db()


@app.exception_handler(AppError)
def app_error_handler(_: Request, exc: AppError):
    return fail(exc.code, exc.message, exc.status_code)


@app.exception_handler(RequestValidationError)
def validation_error_handler(_: Request, exc: RequestValidationError):
    return fail("INVALID_PARAMETER", str(exc.errors()), 400)


@app.exception_handler(Exception)
def fallback_handler(_: Request, __: Exception):
    return fail("SCHEMA_VALIDATION_FAILED", "Đã xảy ra lỗi nội bộ", 500)


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})
