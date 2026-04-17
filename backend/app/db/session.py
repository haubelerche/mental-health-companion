from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from functools import lru_cache

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass

@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    return create_engine(settings.normalized_database_url(), future=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session)


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
