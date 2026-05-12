"""Narrow repository for canonical Mem0-backed user memories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Mem0Memory:
    id: str
    content: str
    source: str | None
    created_at: str | None
    metadata: dict[str, Any]


def _memory_from_row(row: Any) -> Mem0Memory:
    payload = dict(row.metadata or {})
    content = str(row.content or "").strip()
    return Mem0Memory(
        id=str(row.id),
        content=content,
        source=str(row.source or "").strip() or None,
        created_at=str(row.created_at or "").strip() or None,
        metadata=payload,
    )


def list_user_memories(db: Session, *, user_id: str, limit: int = 100) -> list[Mem0Memory]:
    """List canonical vector memories owned by a user.

    Mem0 owns the table shape, so application code must only rely on the stable
    id and payload contract we write through MemoryManager.
    """
    rows = db.execute(
        text(
            """
            SELECT
                m.id::text AS id,
                COALESCE(
                    NULLIF(m.payload->>'data', ''),
                    NULLIF(m.payload->>'memory', ''),
                    NULLIF(m.payload->>'text', ''),
                    NULLIF(m.payload->>'content', '')
                ) AS content,
                NULLIF(m.payload->>'source', '') AS source,
                NULLIF(m.payload->>'created_at', '') AS created_at,
                COALESCE(m.payload, '{}'::jsonb) AS metadata
            FROM app.mem0_memories AS m
            WHERE m.payload->>'user_id' = :user_id
              AND COALESCE(
                    NULLIF(m.payload->>'data', ''),
                    NULLIF(m.payload->>'memory', ''),
                    NULLIF(m.payload->>'text', ''),
                    NULLIF(m.payload->>'content', '')
                ) IS NOT NULL
            ORDER BY NULLIF(m.payload->>'created_at', '') DESC, m.id::text DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": max(1, min(int(limit), 200))},
    ).all()
    return [_memory_from_row(row) for row in rows]


def delete_user_memory(db: Session, *, user_id: str, memory_id: str) -> bool:
    """Delete one memory only when it belongs to the authenticated user."""
    deleted_id = db.execute(
        text(
            """
            DELETE FROM app.mem0_memories AS m
            WHERE m.id::text = :memory_id
              AND m.payload->>'user_id' = :user_id
            RETURNING id
            """
        ),
        {"user_id": user_id, "memory_id": memory_id},
    ).scalar()
    return deleted_id is not None


def list_all_user_memories(db: Session, *, user_id: str, batch_size: int = 200, max_rows: int = 2000) -> list[Mem0Memory]:
    """Load all user memories in stable batches for analyst-grade aggregation."""
    out: list[Mem0Memory] = []
    fetched = 0
    step = max(1, min(int(batch_size), 500))
    hard_cap = max(step, min(int(max_rows), 5000))
    while fetched < hard_cap:
        rows = db.execute(
            text(
                """
                SELECT
                    m.id::text AS id,
                    COALESCE(
                        NULLIF(m.payload->>'data', ''),
                        NULLIF(m.payload->>'memory', ''),
                        NULLIF(m.payload->>'text', ''),
                        NULLIF(m.payload->>'content', '')
                    ) AS content,
                    NULLIF(m.payload->>'source', '') AS source,
                    NULLIF(m.payload->>'created_at', '') AS created_at,
                    COALESCE(m.payload, '{}'::jsonb) AS metadata
                FROM app.mem0_memories AS m
                WHERE m.payload->>'user_id' = :user_id
                  AND COALESCE(
                        NULLIF(m.payload->>'data', ''),
                        NULLIF(m.payload->>'memory', ''),
                        NULLIF(m.payload->>'text', ''),
                        NULLIF(m.payload->>'content', '')
                    ) IS NOT NULL
                ORDER BY NULLIF(m.payload->>'created_at', '') DESC, m.id::text DESC
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
