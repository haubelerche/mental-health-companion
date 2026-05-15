import logging
import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass

@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    database_url = settings.normalized_database_url()
    if database_url.startswith(("postgresql+psycopg://", "postgresql://")):
        parsed = urlparse(database_url)
        host = (parsed.hostname or "").lower()
        port = parsed.port or 5432

        pool_size = max(1, int(settings.db_pool_size))
        max_overflow = max(0, int(settings.db_max_overflow))

        if "supabase.com" in host:
            # Supabase exposes two poolers on different ports:
            #   5432 = session pooler  (PgBouncer session mode)  — free tier: 15 client slots
            #   6543 = transaction pooler (PgBouncer transaction mode) — free tier: many more
            #
            # Session pooler: each SQLAlchemy connection in the pool permanently
            # occupies one slot even when idle. With a 15-slot cap, a pool_size=5
            # app + any dev tooling is enough to trigger EMAXCONNSESSION errors.
            # Cap the pool aggressively so we leave headroom for other clients.
            #
            # Transaction pooler: connections are released between transactions so
            # the slot count never exceeds the number of in-flight transactions.
            # A larger pool is fine there.
            if port == 5432:
                # Session pooler — free-tier cap is 15 slots shared across ALL
                # clients (app, migrations, dev tools, outbox worker).  The old
                # code bumped pool_size to 5+overflow=2 = 7 connections, which
                # pushes the total above 15 under light concurrent usage.
                # Fix: enforce a hard ceiling of pool_size=4, max_overflow=1
                # regardless of env settings, leaving ≥10 slots for everything else.
                #
                # Recommended fix: switch DATABASE_URL port to 6543 (transaction
                # pooler) — connections are released between transactions and the
                # slot limit becomes irrelevant for most workloads.
                pool_size = 4
                max_overflow = 1
                logger.warning(
                    "Supabase SESSION pooler detected (port 5432). "
                    "Pool hard-capped at pool_size=%s max_overflow=%s to avoid EMAXCONNSESSION. "
                    "Switch DATABASE_URL to port 6543 (transaction pooler) for better throughput.",
                    pool_size,
                    max_overflow,
                )
            else:
                # Transaction pooler (port 6543) — more generous cap.
                soft_cap = 12
                pool_size = max(pool_size, 5)
                max_overflow = max(max_overflow, 3)
                if pool_size + max_overflow > soft_cap:
                    max_overflow = max(0, soft_cap - pool_size)
                logger.info(
                    "Supabase transaction pooler detected. "
                    "db pool: pool_size=%s max_overflow=%s",
                    pool_size,
                    max_overflow,
                )

        return create_engine(
            database_url,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
            pool_pre_ping=settings.db_pool_pre_ping,
            pool_use_lifo=True,
            connect_args={"options": "-c search_path=app,extensions"},
        )
    engine = create_engine(database_url, future=True)
    if engine.dialect.name == "sqlite":
        # SQLite has no PostgreSQL-style schemas. Some production models are
        # schema-qualified as `app.*`; translate that schema away for local
        # auto-created SQLite databases so dev startup can still create tables.
        return engine.execution_options(schema_translate_map={"app": None})
    return engine


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
