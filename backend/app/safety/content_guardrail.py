"""Shared pattern library for content guardrail checks.

Rules are inherited from memory/guardrail.py and extended here.
Add new patterns here; do NOT duplicate into feature-specific files.
"""

from __future__ import annotations

import re

# --- Diagnosis language -------------------------------------------------
DIAGNOSIS_PATTERNS: list[str] = [
    r"\b(trầm cảm|rối loạn|tâm thần|hoang tưởng|tự kỷ|ám ảnh|lo âu rối loạn)\b",
    r"\bbạn (bị|mắc|có)\b.{0,30}(rối loạn|disorder|syndrome|phobia)",
    r"\b(depression|anxiety disorder|OCD|PTSD|bipolar|schizophrenia)\b",
]

# --- SOS / high-risk content --------------------------------------------
SOS_PATTERNS: list[str] = [
    r"\b(tự tử|tự làm hại|muốn chết|kết thúc cuộc sống|suicide|self.harm|kill (myself|yourself))\b",
    r"\b(không muốn sống|chấm dứt|kết liễu)\b",
]

# --- Harmful / hate content --------------------------------------------
HARMFUL_PATTERNS: list[str] = [
    r"\b(ghét|căm thù|giết|bạo lực|làm hại người khác)\b.{0,40}(ai đó|người|họ|nó)",
    r"\b(how to harm|how to hurt)\b",
]


def _match_any(text: str, patterns: list[str]) -> str | None:
    """Return the first matching pattern key or None."""
    lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, lower, re.IGNORECASE):
            return pattern
    return None


def has_diagnosis_language(text: str) -> bool:
    return _match_any(text, DIAGNOSIS_PATTERNS) is not None


def has_sos_signal(text: str) -> bool:
    return _match_any(text, SOS_PATTERNS) is not None


def has_harmful_content(text: str) -> bool:
    return _match_any(text, HARMFUL_PATTERNS) is not None


def is_spam_by_unique_ratio(text: str, min_ratio: float) -> bool:
    words = text.lower().split()
    if not words:
        return True
    unique = len(set(words))
    return (unique / len(words)) < min_ratio
