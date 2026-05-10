"""Mem0 wrapper for hybrid long-term memory.

This service is intentionally fail-safe: Mem0 errors never break chat flows.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MEM0_SCHEMA = "app"
MEM0_COLLECTION_NAME = f"{MEM0_SCHEMA}.mem0_memories"


CLINICAL_MEMORY_PROMPT = """Bạn đang phân tích hội thoại từ ứng dụng hỗ trợ tâm lý (tiếng Việt).
Trích xuất MEMORY QUAN TRỌNG về người dùng:

CẦN LƯU:
- Tác nhân gây căng thẳng (trigger): công việc, gia đình, tài chính, sức khỏe, cô đơn
- Cảm xúc người dùng thể hiện rõ ràng
- Chiến lược đối phó đã thử (thở, đi bộ, viết nhật ký...)
- Mục tiêu cá nhân người dùng đề cập
- Mối quan hệ quan trọng (KHÔNG lưu tên thật - dùng \"người thân\", \"đồng nghiệp\")
- Sở thích giao tiếp (muốn lắng nghe / muốn giải pháp / muốn được hiểu)

KHÔNG LƯU: tên thật, số điện thoại, địa chỉ, nội dung SOS/khủng hoảng.
Mỗi memory: ngắn gọn tiếng Việt, dưới 80 từ.
"""


def _pgvector_config_from_database_url(database_url: str) -> dict[str, Any]:
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/") or "postgres"
    conn_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    conn_parsed = urlparse(conn_url)
    query = dict(parse_qsl(conn_parsed.query, keep_blank_values=True))
    query.setdefault("options", f"-c search_path={MEM0_SCHEMA},extensions")
    connection_string = urlunparse(conn_parsed._replace(query=urlencode(query)))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "dbname": db_name,
        "collection_name": MEM0_COLLECTION_NAME,
        "embedding_model_dims": 1536,
        "connection_string": connection_string,
    }


def get_mem0_config() -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    if "postgresql" not in settings.database_url:
        # Local SQLite mode: skip Mem0 and keep structured-only memory.
        return None

    vector_config = _pgvector_config_from_database_url(settings.database_url)
    config: dict[str, Any] = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": settings.openai_model_analyst or "gpt-4o-mini",
                "api_key": settings.openai_api_key,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": settings.openai_api_key,
            },
        },
        "vector_store": {
            "provider": "pgvector",
            "config": vector_config,
        },
        "custom_prompt": CLINICAL_MEMORY_PROMPT,
    }
    # MVP boundary: Mem0 may use PostgreSQL/pgvector memory, but must not write
    # user-derived memory to the Neo4j graph. Neo4j remains static/internal taxonomy only.
    return config


class MemoryManager:
    _instance: "MemoryManager | None" = None

    def __init__(self) -> None:
        self._client: Any | None = None
        self._enabled = False
        cfg = get_mem0_config()
        if cfg is None:
            return
        try:
            from mem0 import Memory

            self._client = Memory.from_config(cfg)
            self._enabled = True
        except Exception as exc:
            logger.warning("mem0 init failed, fallback to structured memory only: %s", exc)
            self._enabled = False

    @classmethod
    def instance(cls) -> "MemoryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_session(self, user_id: str, messages: list[dict[str, str]]) -> None:
        if not self._enabled or not self._client or not user_id or not messages:
            return
        try:
            self._client.add(messages, user_id=user_id, metadata={"source": "session_summary"})
        except Exception as exc:
            logger.warning("mem0 add_session failed for %s: %s", user_id, exc)

    def search(self, user_id: str, query: str, limit: int = 5) -> list[str]:
        if not self._enabled or not self._client or not user_id:
            return []
        try:
            results = self._client.search(query or "", user_id=user_id, limit=limit)
        except Exception as exc:
            logger.warning("mem0 search failed for %s: %s", user_id, exc)
            return []

        items = list((results or {}).get("results") or [])
        out: list[str] = []
        for item in items:
            text = str((item or {}).get("memory") or "").strip()
            if text:
                out.append(text)
        return out

    def delete_user(self, user_id: str) -> None:
        if not self._enabled or not self._client or not user_id:
            return
        try:
            if hasattr(self._client, "delete_all"):
                self._client.delete_all(user_id=user_id)
            elif hasattr(self._client, "delete"):
                self._client.delete(user_id=user_id)
        except Exception as exc:
            logger.warning("mem0 delete_user failed for %s: %s", user_id, exc)
