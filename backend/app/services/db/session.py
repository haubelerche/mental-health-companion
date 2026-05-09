import logging
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
        # Supabase session pooler can have a very small project-level client cap.
        # Keep the application pool below that cap because background workers share
        # the same singleton engine with request handlers.
        if "supabase.com" in host:
            soft_cap = 3
            if pool_size > soft_cap:
                pool_size = soft_cap
                max_overflow = 0
            elif pool_size + max_overflow > soft_cap:
                max_overflow = max(0, soft_cap - pool_size)
            logger.info(
                "db pool capped for supabase session pooler: pool_size=%s max_overflow=%s",
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
            connect_args={"options": "-c search_path=app,public,extensions"},
        )
    return create_engine(database_url, future=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
