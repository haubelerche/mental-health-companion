from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from functools import lru_cache

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass

@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    database_url = settings.normalized_database_url()
    if database_url.startswith(("postgresql+psycopg://", "postgresql://")):
        return create_engine(
            database_url,
            future=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
            pool_pre_ping=settings.db_pool_pre_ping,
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
