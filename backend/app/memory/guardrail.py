"""Memory guardrail — deterministic safety review for candidate cards.

Rules (plan 06):
- No diagnosis language (DSM disorder names, "bạn bị", "bạn mắc").
- No highly sensitive / SOS-level content.
- Content must be concise (≤ 300 chars) and reviewable.
- Title must be non-empty and ≤ 120 chars.
- Confidence must be in [0.0, 1.0] when provided.
"""

from __future__ import annotations

import re
from typing import TypedDict

DIAGNOSIS_PATTERNS = [
    r"\b(trầm cảm|rối loạn|tâm thần|hoang tưởng|tự kỷ|ám ảnh|lo âu rối loạn)\b",
    r"\bbạn (bị|mắc|có)\b.{0,30}(rối loạn|disorder|syndrome|phobia)",
    r"\b(depression|anxiety disorder|OCD|PTSD|bipolar|schizophrenia)\b",
]

SOS_PATTERNS = [
    r"\b(tự tử|tự làm hại|muốn chết|kết thúc cuộc sống|suicide|self.harm|kill (myself|yourself))\b",
]

MAX_CONTENT_CHARS = 300
MAX_TITLE_CHARS = 120

VALID_TYPES = {
    "preference",
    "emotional_pattern",
    "coping_history",
    "current_stressor",
    "nutrition_pattern",
    "kindness_pattern",
    "persona_preference",
}


class GuardrailResult(TypedDict):
    approved: bool
    rejection_reason: str | None


def review_memory_candidate(
    memory_type: str,
    title: str,
    content: str,
    confidence: float | None = None,
) -> GuardrailResult:
    """Return approved=True if the candidate passes all guardrail rules."""
    if memory_type not in VALID_TYPES:
        return GuardrailResult(approved=False, rejection_reason="invalid_memory_type")

    if not title or not title.strip():
        return GuardrailResult(approved=False, rejection_reason="empty_title")

    if len(title) > MAX_TITLE_CHARS:
        return GuardrailResult(approved=False, rejection_reason="title_too_long")

    if not content or not content.strip():
        return GuardrailResult(approved=False, rejection_reason="empty_content")

    if len(content) > MAX_CONTENT_CHARS:
        return GuardrailResult(approved=False, rejection_reason="content_too_long")

    if confidence is not None and not (0.0 <= confidence <= 1.0):
        return GuardrailResult(approved=False, rejection_reason="invalid_confidence")

    text = f"{title} {content}".lower()

    for pattern in SOS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return GuardrailResult(approved=False, rejection_reason="sos_content")

    for pattern in DIAGNOSIS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return GuardrailResult(approved=False, rejection_reason="diagnosis_language")

    return GuardrailResult(approved=True, rejection_reason=None)
