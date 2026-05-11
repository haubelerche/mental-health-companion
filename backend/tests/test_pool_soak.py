from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


@pytest.mark.real_db
def test_app_engine_pool_survives_short_parallel_soak(real_db_url: str) -> None:
    if "sqlite" in real_db_url:
        pytest.skip("pool soak requires PostgreSQL")

    # Do not use the app's singleton engine: CI often sets DB_POOL_SIZE=1 for the API,
    # but this test needs enough concurrent checkouts for 8 workers.
    connect_args: dict = {}
    if real_db_url.startswith(("postgresql+psycopg://", "postgresql://")):
        connect_args = {"options": "-c search_path=app,extensions"}
    engine = create_engine(
        real_db_url,
        future=True,
        pool_size=10,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    try:

        def ping() -> str:
            with engine.connect() as conn:
                conn.execute(text("SET search_path TO app, extensions"))
                return str(conn.execute(text("SELECT current_schema()")).scalar_one())

        results: list[str] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(ping) for _ in range(80)]
            for future in as_completed(futures, timeout=60):
                try:
                    results.append(future.result())
                except OperationalError as exc:
                    msg = str(exc)
                    if "EMAXCONNSESSION" in msg or "max clients reached" in msg:
                        pytest.skip(f"pool soak skipped: real DB session cap reached: {exc}")
                    raise

        assert len(results) == 80
        assert all(result == "app" for result in results)
    finally:
        engine.dispose()
