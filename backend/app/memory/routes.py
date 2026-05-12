"""Canonical user memory API backed by app.mem0_memories."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import User
from app.services.db.session import get_db
from app.services.mem0_repository import Mem0Memory, delete_user_memory, list_user_memories
from app.services.observability import record_event, record_metric

router = APIRouter(prefix="/chat/memories", tags=["memory"])


class UserMemoryOut(BaseModel):
    memory_id: str = Field(..., description="Canonical app.mem0_memories row id.")
    content: str
    source: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_memory(cls, memory: Mem0Memory) -> "UserMemoryOut":
        return cls(
            memory_id=memory.id,
            content=memory.content,
            source=memory.source,
            created_at=memory.created_at,
            metadata=memory.metadata,
        )


@router.get("", summary="List canonical user memories")
def list_memories(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: User = Depends(ensure_policy_acknowledged),
) -> Any:
    memories = list_user_memories(db, user_id=current_user.user_id, limit=limit)
    safe_memories: list[Mem0Memory] = []
    for memory in memories:
        owner = str(memory.metadata.get("user_id") or "").strip()
        if owner and owner != current_user.user_id:
            record_metric("memory_owner_mismatch_total", 1, labels={"operation": "list"})
            record_event("memory.owner_mismatch", metadata={"operation": "list", "reason_code": "owner_mismatch"})
            continue
        safe_memories.append(memory)
    return ok({"memories": [UserMemoryOut.from_memory(memory) for memory in safe_memories]})


@router.delete("/{memory_id}", summary="Delete one canonical user memory")
def delete_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _policy: User = Depends(ensure_policy_acknowledged),
    _csrf: None = Depends(require_csrf),
) -> Any:
    deleted = delete_user_memory(db, user_id=current_user.user_id, memory_id=memory_id)
    if not deleted:
        raise AppError("MEMORY_NOT_FOUND", "Không tìm thấy ký ức hoặc bạn không có quyền xoá.", 404)
    db.commit()
    return ok({"deleted": True, "memory_id": memory_id})
