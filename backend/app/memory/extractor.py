"""Memory candidate extractor — Plan 06.

Called after a conversation session ends. Returns candidate MemoryCard dicts
that the guardrail will review before persistence.

Design: This module defines the stable interface and a deterministic rule-based
reference implementation. A full LLM-backed extractor can be swapped in by
replacing `extract_memory_candidates` while keeping the same return type.

Return schema matches the plan contract:
{
  "candidate_cards": [
    {
      "memory_type": str,
      "title": str,
      "content": str,
      "confidence": float,
      "source_session_id": str | None,
      "metadata": dict,
    }
  ]
}
"""

from __future__ import annotations

import re
from typing import TypedDict


class MemoryCandidate(TypedDict):
    memory_type: str
    title: str
    content: str
    confidence: float
    source_session_id: str | None
    metadata: dict


class ExtractionResult(TypedDict):
    candidate_cards: list[MemoryCandidate]


# ---------------------------------------------------------------------------
# Rule-based signal patterns (reference implementation)
# ---------------------------------------------------------------------------

_PREFERENCE_SIGNALS = [
    (r"(thích|prefer).{0,40}(ngắn|brief|short)", "preference",
     "Bạn thích câu trả lời ngắn gọn.", 0.7),
    (r"(thích|prefer).{0,40}(tối|buổi tối|đêm)", "preference",
     "Bạn hay nhắn tin vào buổi tối.", 0.65),
]

_COPING_SIGNALS = [
    (r"(đi bộ|bước đi|walk).{0,30}(giúp|nhẹ|better)", "coping_history",
     "Đi bộ ngắn từng giúp bạn cảm thấy nhẹ hơn.", 0.75),
    (r"(hít thở|thở sâu|breathing).{0,30}(bình tĩnh|calm|nhẹ)", "coping_history",
     "Hít thở sâu giúp bạn bình tĩnh lại.", 0.7),
]

_STRESSOR_SIGNALS = [
    (r"(deadline|bài nộp|nộp bài|áp lực|pressure).{0,60}", "current_stressor",
     "Bạn đang có áp lực về deadline hoặc bài nộp.", 0.6),
    (r"(thi|exam|kiểm tra).{0,50}(stress|lo|mệt)", "current_stressor",
     "Bạn đang lo lắng về bài thi sắp tới.", 0.6),
]

_PERSONA_SIGNALS = [
    (r"(người thầy|nguoi_thay|mentor).{0,30}(giúp|thích|hay|good)", "persona_preference",
     "Bạn thích chọn Người Thầy khi cần suy nghĩ rõ ràng hơn.", 0.65),
]

_ALL_SIGNALS = _PREFERENCE_SIGNALS + _COPING_SIGNALS + _STRESSOR_SIGNALS + _PERSONA_SIGNALS


def extract_memory_candidates(
    session_text: str,
    session_id: str | None = None,
) -> ExtractionResult:
    """Extract candidate memory cards from a session transcript.

    Args:
        session_text: Full concatenated text of user messages in the session.
        session_id: Optional session identifier stored on each candidate.

    Returns:
        ExtractionResult with a list of candidate cards.
    """
    if not session_text or not session_text.strip():
        return ExtractionResult(candidate_cards=[])

    candidates: list[MemoryCandidate] = []
    seen_types: set[str] = set()

    for pattern, mem_type, content, confidence in _ALL_SIGNALS:
        if mem_type in seen_types:
            continue
        if re.search(pattern, session_text, re.IGNORECASE):
            candidates.append(
                MemoryCandidate(
                    memory_type=mem_type,
                    title=_default_title(mem_type),
                    content=content,
                    confidence=confidence,
                    source_session_id=session_id,
                    metadata={},
                )
            )
            seen_types.add(mem_type)

    return ExtractionResult(candidate_cards=candidates)


def _default_title(memory_type: str) -> str:
    return {
        "preference": "Sở thích của bạn",
        "emotional_pattern": "Cảm xúc của bạn",
        "coping_history": "Cách bạn từng vượt qua",
        "current_stressor": "Áp lực hiện tại",
        "nutrition_pattern": "Thói quen ăn uống",
        "kindness_pattern": "Lòng tốt của bạn",
        "persona_preference": "Phong cách hỗ trợ bạn thích",
    }.get(memory_type, "Ký ức")
