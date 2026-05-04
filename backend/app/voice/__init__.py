"""Voice/TTS package — minimal slice for contract tests before dedup lands."""

from app.voice.types import TTS_REUSABLE_STATUSES, TTS_TERMINAL_STATUSES, TTSStatus

__all__ = [
    "TTS_REUSABLE_STATUSES",
    "TTS_TERMINAL_STATUSES",
    "TTSStatus",
]
