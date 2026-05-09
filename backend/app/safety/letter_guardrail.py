"""Letter safety pipeline.

Pipeline:
  WordCountGate → SOSGate → SpamGate → ContentGuardrail → verdict

Only deterministic rule-based checks. No LLM calls here.
"""

from __future__ import annotations

from .content_guardrail import (
    has_diagnosis_language,
    has_harmful_content,
    has_sos_signal,
    is_spam_by_unique_ratio,
)
from .policy import (
    LETTER_MIN_WORDS,
    MAX_LETTER_CHARS,
    SPAM_MIN_UNIQUE_WORD_RATIO,
)
from .verdicts import LetterSafetyVerdict


def _word_count(text: str) -> int:
    return len(text.split())


def review_letter(content: str) -> LetterSafetyVerdict:
    """Run the full letter review pipeline and return a typed verdict."""

    if len(content) > MAX_LETTER_CHARS:
        return LetterSafetyVerdict(
            verdict="rejected_harmful_content",
            reward_allowed=False,
            user_message="Thư quá dài. Vui lòng viết ngắn hơn.",
            reason_codes=["content_too_long"],
            confidence=1.0,
            should_create_safety_event=False,
            should_notify_safety_flow=False,
        )

    wc = _word_count(content)
    if wc < LETTER_MIN_WORDS:
        return LetterSafetyVerdict(
            verdict="rejected_too_short",
            reward_allowed=False,
            user_message=(
                f"Thư cần ít nhất {LETTER_MIN_WORDS} từ để nhận Tim thưởng. "
                f"Hiện tại thư của bạn có {wc} từ."
            ),
            reason_codes=["too_short"],
            confidence=1.0,
            should_create_safety_event=False,
            should_notify_safety_flow=False,
        )

    # SOS check runs before spam: a crisis signal must never be suppressed
    # by the repetition/farming gate.
    if has_sos_signal(content):
        return LetterSafetyVerdict(
            verdict="safety_escalate",
            reward_allowed=False,
            user_message=(
                "Serene nhận ra bạn đang trải qua điều rất khó khăn. "
                "Hãy để Serene ở đây cùng bạn."
            ),
            reason_codes=["sos_content"],
            confidence=0.95,
            should_create_safety_event=True,
            should_notify_safety_flow=True,
        )

    if is_spam_by_unique_ratio(content, SPAM_MIN_UNIQUE_WORD_RATIO):
        return LetterSafetyVerdict(
            verdict="rejected_spam_or_farming",
            reward_allowed=False,
            user_message="Thư có vẻ lặp lại quá nhiều. Hãy viết từ trái tim bạn nhé.",
            reason_codes=["spam_low_unique_ratio"],
            confidence=0.85,
            should_create_safety_event=False,
            should_notify_safety_flow=False,
        )

    if has_harmful_content(content):
        return LetterSafetyVerdict(
            verdict="rejected_harmful_content",
            reward_allowed=False,
            user_message="Thư chứa nội dung không phù hợp và không thể được gửi đi.",
            reason_codes=["harmful_content"],
            confidence=0.90,
            should_create_safety_event=True,
            should_notify_safety_flow=False,
        )

    if has_diagnosis_language(content):
        return LetterSafetyVerdict(
            verdict="needs_manual_review",
            reward_allowed=False,
            user_message="Thư đang được xem xét. Tim thưởng sẽ được cấp sau khi hoàn tất.",
            reason_codes=["diagnosis_language"],
            confidence=0.80,
            should_create_safety_event=False,
            should_notify_safety_flow=False,
        )

    return LetterSafetyVerdict(
        verdict="approved_safe_long_letter",
        reward_allowed=True,
        user_message="Thư của bạn đã được gửi thành công.",
        reason_codes=[],
        confidence=1.0,
        should_create_safety_event=False,
        should_notify_safety_flow=False,
    )
