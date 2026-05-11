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
    payload = dict(row.payload or {})
    content = str(
        payload.get("data")
        or payload.get("memory")
        or payload.get("text")
        or payload.get("content")
        or ""
    ).strip()
    return Mem0Memory(
        id=str(row.id),
        content=content,
        source=str(payload.get("source") or "").strip() or None,
        created_at=str(payload.get("created_at") or "").strip() or None,
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
            SELECT id::text AS id, payload
            FROM app.mem0_memories
            WHERE payload->>'user_id' = :user_id
              AND COALESCE(payload->>'data', payload->>'memory', payload->>'text', payload->>'content', '') <> ''
            ORDER BY COALESCE(payload->>'created_at', '') DESC, id::text DESC
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
            DELETE FROM app.mem0_memories
            WHERE id::text = :memory_id
              AND payload->>'user_id' = :user_id
            RETURNING id
            """
        ),
        {"user_id": user_id, "memory_id": memory_id},
    ).scalar()
    return deleted_id is not None
