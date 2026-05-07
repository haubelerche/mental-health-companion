"""Voice/TTS package.

Provides persona style mapping, event signature deduplication,
and TTS status type definitions.
"""

from app.voice.dedup import compute_event_signature, dedup_status_for, find_dedup_job
from app.voice.style_mapping import get_voice_style, resolve_active_style
from app.voice.types import TTS_REUSABLE_STATUSES, TTS_TERMINAL_STATUSES, TTSStatus

__all__ = [
    "compute_event_signature",
    "find_dedup_job",
    "dedup_status_for",
    "get_voice_style",
    "resolve_active_style",
    "TTS_REUSABLE_STATUSES",
    "TTS_TERMINAL_STATUSES",
    "TTSStatus",
]
