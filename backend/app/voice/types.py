"""Voice/TTS type definitions — Plan 08.

Canonical status vocabulary (rule: voice-tts.md, plan 08 §14.4).
Frontend polling stops on terminal statuses.
"""

from __future__ import annotations

from typing import Literal

TTSStatus = Literal[
    "queued",
    "processing",
    "ready",
    "failed",
    "skipped_duplicate",
    "cache_hit",
    "provider_disabled",
]

# Statuses at which frontend polling should stop.
TTS_TERMINAL_STATUSES: frozenset[str] = frozenset({
    "ready",
    "failed",
    "skipped_duplicate",
    "cache_hit",
    "provider_disabled",
})

# Statuses considered healthy (reusable for cache_hit path).
TTS_REUSABLE_STATUSES: frozenset[str] = frozenset({
    "queued",
    "processing",
    "ready",
    "cache_hit",
})
