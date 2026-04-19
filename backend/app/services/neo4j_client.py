"""Optional Neo4j driver — graph sync via outbox worker in production."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_neo4j_driver() -> Any | None:
    settings = get_settings()
    uri = getattr(settings, "neo4j_uri", "") or ""
    if not uri:
        return None
    try:
        from neo4j import GraphDatabase

        password = (getattr(settings, "neo4j_password", "") or "").strip()
        user = (getattr(settings, "neo4j_user", "neo4j") or "neo4j").strip()
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception:
        return None
