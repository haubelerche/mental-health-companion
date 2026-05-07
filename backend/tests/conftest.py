"""Pytest setup for backend/tests: PYTHONPATH, repo-root .env, collection rules."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

_THIS = Path(__file__).resolve().parent
_BACKEND_ROOT = _THIS.parent
_REPO_ROOT = _BACKEND_ROOT.parent

# `app.*` resolves from backend/; `scripts.*` from repo root.
for _p in (_BACKEND_ROOT, _REPO_ROOT):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# Fail-open Redis-backed limits for the whole pytest process (see rate_limit.get_rate_limiter).
os.environ.setdefault("SERENE_BACKEND_TESTING", "1")
os.environ.setdefault("JWT_DEV_SECRET", "serene-test-jwt-secret-123")
try:
    from app.services import rate_limit as _rate_limit_mod

    _rate_limit_mod.get_rate_limiter.cache_clear()
except Exception:
    pass

# Manual wire script (imports legacy paths); not a pytest suite.
collect_ignore = ["test_db.py"]


def pytest_configure(config: pytest.Config) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_REPO_ROOT / ".env", override=False)


class _NoOpAuthRateLimiter:
    """Integration tests share one TestClient IP; Redis-backed signup limits → flaky 429."""

    def enforce_per_minute(self, *args: object, **kwargs: object) -> None:
        return

    def enforce_auth_lockout(self, *args: object, **kwargs: object) -> None:
        return

    def record_auth_failure(self, *args: object, **kwargs: object) -> None:
        return

    def clear_auth_failure(self, *args: object, **kwargs: object) -> None:
        return


@pytest.fixture(scope="session", autouse=True)
def _disable_auth_router_rate_limit_for_test_session() -> None:
    """Patch auth router limiter for the whole suite so order vs Redis does not flake CI."""
    from app.api.v1.routers import auth as auth_module

    with patch.object(auth_module, "get_rate_limiter", lambda: _NoOpAuthRateLimiter()):
        yield


@pytest.fixture(scope="session")
def real_db_url() -> str:
    """Skip if DATABASE_URL is not set or points to SQLite."""
    url = os.environ.get("DATABASE_URL", "")
    if not url or "sqlite" in url:
        pytest.skip("DATABASE_URL not set (or SQLite) - skipping real-db integration tests")
    return url


@pytest.fixture(scope="session")
def real_engine(real_db_url: str):
    engine = create_engine(
        real_db_url,
        connect_args={"options": "-c search_path=app,public,extensions", "connect_timeout": 15},
        poolclass=NullPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture
def real_db(real_engine):
    SessionLocal = sessionmaker(bind=real_engine)
    session = SessionLocal()
    opened = False
    try:
        try:
            session.execute(text("SET search_path TO app, public, extensions"))
            opened = True
        except OperationalError as exc:
            session.close()
            if "EMAXCONNSESSION" in str(exc) or "max clients reached" in str(exc):
                pytest.skip(f"real DB unavailable: Supabase session pool exhausted: {exc}")
            raise
        yield session
    finally:
        if opened:
            session.rollback()
            session.close()
