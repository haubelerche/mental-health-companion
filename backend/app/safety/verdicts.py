"""Typed verdict contracts for all safety surfaces."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Letter surface
# ---------------------------------------------------------------------------

LetterVerdictCode = Literal[
    "approved_safe_long_letter",
    "rejected_too_short",
    "rejected_harmful_content",
    "rejected_spam_or_farming",
    "needs_manual_review",
    "safety_escalate",
]


class LetterSafetyVerdict(BaseModel):
    verdict: LetterVerdictCode
    reward_allowed: bool
    user_message: str
    reason_codes: list[str]
    confidence: float
    should_create_safety_event: bool
    should_notify_safety_flow: bool

    @property
    def is_approved(self) -> bool:
        return self.verdict == "approved_safe_long_letter"

    @property
    def needs_escalation(self) -> bool:
        return self.verdict == "safety_escalate"


# ---------------------------------------------------------------------------
# Output surface (Friend, dashboard insight, TTS script)
# ---------------------------------------------------------------------------

OutputVerdictCode = Literal["allow", "block", "rewrite_required"]


class OutputSafetyVerdict(BaseModel):
    verdict: OutputVerdictCode
    reason_codes: list[str]
    flagged_fragments: list[str]

    @property
    def is_blocked(self) -> bool:
        return self.verdict != "allow"
