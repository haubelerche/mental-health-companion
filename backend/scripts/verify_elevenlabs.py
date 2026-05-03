#!/usr/bin/env python3
"""
Smoke-check ElevenLabs API key (run from repo root: python backend/scripts/verify_elevenlabs.py).

Uses the same env as the API (backend/.env via get_settings). Calls the same code path as
production TTS (text_to_speech.convert) with a 1-character probe — avoids models.list(), which
requires the models_read scope many restricted keys do not have.

Exits 0 on success, 1 on failure. Consumes minimal TTS quota (~1 char).
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path

# Ensure `app` package resolves when run as script
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_PROBE_TIMEOUT_S = 25.0


def main() -> int:
    from app.core.config import get_settings
    from app.services.tts_renderer import _elevenlabs_synthesize

    s = get_settings()
    key = (s.elevenlabs_api_key or "").strip()
    voice = (s.elevenlabs_voice_id or "").strip()
    if not key:
        print("ELEVENLABS_API_KEY is empty — set it in .env", file=sys.stderr)
        return 1
    if not voice:
        print("ELEVENLABS_VOICE_ID is empty — set it in .env", file=sys.stderr)
        return 1
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_elevenlabs_synthesize, s, ".")
            audio = fut.result(timeout=_PROBE_TIMEOUT_S)
        if not audio:
            print("ElevenLabs FAILED: empty audio response", file=sys.stderr)
            return 1
        print(f"ElevenLabs OK: TTS probe succeeded; audio_bytes={len(audio)}")
        return 0
    except FuturesTimeout:
        print(f"ElevenLabs FAILED: timeout after {_PROBE_TIMEOUT_S}s", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ElevenLabs FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
