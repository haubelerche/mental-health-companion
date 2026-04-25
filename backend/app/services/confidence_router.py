from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceDecision:
    requires_human_review: bool
    reason: str


def route_for_human_review(*, distress_score: float, sos_triggered: bool, threshold: float = 0.85) -> ConfidenceDecision:
    if sos_triggered:
        return ConfidenceDecision(False, "sos_path")
    if float(distress_score) >= float(threshold):
        return ConfidenceDecision(True, "high_distress_low_confidence")
    return ConfidenceDecision(False, "auto_ok")
