"""Regression tests for canonical mem0-backed memory routes.

This file must not import retired ORM models (`MemoryCard`, `MemoryCardAuditEvent`).
Those tables were retired and should never be required for test collection.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.errors import AppError
from app.core.responses import fail
from app.memory.routes import router
from app.services.db.models import User
from app.services.db.session import get_db
from app.services.mem0_repository import Mem0Memory


def _user(user_id: str = "usr_mem_test") -> User:
    return User(
        user_id=user_id,
        display_name="Memory Tester",
        email=f"{user_id}@example.com",
        password_hash="x",
        is_active=True,
        policy_acknowledged_at=datetime.now(UTC).replace(tzinfo=None),
    )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    class FakeDb:
        def commit(self) -> None:
            return None

    @app.exception_handler(AppError)
    def app_error_handler(_, exc: AppError):
        return fail(exc.code, exc.message, exc.status_code)

    app.dependency_overrides[get_db] = lambda: FakeDb()
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[ensure_policy_acknowledged] = lambda: _user()
    app.dependency_overrides[require_csrf] = lambda: None
    return TestClient(app)


def test_list_memories_returns_only_repository_results(monkeypatch):
    seen: dict[str, object] = {}

    def fake_list(db, *, user_id: str, limit: int):
        seen.update({"db": db, "user_id": user_id, "limit": limit})
        return [
            Mem0Memory(
                id="075f7d87-cb7d-4e8b-a687-6aa21e5cde2e",
                content="User likes concise supportive replies.",
                source="session_summary",
                created_at="2026-05-10T00:00:00Z",
                metadata={"user_id": user_id, "data": "User likes concise supportive replies."},
            )
        ]

    monkeypatch.setattr("app.memory.routes.list_user_memories", fake_list)

    response = _client().get("/chat/memories?limit=10")

    assert response.status_code == 200
    body = response.json()["data"]
    assert seen["user_id"] == "usr_mem_test"
    assert seen["limit"] == 10
    assert body["memories"][0]["memory_id"] == "075f7d87-cb7d-4e8b-a687-6aa21e5cde2e"
    assert body["memories"][0]["content"] == "User likes concise supportive replies."


def test_delete_memory_uses_authenticated_user_for_authorization(monkeypatch):
    calls: list[dict[str, str]] = []

    def fake_delete(db, *, user_id: str, memory_id: str) -> bool:
        calls.append({"user_id": user_id, "memory_id": memory_id})
        return user_id == "usr_mem_test" and memory_id == "mem_allowed"

    monkeypatch.setattr("app.memory.routes.delete_user_memory", fake_delete)
    client = _client()

    ok_response = client.delete("/chat/memories/mem_allowed")
    denied_response = client.delete("/chat/memories/mem_foreign")

    assert ok_response.status_code == 200
    assert ok_response.json()["data"] == {"deleted": True, "memory_id": "mem_allowed"}
    assert denied_response.status_code == 404
    assert calls == [
        {"user_id": "usr_mem_test", "memory_id": "mem_allowed"},
        {"user_id": "usr_mem_test", "memory_id": "mem_foreign"},
    ]
