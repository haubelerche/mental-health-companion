"""Deterministic atomic memory-card candidate extraction.

One candidate is one compact, user-facing fact/preference/pattern about the
user. Session summaries and analyst notes are intentionally out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MemoryType = Literal[
    "background",
    "support_style",
    "current_stressor",
    "coping_history",
    "preference",
    "persona_preference",
    "nutrition_pattern",
    "temporary_context",
    # Extended types for richer user-facing memory
    "event_memory",
    "support_insight",
    "relationship_context",
    "goal_or_hope",
    "emotional_pattern",
]

SensitivityLevel = Literal["low", "medium", "high"]


@dataclass(slots=True)
class AtomicMemoryCandidate:
    memory_type: MemoryType
    display_category: str
    subject: str
    predicate: str
    display_text: str
    confidence: float
    is_temporary: bool = False
    ttl_days: int | None = None
    evidence_message_ids: list[str] = field(default_factory=list)
    source_session_id: str | None = None
    sensitivity_level: SensitivityLevel = "low"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.display_category

    @property
    def content(self) -> str:
        return self.display_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_type": self.memory_type,
            "display_category": self.display_category,
            "subject": self.subject,
            "predicate": self.predicate,
            "display_text": self.display_text,
            "title": self.display_category,
            "content": self.display_text,
            "confidence": self.confidence,
            "is_temporary": self.is_temporary,
            "ttl_days": self.ttl_days,
            "evidence_message_ids": list(self.evidence_message_ids),
            "source_session_id": self.source_session_id,
            "sensitivity_level": self.sensitivity_level,
            "metadata": dict(self.metadata),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


class MemoryCandidate(AtomicMemoryCandidate):
    """Backward-compatible candidate shape for older callers/tests.

    New code should construct AtomicMemoryCandidate directly.
    """

    def __init__(
        self,
        *,
        memory_type: str,
        title: str,
        content: str,
        confidence: float = 0.7,
        source_session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            memory_type=memory_type,  # type: ignore[arg-type]
            display_category=title,
            subject=str((metadata or {}).get("subject") or title) if isinstance(metadata, dict) else title,
            predicate=str((metadata or {}).get("predicate") or content) if isinstance(metadata, dict) else content,
            display_text=content,
            confidence=confidence,
            is_temporary=bool((metadata or {}).get("is_temporary")) if isinstance(metadata, dict) else False,
            ttl_days=(metadata or {}).get("ttl_days") if isinstance(metadata, dict) else None,
            evidence_message_ids=list((metadata or {}).get("evidence_message_ids") or []) if isinstance(metadata, dict) else [],
            source_session_id=source_session_id,
            sensitivity_level=str((metadata or {}).get("sensitivity_level") or "low"),  # type: ignore[arg-type]
            metadata=dict(metadata or {}),
        )


@dataclass(slots=True)
class ExtractionResult:
    candidate_cards: list[AtomicMemoryCandidate] = field(default_factory=list)

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
    candidates: list[AtomicMemoryCandidate] = []
    seen_keys: set[tuple[str, str, str]] = set()

    def add(
        memory_type: MemoryType,
        display_category: str,
        subject: str,
        predicate: str,
        display_text: str,
        *,
        confidence: float = 0.72,
        is_temporary: bool = False,
        ttl_days: int | None = None,
    ) -> None:
        key = (memory_type, subject.lower().strip(), predicate.lower().strip())
        if key in seen_keys:
            return
        seen_keys.add(key)
        candidates.append(
            AtomicMemoryCandidate(
                memory_type=memory_type,
                display_category=display_category,
                subject=subject,
                predicate=predicate,
                display_text=display_text[:160].strip(),
                confidence=confidence,
                is_temporary=is_temporary,
                ttl_days=ttl_days,
                source_session_id=session_id,
                sensitivity_level="low",
                metadata={"extractor": "deterministic_atomic_v1"},
            )
        )

    if _contains_any(lowered, ("đi bộ", "di bo", "hít thở", "hit tho", "thở sâu", "tho sau", "nhẹ hơn", "nhe hon")):
        add(
            "coping_history",
            "Điều từng giúp bạn",
            "di_bo_hit_tho",
            "giup_diu_lai",
            "Bạn từng thấy đi bộ hoặc hít thở chậm giúp đầu óc dịu lại.",
        )

    if _contains_any(lowered, ("deadline", "áp lực", "ap luc", "stress", "thi cử", "thi cu", "công việc", "cong viec")):
        add(
            "current_stressor",
            "Điều đang áp lực",
            "deadline_cong_viec_hoc_tap",
            "de_cang_thang",
            "Bạn từng nói deadline, học tập hoặc công việc khiến bạn dễ căng thẳng.",
            confidence=0.68,
            is_temporary=True,
            ttl_days=30,
        )

    if _contains_any(lowered, ("trả lời ngắn", "tra loi ngan", "ít chữ", "it chu", "ngắn gọn", "ngan gon")):
        add(
            "support_style",
            "Cách hỗ trợ",
            "cau_tra_loi_ngan",
            "hop_khi_met",
            "Bạn thích Serene trả lời ngắn gọn khi bạn đang mệt.",
        )

    if _contains_any(lowered, ("làm việc ở nhà", "lam viec o nha", "work from home", "wfh")):
        add(
            "background",
            "Bối cảnh",
            "noi_lam_viec",
            "lam_viec_o_nha",
            "Bạn làm việc ở nhà.",
            confidence=0.78,
        )

    return ExtractionResult(candidate_cards=candidates)
