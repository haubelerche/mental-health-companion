"""Safety policy constants.

All numeric thresholds that are shared across surfaces live here.
Do NOT hardcode these values in service code — import from here.
"""

from __future__ import annotations

# --- Letter reward eligibility -----------------------------------------
LETTER_MIN_WORDS: int = 100
LETTER_MAX_REWARD_PER_DAY: int = 2
LETTER_REWARD_AMOUNT: int = 10
LETTER_REWARD_EVENT_TYPE: str = "safe_long_letter_approved"

# --- Output validator ---------------------------------------------------
# Phrases that must never appear in any user-facing text
FORBIDDEN_ROLE_CLAIMS: tuple[str, ...] = (
    "mình là bác sĩ",
    "mình là nhà trị liệu",
    "mình là con người",
    "mình là cấp cứu",
    "mình là người yêu",
    "i am a doctor",
    "i am a therapist",
    "i am a human",
)

FORBIDDEN_DIAGNOSIS_TEMPLATES: tuple[str, ...] = (
    r"bạn bị ",
    r"bạn mắc ",
    r"you have ",
    r"you are diagnosed",
    r"bạn có nguy cơ \d",
)

# --- Content guardrail --------------------------------------------------
MAX_LETTER_CHARS: int = 10_000
SPAM_MIN_UNIQUE_WORD_RATIO: float = 0.25
