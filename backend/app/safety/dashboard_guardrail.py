"""Dashboard insight safety projector.

Filters InsightHypothesis cards before they reach the frontend.
Rules:
- No diagnosis framing (clinical label, percentage claim).
- No SOS-level content in user-facing summary.
- Confidence must be ≤ 0.85 (prevents over-certainty claims).

Frontend MUST NOT see clinical_profiles, risk_inference_log, or raw analyst_signals.
This module only guards the summary text that is already approved for display.
"""

from __future__ import annotations

from .content_guardrail import has_diagnosis_language, has_sos_signal

_MAX_CONFIDENCE = 0.85


def insight_display_allowed(
    *,
    user_safe_summary: str,
    confidence: float | None,
) -> tuple[bool, str | None]:
    """Return (allowed, rejection_reason).

    Called per-card in build_safe_insight_cards before the card is included.
    """
    if not user_safe_summary or not user_safe_summary.strip():
        return False, "empty_summary"

    if has_sos_signal(user_safe_summary):
        return False, "sos_in_insight"

    if has_diagnosis_language(user_safe_summary):
        return False, "diagnosis_in_insight"

    if confidence is not None and confidence > _MAX_CONFIDENCE:
        return False, "confidence_too_high"

    return True, None
