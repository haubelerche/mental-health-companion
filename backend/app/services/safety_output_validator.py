"""Conversation-quality and safety validation helpers for Serene output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.microcopy_library import contains_generic_empathy
from app.services.sos_handler import _normalize_text


@dataclass(frozen=True)
class ResponseQualityVerdict:
    ok: bool
    reason_codes: list[str]


def count_questions(text: str) -> int:
    return text.count("?") + text.count("？")


def _meets_context_anchor(stripped: str) -> bool:
    """Heuristic for 'enough substance' without punishing normal short Vietnamese chat.

    A fixed 16-token minimum rejected most concise empathetic replies and forced
    deterministic fallbacks in ``build_response_plan``, making Serene feel templated.
    """
    if not stripped:
        return False
    if len(stripped) >= 40:
        return True
    return len(stripped.split()) >= 6


def count_sentences(text: str) -> int:
    parts = re.split(r"(?<=[.!?。！？])\s+", (text or "").strip())
    return len([part for part in parts if part.strip()])


def has_markdown(text: str) -> bool:
    return bool(re.search(r"(```|^\s*[-*+]\s+|[*_#>\[\]])", text or "", re.MULTILINE))


def validate_serene_response(
    text: str,
    *,
    require_context_anchor: bool = False,
    max_sentences: int | None = None,
    max_questions: int = 1,
    emotional_chat: bool = True,
) -> ResponseQualityVerdict:
    reasons: list[str] = []
    stripped = (text or "").strip()
    if not stripped:
        reasons.append("empty_response")
    if contains_generic_empathy(stripped):
        reasons.append("generic_empathy_loop")
    if contains_generic_empathy(_normalize_text(stripped)):
        reasons.append("generic_empathy_loop")
    if count_questions(stripped) > max_questions:
        reasons.append("too_many_questions")
    if re.search(r"\b(chẩn đoán|rối loạn|bệnh lý|diagnos)", stripped, re.IGNORECASE):
        reasons.append("diagnosis_language")
    if stripped.count("!") > 1:
        reasons.append("excessive_exclamation")
    if emotional_chat and has_markdown(stripped):
        reasons.append("markdown_in_emotional_chat")
    if max_sentences is not None and count_sentences(stripped) > max_sentences:
        reasons.append("too_many_sentences")
    if require_context_anchor and not _meets_context_anchor(stripped):
        reasons.append("missing_context_anchor")
    normalized_reasons = sorted(set(reasons))
    return ResponseQualityVerdict(ok=not normalized_reasons, reason_codes=normalized_reasons)
