"""Knowledge content safety review — Plan 07.

Deterministic check that knowledge card content is psychoeducation, not diagnosis.

Rules (PRD §12.4, plan 07):
- No disorder diagnosis framing.
- No deterministic claims about the user ("bạn bị", "bạn mắc").
- No SOS-level content without escalation guidance marker.
- Must include a psychoeducation disclaimer token (checked separately via seeding).
- Title + content must be non-empty and within length limits.
"""

from __future__ import annotations

from typing import TypedDict

# Patterns owned by safety/content_guardrail.py — do not duplicate here.
from app.safety.content_guardrail import has_diagnosis_language, has_sos_signal

MAX_TITLE_CHARS = 200
MAX_CONTENT_CHARS = 5000


class ContentReviewResult(TypedDict):
    approved: bool
    rejection_reason: str | None


def review_knowledge_card(
    title: str,
    content_markdown: str,
    reflection_prompt: str | None = None,
) -> ContentReviewResult:
    """Return approved=True if content passes all knowledge safety rules."""
    if not title or not title.strip():
        return ContentReviewResult(approved=False, rejection_reason="empty_title")

    if len(title) > MAX_TITLE_CHARS:
        return ContentReviewResult(approved=False, rejection_reason="title_too_long")

    if not content_markdown or not content_markdown.strip():
        return ContentReviewResult(approved=False, rejection_reason="empty_content")

    if len(content_markdown) > MAX_CONTENT_CHARS:
        return ContentReviewResult(approved=False, rejection_reason="content_too_long")

    combined = f"{title} {content_markdown} {reflection_prompt or ''}"

    if has_diagnosis_language(combined):
        return ContentReviewResult(approved=False, rejection_reason="diagnosis_framing")

    if has_sos_signal(combined):
        return ContentReviewResult(approved=False, rejection_reason="sos_content_without_escalation")

    return ContentReviewResult(approved=True, rejection_reason=None)
