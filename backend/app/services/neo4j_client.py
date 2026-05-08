"""Optional Neo4j driver — graph sync via outbox worker in production."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Any, TypedDict

from app.core.config import get_settings

_neo4j_log = logging.getLogger(__name__)


class UserPatternsResult(TypedDict):
    triggers: list[dict]
    emotions: list[dict]
    coping: list[dict]
    available: bool


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
    except Exception as _exc:
        _neo4j_log.warning("Neo4j driver init failed (uri=%s): %s", uri[:20], _exc)
        return None


def _query_user_patterns_sync(user_id: str, limit: int) -> UserPatternsResult:
    """Blocking Neo4j query — only call via asyncio.to_thread()."""
    try:
        driver = get_neo4j_driver()
        if driver is None:
            return {"triggers": [], "emotions": [], "coping": [], "available": False}
        from neo4j import READ_ACCESS
        with driver.session(default_access_mode=READ_ACCESS) as session:
            result = session.run(
                """
                MATCH (u:User {user_id: $uid})
                OPTIONAL MATCH (u)-[r1:EXPERIENCED]->(t:Trigger)
                OPTIONAL MATCH (u)-[r2:FELT]->(e:Emotion)
                OPTIONAL MATCH (u)-[r3:USED_COPING]->(c:CopingAction)
                RETURN
                  collect(DISTINCT {name: t.name, count: r1.count})[..$lim] AS triggers,
                  collect(DISTINCT {name: e.name, count: r2.count})[..$lim] AS emotions,
                  collect(DISTINCT {name: c.name, effectiveness: r3.effectiveness_avg})[..$lim] AS coping
                """,
                uid=user_id,
                lim=limit,
            )
            row = result.single()
            if row is None:
                return {"triggers": [], "emotions": [], "coping": [], "available": True}
            return {
                "triggers": [r for r in (row["triggers"] or []) if r.get("name")],
                "emotions": [r for r in (row["emotions"] or []) if r.get("name")],
                "coping": [r for r in (row["coping"] or []) if r.get("name")],
                "available": True,
            }
    except Exception as exc:
        _neo4j_log.warning("Neo4j pattern query failed user=%s: %s", user_id, exc)
        return {"triggers": [], "emotions": [], "coping": [], "available": False}


async def get_user_patterns_async(user_id: str, limit: int = 5) -> UserPatternsResult:
    """
    Non-blocking Neo4j user pattern query. Wraps sync driver via asyncio.to_thread().
    Returns empty dicts with available=False on any failure.
    """
    return await asyncio.to_thread(_query_user_patterns_sync, user_id, limit)
