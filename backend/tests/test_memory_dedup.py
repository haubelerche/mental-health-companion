"""Unit tests for mention_count dedup helpers in mem0_service.

Pure unit tests — no DB, no network, no external services required.
"""

from __future__ import annotations

import pytest

from app.services.mem0_repository import Mem0Memory
from app.services.mem0_service import (
    get_mention_count,
    is_likely_duplicate,
    record_memory_with_dedup,
    with_incremented_mention_count,
)


def _mem(content: str, metadata: dict | None = None, id: str = "test-id") -> Mem0Memory:
    return Mem0Memory(
        id=id,
        content=content,
        source=None,
        created_at=None,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# get_mention_count
# ---------------------------------------------------------------------------

def test_get_mention_count_defaults_to_one() -> None:
    m = Mem0Memory(id="x", content="test", source=None, created_at=None, metadata={})
    assert get_mention_count(m) == 1


def test_get_mention_count_reads_from_metadata() -> None:
    m = Mem0Memory(id="x", content="test", source=None, created_at=None, metadata={"mention_count": 5})
    assert get_mention_count(m) == 5


# ---------------------------------------------------------------------------
# is_likely_duplicate
# ---------------------------------------------------------------------------

def test_is_likely_duplicate_exact_match() -> None:
    assert is_likely_duplicate("mình tên là Hậu", "mình tên là Hậu") is True


def test_is_likely_duplicate_case_insensitive() -> None:
    assert is_likely_duplicate("Tên Là Hậu", "tên là hậu") is True


def test_is_likely_duplicate_different_content() -> None:
    assert is_likely_duplicate("tên là Hậu", "làm việc ở Hà Nội") is False


# ---------------------------------------------------------------------------
# record_memory_with_dedup
# ---------------------------------------------------------------------------

def test_record_memory_with_dedup_new_memory() -> None:
    action, count = record_memory_with_dedup(
        existing_memories=[],
        new_content="mình là AI engineer",
    )
    assert action == "new_memory"
    assert count == 1


def test_record_memory_with_dedup_duplicate_skipped() -> None:
    existing = [_mem("mình là AI engineer")]
    action, count = record_memory_with_dedup(
        existing_memories=existing,
        new_content="mình là AI engineer",
    )
    assert action == "duplicate_skipped"
    assert count == 2


def test_record_memory_with_dedup_distinct_facts_not_merged() -> None:
    existing = [
        _mem("mình là AI engineer", id="id-1"),
        _mem("làm việc ở Hà Nội", id="id-2"),
    ]
    action, count = record_memory_with_dedup(
        existing_memories=existing,
        new_content="thích cà phê buổi sáng",
    )
    assert action == "new_memory"
    assert count == 1


# ---------------------------------------------------------------------------
# with_incremented_mention_count
# ---------------------------------------------------------------------------

def test_with_incremented_mention_count_from_one() -> None:
    m = _mem("some content", metadata={})
    updated = with_incremented_mention_count(m)
    assert updated["mention_count"] == 2


def test_with_incremented_mention_count_from_three() -> None:
    m = _mem("some content", metadata={"mention_count": 3})
    updated = with_incremented_mention_count(m)
    assert updated["mention_count"] == 4
