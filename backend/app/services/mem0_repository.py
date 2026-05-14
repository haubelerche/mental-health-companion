"""Narrow repository for optional Mem0-derived retrieval cache rows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.utils import get_now

_OWNER_EXPR = """
COALESCE(
    NULLIF(m.payload->>'user_id', ''),
    NULLIF(m.payload#>>'{metadata,user_id}', ''),
    NULLIF(m.payload#>>'{filters,user_id}', ''),
    NULLIF(m.payload#>>'{metadata,filters,user_id}', '')
)
"""

_CONTENT_EXPR = """
COALESCE(
    NULLIF(m.payload->>'data', ''),
    NULLIF(m.payload->>'memory', ''),
    NULLIF(m.payload->>'text', ''),
    NULLIF(m.payload->>'content', ''),
    NULLIF(m.payload#>>'{metadata,data}', ''),
    NULLIF(m.payload#>>'{metadata,memory}', ''),
    NULLIF(m.payload#>>'{metadata,text}', ''),
    NULLIF(m.payload#>>'{metadata,content}', '')
)
"""

_SOURCE_EXPR = """
COALESCE(
    NULLIF(m.payload->>'source', ''),
    NULLIF(m.payload#>>'{metadata,source}', '')
)
"""

_CREATED_AT_EXPR = """
COALESCE(
    NULLIF(m.payload->>'created_at', ''),
    NULLIF(m.payload#>>'{metadata,created_at}', ''),
    NULLIF(m.payload->>'created', ''),
    NULLIF(m.payload#>>'{metadata,created}', '')
)
"""


@dataclass(frozen=True)
class Mem0Memory:
    id: str
    content: str
    source: str | None
    created_at: str | None
    metadata: dict[str, Any]


def _memory_from_row(row: Any) -> Mem0Memory:
    payload = dict(row.metadata or {})
    owner = str(getattr(row, "user_id", "") or payload.get("user_id") or "").strip()
    if owner:
        payload["user_id"] = owner

    content = str(row.content or "").strip()
    user_name = str(payload.get("user_name") or "").strip()
    if user_name and content:
        content_lower = content.casefold()
        user_lower = user_name.casefold()
        if not content_lower.startswith(f"{user_lower} \u0111\u00e3 ") and not content_lower.startswith(f"{user_lower} da "):
            content = f"{user_name} \u0111\u00e3 {content}"

    return Mem0Memory(
        id=str(row.id),
        content=content,
        source=str(row.source or "").strip() or None,
        created_at=str(row.created_at or "").strip() or None,
        metadata=payload,
    )


def _is_sqlite(db: Session) -> bool:
    try:
        bind = db.get_bind()
    except Exception:
        bind = getattr(db, "bind", None)
    return str(getattr(getattr(bind, "dialect", None), "name", "")).lower() == "sqlite"


def list_user_memories(db: Session, *, user_id: str, limit: int = 100) -> list[Mem0Memory]:
    """List derived vector-cache memories owned by a user.

    User-visible memory must be served from app.memory_cards. This helper is
    retained only for bounded recall fallback and diagnostics.
    """
    if _is_sqlite(db):
        return []

    rows = db.execute(
        text(
            f"""
            SELECT
                m.id::text AS id,
                {_OWNER_EXPR} AS user_id,
                {_CONTENT_EXPR} AS content,
                {_SOURCE_EXPR} AS source,
                {_CREATED_AT_EXPR} AS created_at,
                COALESCE(m.payload, '{{}}'::jsonb) AS metadata
            FROM app.mem0_memories AS m
            WHERE {_OWNER_EXPR} = :user_id
              AND {_CONTENT_EXPR} IS NOT NULL
            ORDER BY {_CREATED_AT_EXPR} DESC NULLS LAST, m.id::text DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": max(1, min(int(limit), 200))},
    ).all()
    return [_memory_from_row(row) for row in rows]


def delete_user_memory(db: Session, *, user_id: str, memory_id: str) -> bool:
    """Delete one memory only when it belongs to the authenticated user."""
    if _is_sqlite(db):
        return False

    deleted_id = db.execute(
        text(
            f"""
            DELETE FROM app.mem0_memories AS m
            WHERE m.id::text = :memory_id
              AND {_OWNER_EXPR} = :user_id
            RETURNING id
            """
        ),
        {"user_id": user_id, "memory_id": memory_id},
    ).scalar()
    return deleted_id is not None


def ensure_session_summary_memory(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    summary_text: str,
    created_at: str | None = None,
) -> str | None:
    """Legacy helper for derived mem0 cache rows; not user-visible canonical memory."""
    if _is_sqlite(db):
        return None

    safe_user_id = str(user_id or "").strip()
    safe_session_id = str(session_id or "").strip()
    safe_summary = " ".join(str(summary_text or "").split()).strip()
    if not safe_user_id or not safe_session_id or not safe_summary:
        return None

    existing_id = db.execute(
        text(
            f"""
            SELECT m.id::text
            FROM app.mem0_memories AS m
            WHERE {_OWNER_EXPR} = :user_id
              AND NULLIF(m.payload->>'session_id', '') = :session_id
              AND {_SOURCE_EXPR} = 'session_summary'
            ORDER BY {_CREATED_AT_EXPR} DESC NULLS LAST, m.id::text DESC
            LIMIT 1
            """
        ),
        {"user_id": safe_user_id, "session_id": safe_session_id},
    ).scalar()
    if existing_id:
        return str(existing_id)

    memory_id = str(uuid4())
    payload = {
        "user_id": safe_user_id,
        "data": safe_summary[:700],
        "source": "session_summary",
        "created_at": created_at or get_now().isoformat(),
        "session_id": safe_session_id,
        "summary": safe_summary[:700],
    }
    db.execute(
        text(
            """
            INSERT INTO app.mem0_memories (id, payload)
            VALUES (CAST(:id AS uuid), CAST(:payload AS jsonb))
            """
        ),
        {"id": memory_id, "payload": json.dumps(payload, ensure_ascii=False)},
    )
    return memory_id


def list_all_user_memories(db: Session, *, user_id: str, batch_size: int = 200, max_rows: int = 2000) -> list[Mem0Memory]:
    """Load all user memories in stable batches for analyst-grade aggregation."""
    if _is_sqlite(db):
        return []

    out: list[Mem0Memory] = []
    fetched = 0
    step = max(1, min(int(batch_size), 500))
    hard_cap = max(step, min(int(max_rows), 5000))
    while fetched < hard_cap:
        rows = db.execute(
            text(
                f"""
                SELECT
                    m.id::text AS id,
                    {_OWNER_EXPR} AS user_id,
                    {_CONTENT_EXPR} AS content,
                    {_SOURCE_EXPR} AS source,
                    {_CREATED_AT_EXPR} AS created_at,
                    COALESCE(m.payload, '{{}}'::jsonb) AS metadata
                FROM app.mem0_memories AS m
                WHERE {_OWNER_EXPR} = :user_id
                  AND {_CONTENT_EXPR} IS NOT NULL
                ORDER BY {_CREATED_AT_EXPR} DESC NULLS LAST, m.id::text DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"user_id": user_id, "limit": step, "offset": fetched},
        ).all()
        if not rows:
            break
        out.extend(_memory_from_row(row) for row in rows)
        fetched += len(rows)
        if len(rows) < step:
            break
    return out[:hard_cap]
