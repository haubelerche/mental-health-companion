"""Deterministic memory-card candidate extraction.

This keeps legacy memory-card imports working while canonical long-term memory
continues to live in mem0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MemoryType = Literal[
    "preference",
    "emotional_pattern",
    "coping_history",
    "current_stressor",
    "nutrition_pattern",
    "kindness_pattern",
    "persona_preference",
]


@dataclass(slots=True)
class MemoryCandidate:
    memory_type: MemoryType
    title: str
    content: str
    confidence: float = 0.7
    source_session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "confidence": self.confidence,
            "source_session_id": self.source_session_id,
            "metadata": dict(self.metadata),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass(slots=True)
class ExtractionResult:
    candidate_cards: list[MemoryCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_cards": [candidate.to_dict() for candidate in self.candidate_cards]}

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_memory_candidates(text: str, *, session_id: str | None = None) -> ExtractionResult:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ExtractionResult()

    lowered = cleaned.lower()
    candidates: list[MemoryCandidate] = []
    seen_types: set[str] = set()

    def add(memory_type: MemoryType, title: str, content: str, confidence: float = 0.72) -> None:
        if memory_type in seen_types:
            return
        seen_types.add(memory_type)
        candidates.append(
            MemoryCandidate(
                memory_type=memory_type,
                title=title,
                content=content[:280],
                confidence=confidence,
                source_session_id=session_id,
                metadata={"extractor": "deterministic_v1"},
            )
        )

    if _contains_any(lowered, ("đi bộ", "di bo", "hít thở", "hit tho", "thở sâu", "tho sau", "nhẹ hơn", "nhe hon")):
        add("coping_history", "Cách đối phó từng giúp ích", "Đi bộ, hít thở hoặc một hoạt động nhẹ từng giúp bạn dịu lại.")

    if _contains_any(lowered, ("deadline", "áp lực", "ap luc", "stress", "thi cử", "thi cu", "công việc", "cong viec")):
        add("current_stressor", "Tác nhân gây căng thẳng hiện tại", "Deadline, học tập hoặc công việc đang là nguồn áp lực đáng chú ý.")

    if _contains_any(lowered, ("trả lời ngắn", "tra loi ngan", "ít chữ", "it chu", "ngắn gọn", "ngan gon")):
        add("preference", "Sở thích phản hồi", "Bạn có xu hướng thích câu trả lời ngắn gọn và trực tiếp.")

    return ExtractionResult(candidate_cards=candidates)
