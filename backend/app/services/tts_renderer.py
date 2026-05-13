"""ElevenLabs-only TTS renderer for proactive voice jobs."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Literal, cast

from app.core.config import Settings, get_settings
from app.services.pii_mask import mask_pii
from app.services.tts_elevenlabs_budget import can_use_elevenlabs_chars, record_elevenlabs_chars_used
from app.services.tts_exceptions import PermanentTtsError

logger = logging.getLogger(__name__)

TTS_AUDIO_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "generated_voice"
TTS_AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_EST_CHARS_PER_SEC_VI = 12.0


def _parse_numeric_job_id(job_id: str) -> int:
    s = (job_id or "").strip()
    if s.lower().startswith("tts_"):
        s = s[4:]
    return int(s)


def _estimate_duration_seconds(char_count: int) -> float:
    if char_count <= 0:
        return 0.0
    return round(char_count / _EST_CHARS_PER_SEC_VI, 2)


def _normalize_audio_bytes(raw: Any) -> bytes:
    if isinstance(raw, bytes):
        return raw
    if hasattr(raw, "__iter__"):
        chunks: list[bytes] = []
        for chunk in raw:
            if isinstance(chunk, bytes):
                chunks.append(chunk)
        return b"".join(chunks)
    return b""


def _tier_list_from_settings(settings: Settings) -> set[str]:
    raw = (settings.elevenlabs_use_only_on_tier or "").strip().lower()
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def elevenlabs_route_allowed(
    *,
    safety_tier: str | None,
    distress_score: float | None,
    settings: Settings,
) -> bool:
    tiers = _tier_list_from_settings(settings)
    st = (safety_tier or "").strip().lower()
    if st in tiers:
        return True
    d = float(distress_score if distress_score is not None else 0.0)
    return d >= float(settings.elevenlabs_min_distress)


def _elevenlabs_credentials_ready(settings: Settings) -> bool:
    return bool((settings.elevenlabs_api_key or "").strip() and (settings.elevenlabs_voice_id or "").strip())

def resolve_elevenlabs_voice_id(*, settings: Settings, voice_style_id: str | None) -> str:
    """Resolve per-persona ElevenLabs voice id with safe fallback."""
    style = (voice_style_id or "").strip().lower()
    if style == "warm_friend":
        preferred = (getattr(settings, "elevenlabs_voice_id_crush_male", "") or "").strip()
        return preferred or (getattr(settings, "elevenlabs_voice_id", "") or "").strip()
    if style == "calm_mentor":
        preferred = (getattr(settings, "elevenlabs_voice_id_mentor", "") or "").strip()
        return preferred or (getattr(settings, "elevenlabs_voice_id", "") or "").strip()
    return (getattr(settings, "elevenlabs_voice_id", "") or "").strip()


def _ensure_elevenlabs_eligible(
    *,
    settings: Settings,
    safety_tier: str | None,
    distress_score: float | None,
    user_id: str | None,
    char_count: int,
) -> None:
    if not bool(settings.elevenlabs_feature_enabled):
        raise PermanentTtsError("elevenlabs_feature_disabled")
    if not _elevenlabs_credentials_ready(settings):
        raise PermanentTtsError("elevenlabs_credentials_missing")
    if not elevenlabs_route_allowed(safety_tier=safety_tier, distress_score=distress_score, settings=settings):
        logger.warning(
            "elevenlabs_route_not_allowed safety_tier=%s distress_score=%s",
            safety_tier, distress_score,
        )
        raise PermanentTtsError("elevenlabs_route_not_allowed")
    uid = (user_id or "").strip()
    if not uid:
        raise PermanentTtsError("elevenlabs_user_id_required")
    if not can_use_elevenlabs_chars(uid, char_count, settings):
        raise PermanentTtsError("elevenlabs_budget_unavailable")


def _truncate_for_tts(script: str, max_chars: int) -> str:
    s = script.strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _elevenlabs_synthesize(settings: Settings, text: str, *, voice_style_id: str | None = None) -> bytes:
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs.types.voice_settings import VoiceSettings
    except ImportError as exc:
        # Package missing — treat as permanent (no point retrying 3 times).
        raise PermanentTtsError("elevenlabs_package_missing") from exc

    client = ElevenLabs(api_key=(settings.elevenlabs_api_key or "").strip())
    vs = VoiceSettings(
        stability=0.82,
        similarity_boost=0.78,
        style=0.0,
        speed=0.9,
        use_speaker_boost=True,
    )
    fmt = (settings.elevenlabs_output_format or "mp3_44100_128").strip()
    model = (settings.elevenlabs_model_id or "eleven_multilingual_v2").strip()
    voice = resolve_elevenlabs_voice_id(settings=settings, voice_style_id=voice_style_id)
    out_iter = client.text_to_speech.convert(
        voice_id=voice,
        text=text,
        model_id=model,
        output_format=cast(Any, fmt),
        voice_settings=vs,
    )
    return _normalize_audio_bytes(out_iter)


def _invoke_elevenlabs_with_timeout(
    settings: Settings,
    text: str,
    *,
    voice_style_id: str | None = None,
) -> tuple[bytes | None, str]:
    timeout_s = float(settings.elevenlabs_timeout_seconds)

    def _work() -> bytes:
        return _elevenlabs_synthesize(settings, text, voice_style_id=voice_style_id)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_work)
            data = fut.result(timeout=timeout_s)
        if not data:
            return None, "error"
        return data, "success"
    except FuturesTimeout:
        logger.warning("elevenlabs tts: timeout after %.1fs", timeout_s)
        return None, "timeout"
    except PermanentTtsError:
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "429" in msg or "rate" in msg:
            logger.warning("elevenlabs tts: rate limit / throttle: %s", exc)
            return None, "rate_limit"
        if "402" in msg or "quota" in msg or "credit" in msg:
            logger.warning("elevenlabs tts: quota / billing: %s", exc)
            return None, "quota_exceeded"
        logger.warning("elevenlabs tts: synthesis failed: %s", exc)
        return None, "error"


def _write_mp3(job_num: int, audio_bytes: bytes) -> Path:
    out = TTS_AUDIO_OUTPUT_DIR / f"tts_{job_num}.mp3"
    out.write_bytes(audio_bytes)
    return out


def _tts_result_dict(
    path: Path | None,
    *,
    provider_label: Literal["elevenlabs"],
    chars: int,
    used_fallback: bool,
    success: bool,
) -> dict[str, Any]:
    duration = _estimate_duration_seconds(chars)
    return {
        "audio_path": str(path) if path else "",
        "provider": provider_label,
        "duration": duration,
        "chars": chars,
        "success": success and path is not None,
        "fallback": used_fallback,
    }


def _run_elevenlabs(
    job_num: int,
    text: str,
    settings: Settings,
    *,
    user_id: str | None,
    started: float,
    distress_score: float | None,
    voice_style_id: str | None = None,
) -> dict[str, Any]:
    el_bytes, el_outcome = _invoke_elevenlabs_with_timeout(settings, text, voice_style_id=voice_style_id)
    el_latency = (time.perf_counter() - started) * 1000.0
    ds = distress_score if distress_score is not None else -1.0
    if el_bytes:
        uid = (user_id or "").strip()
        if uid:
            record_elevenlabs_chars_used(uid, len(text))
        path = _write_mp3(job_num, el_bytes)
        logger.info(
            "tts_metrics provider=elevenlabs latency_ms=%.1f char_count=%s outcome=success fallback=false distress_score=%.3f",
            el_latency,
            len(text),
            ds,
        )
        return _tts_result_dict(
            path,
            provider_label="elevenlabs",
            chars=len(text),
            used_fallback=False,
            success=True,
        )

    logger.info(
        "tts_metrics provider=elevenlabs latency_ms=%.1f char_count=%s outcome=%s fallback=false distress_score=%.3f",
        el_latency,
        len(text),
        el_outcome,
        ds,
    )
    return _tts_result_dict(
        None,
        provider_label="elevenlabs",
        chars=len(text),
        used_fallback=False,
        success=False,
    )


def _normalize_tts_provider(provider: str | None) -> str:
    p = (provider or "elevenlabs").strip().lower()
    if p in ("elevenlabs", "auto"):
        return p
    logger.info("tts_provider=%s unsupported; forcing elevenlabs", p)
    return "elevenlabs"


def render_tts_audio(
    provider: str,
    script: str,
    job_id: str,
    distress_score: float | None = None,
    safety_tier: str | None = None,
    *,
    user_id: str | None = None,
    voice_style_id: str | None = None,
) -> dict[str, Any]:
    """
    Render TTS for a voice job. ``script`` should be the assistant reply text (caller may pre-mask).

    Returns: audio_path, provider, duration, chars, success, fallback.
    """
    settings = get_settings()
    _ = _normalize_tts_provider(provider)
    masked = mask_pii(script or "")
    max_chars = int(settings.elevenlabs_max_chars_per_job)
    prepared = _truncate_for_tts(masked, max_chars)
    chars = len(prepared)
    job_num = _parse_numeric_job_id(job_id)
    started = time.perf_counter()

    _ensure_elevenlabs_eligible(
        settings=settings,
        safety_tier=safety_tier,
        distress_score=distress_score,
        user_id=user_id,
        char_count=chars,
    )
    return _run_elevenlabs(
        job_num,
        prepared,
        settings,
        user_id=user_id,
        started=started,
        distress_score=distress_score,
        voice_style_id=voice_style_id,
    )
