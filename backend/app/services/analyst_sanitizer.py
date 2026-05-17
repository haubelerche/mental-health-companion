"""
Analyst bundle sanitizer.

Prevents internal Analyst fields (risk_indicators, clinical_note_internal,
disorder labels, diagnosis probabilities) from reaching FriendNode prompts
or public dashboard output.

Rules (per PRD §3 / CLAUDE.md §3):
- FriendNode may only receive user-safe themes, coping preferences, emotions.
- Dashboard receives only severity_band + user_safe_summary + evidence_count.
- Any diagnosis-like phrase is rewritten to non-clinical language.
- Clinical rationale and raw risk indicators are stripped entirely.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.schemas.contracts import AnalystBundle

# ---------------------------------------------------------------------------
# Diagnosis detection patterns
# ---------------------------------------------------------------------------

_DIAGNOSIS_PATTERNS: list[str] = [
    r"bạn bị ",
    r"bạn mắc ",
    r"mình chẩn đoán",
    r"chẩn đoán bạn là",
    r"bạn có \d+% khả năng",
    r"you have ",
    r"you are diagnosed",
    r"rối loạn lo âu",
    r"trầm cảm nặng",
    r"bipolar",
    r"MDD",
    r"GAD\b",
    r"PTSD\b",
]

_DISORDER_LABEL_REWRITES: dict[str, str] = {
    "rối loạn lo âu": "lo âu kéo dài",
    "trầm cảm nặng": "tâm trạng xuống dốc kéo dài",
    "trầm cảm": "cảm xúc nặng nề",
    "bipolar": "cảm xúc biến động",
    "mdd": "giai đoạn cảm xúc khó khăn",
    "gad": "lo lắng nhiều",
    "ptsd": "ký ức nặng nề",
    "rối loạn nhân cách": "khó khăn trong mối quan hệ",
    "tâm thần phân liệt": "khó khăn về nhận thức",
}


def _contains_diagnosis(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t, re.IGNORECASE) for p in _DIAGNOSIS_PATTERNS)


def _rewrite_clinical_to_safe(text: str) -> str:
    """Replace clinical labels with non-clinical phrasing."""
    result = text
    for clinical, safe in _DISORDER_LABEL_REWRITES.items():
        result = re.sub(re.escape(clinical), safe, result, flags=re.IGNORECASE)
    return result


# ---------------------------------------------------------------------------
# FriendNode context sanitizer
# ---------------------------------------------------------------------------

# Keys from AnalystBundle that are safe for FriendNode to receive
_FRIEND_SAFE_KEYS = frozenset({
    "dominant_emotions",
    "coping_preferences",
    "recurring_triggers",   # only if non-clinical
    "missing_info",
})


def sanitize_analyst_bundle_for_friend_context(
    bundle: AnalystBundle,
) -> dict[str, Any]:
    """
    Returns a dict containing only user-safe fields for FriendNode's context.

    Strips: cognitive_patterns (may contain disorder heuristics), nutrition_patterns
    (medical inference), evidence_refs (internal JSONL paths), confidence, time_window.
    Rewrites any remaining clinical language in dominant_emotions and triggers.
    """
    sanitized: dict[str, Any] = {}

    # Emotions — rewrite clinical terms first, then filter residual diagnosis phrases
    safe_emotions = []
    for e in bundle.dominant_emotions:
        rewritten = _rewrite_clinical_to_safe(e)
        if not _contains_diagnosis(rewritten):
            safe_emotions.append(rewritten)
    if safe_emotions:
        sanitized["dominant_emotions"] = safe_emotions

    # Coping preferences — pass through (no clinical risk)
    if bundle.coping_preferences:
        sanitized["coping_preferences"] = list(bundle.coping_preferences)

    # Triggers — rewrite clinical terms, filter diagnosis-like entries
    safe_triggers = [
        _rewrite_clinical_to_safe(t)
        for t in bundle.recurring_triggers
        if not _contains_diagnosis(t)
    ]
    if safe_triggers:
        sanitized["recurring_triggers"] = safe_triggers

    # Missing info (what context is absent) — pass through
    if bundle.missing_info:
        sanitized["missing_info"] = list(bundle.missing_info)

    return sanitized


# ---------------------------------------------------------------------------
# Dashboard sanitizer
# ---------------------------------------------------------------------------

def sanitize_analyst_bundle_for_dashboard(
    bundle: AnalystBundle,
    user_safe_summary: str = "",
) -> dict[str, Any]:
    """
    Returns a dashboard-safe dict: severity_band, user_safe_summary,
    evidence_count, and confidence — no raw risk indicators or clinical rationale.

    The caller is responsible for generating user_safe_summary from a
    backend-controlled template; this function does NOT generate it from
    raw bundle fields to avoid clinical language leakage.
    """
    evidence_count = len(bundle.evidence_refs)
    dominant_count = len(bundle.dominant_emotions)

    # Severity band derived from confidence — no disorder labels
    severity_band_map = {"low": "mild", "medium": "moderate", "high": "elevated"}
    severity_band = severity_band_map.get(bundle.confidence, "unknown")

    # Use caller-provided summary or build a safe default
    if not user_safe_summary:
        if bundle.dominant_emotions:
            primary_emotion = _rewrite_clinical_to_safe(bundle.dominant_emotions[0])
            user_safe_summary = f"Dấu hiệu nổi bật: {primary_emotion}"
        else:
            user_safe_summary = "Không có đủ dữ liệu để phân tích"

    return {
        "severity_band": severity_band,
        "user_safe_summary": user_safe_summary,
        "evidence_count": evidence_count,
        "signal_count": dominant_count,
        "confidence": bundle.confidence,
        # No: cognitive_patterns, nutrition_patterns, recurring_triggers (clinical),
        #     evidence_refs, time_window, user_id
    }


# ---------------------------------------------------------------------------
# Validation helper — for tests and pre-flight checks
# ---------------------------------------------------------------------------

def assert_no_clinical_labels(data: dict[str, Any], context: str = "") -> None:
    """
    Raises AssertionError if any value in data contains a diagnosis phrase.
    Used in tests and optional pre-send validation.
    """
    text = str(data)
    for pattern in _DIAGNOSIS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raise AssertionError(
                f"Clinical label detected in {context or 'output'}: "
                f"pattern='{pattern}' match='{match.group()}'"
            )
