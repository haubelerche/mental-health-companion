from __future__ import annotations

import re
from dataclasses import dataclass

from app.safety.content_guardrail import has_diagnosis_language, has_sos_signal

_PII_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:\+?\d[\s.-]?){8,}\b")
_PHQ_GAD_RE = re.compile(r"\b(PHQ-?9|GAD-?7|điểm\s*(phq|gad)|score)\b", re.IGNORECASE)
_SHAMING_RE = re.compile(r"\b(lười|yếu đuối|tệ|phải|bắt buộc|đáng trách|vô kỷ luật)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PrivacyDecision:
    allowed: bool
    reason: str | None = None
    rewritten_summary: str | None = None


def filter_user_safe_insight(
    *,
    summary: str,
    confidence: float,
    evidence_count: int,
    sensitivity: str = "medium",
) -> PrivacyDecision:
    text = (summary or "").strip()
    lowered = text.lower()
    if not text:
        return PrivacyDecision(False, "empty_summary")
    if "tự hại" in lowered or "nguy cơ" in lowered and ("cao" in lowered or "risk" in lowered):
        return PrivacyDecision(False, "risk_or_crisis_language")
    if has_diagnosis_language(text):
        return PrivacyDecision(False, "diagnosis_language")
    if has_sos_signal(text):
        return PrivacyDecision(False, "risk_or_crisis_language")
    if _PHQ_GAD_RE.search(text):
        return PrivacyDecision(False, "raw_screening_reference")
    if _PII_RE.search(text):
        return PrivacyDecision(False, "pii_detected")
    if _SHAMING_RE.search(text):
        return PrivacyDecision(False, "shaming_language")
    if sensitivity in {"high", "restricted"} and evidence_count < 3:
        return PrivacyDecision(False, "single_sensitive_event")
    if evidence_count < 2:
        return PrivacyDecision(False, "insufficient_evidence")
    if confidence < 0.35:
        return PrivacyDecision(False, "low_confidence")
    return PrivacyDecision(True, None, text)
