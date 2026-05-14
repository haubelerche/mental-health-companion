"""Memory guardrail — deterministic safety review for candidate cards.

Rules (plan 06):
- No diagnosis language (DSM disorder names, "bạn bị", "bạn mắc").
- No highly sensitive / SOS-level content.
- Content must be concise (≤ 300 chars) and reviewable.
- Title must be non-empty and ≤ 120 chars.
- Confidence must be in [0.0, 1.0] when provided.
"""

from __future__ import annotations

from typing import TypedDict

# Patterns are owned by safety/content_guardrail.py — do not duplicate here.
from app.safety.content_guardrail import has_diagnosis_language, has_sos_signal

MAX_CONTENT_CHARS = 300
MAX_TITLE_CHARS = 120

VALID_TYPES = {
    "background",
    "support_style",
    "preference",
    "coping_history",
    "current_stressor",
    "nutrition_pattern",
    "persona_preference",
    "temporary_context",
    "event_memory",
    "support_insight",
    "relationship_context",
    "goal_or_hope",
    "emotional_pattern",
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

    text = f"{title} {content}"

    if has_sos_signal(text):
        return GuardrailResult(approved=False, rejection_reason="sos_content")

    if has_diagnosis_language(text):
        return GuardrailResult(approved=False, rejection_reason="diagnosis_language")

    return GuardrailResult(approved=True, rejection_reason=None)
