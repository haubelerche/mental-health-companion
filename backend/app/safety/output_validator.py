"""SafetyOutputValidator — validate any generated text before it reaches the user.

Covers: FriendNode replies, dashboard insights, TTS scripts.
Does NOT handle routing (that's SafetyGate) or content moderation (that's letter_guardrail).
"""

from __future__ import annotations

import re

from .content_guardrail import has_sos_signal
from .policy import FORBIDDEN_DIAGNOSIS_TEMPLATES, FORBIDDEN_ROLE_CLAIMS
from .verdicts import OutputSafetyVerdict


def _check_role_claims(text: str) -> list[str]:
    lower = text.lower()
    return [claim for claim in FORBIDDEN_ROLE_CLAIMS if claim in lower]


def _check_diagnosis_claims(text: str) -> list[str]:
    lower = text.lower()
    hits: list[str] = []
    for tmpl in FORBIDDEN_DIAGNOSIS_TEMPLATES:
        if re.search(tmpl, lower):
            hits.append(tmpl)
    return hits


def validate_output(text: str, *, surface: str = "chat") -> OutputSafetyVerdict:
    """Validate generated text.

    surface: 'chat' | 'dashboard' | 'tts'
    Returns allow / block / rewrite_required.
    """
    reason_codes: list[str] = []
    flagged: list[str] = []

    role_hits = _check_role_claims(text)
    if role_hits:
        reason_codes.append("forbidden_role_claim")
        flagged.extend(role_hits)

    diag_hits = _check_diagnosis_claims(text)
    if diag_hits:
        reason_codes.append("diagnosis_claim")
        flagged.extend(diag_hits)

    # SOS in a generated output — should have been caught upstream,
    # but block as a last-resort safety net.
    if has_sos_signal(text) and surface in ("dashboard", "tts"):
        reason_codes.append("sos_in_generated_output")

    if not reason_codes:
        return OutputSafetyVerdict(verdict="allow", reason_codes=[], flagged_fragments=[])

    # Role claims and diagnosis claims are hard blocks; never rewrite them.
    return OutputSafetyVerdict(
        verdict="block",
        reason_codes=reason_codes,
        flagged_fragments=flagged,
    )
