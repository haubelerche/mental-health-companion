"""Shared TTS error types (keeps import graph acyclic between proactive_voice and tts_renderer)."""


class PermanentTtsError(Exception):
    """Non-retryable TTS error (e.g. Blaze 401/402)."""
