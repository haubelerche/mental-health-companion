from app.core.config import Settings
from app.services.tts_renderer import resolve_elevenlabs_voice_id


def _settings(**overrides):
    base = {
        "ELEVENLABS_VOICE_ID": "base_voice",
        "ELEVENLABS_VOICE_ID_BFF": "",
        "ELEVENLABS_VOICE_ID_MENTOR": "",
        "ELEVENLABS_VOICE_ID_CRUSH_FEMALE": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_resolve_voice_id_uses_persona_specific_env_vars():
    settings = _settings(
        ELEVENLABS_VOICE_ID_BFF="dung_voice",
        ELEVENLABS_VOICE_ID_MENTOR="dat_voice",
        ELEVENLABS_VOICE_ID_CRUSH_FEMALE="hau_voice",
    )

    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="warm_friend") == "dung_voice"
    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="calm_mentor") == "dat_voice"
    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="soft_quiet") == "hau_voice"


def test_resolve_voice_id_falls_back_to_base_voice_only():
    settings = _settings(ELEVENLABS_VOICE_ID_BFF="")

    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="warm_friend") == "base_voice"
    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="unknown") == "base_voice"


def test_legacy_crush_male_env_does_not_override_bff_mapping(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_VOICE_ID_CRUSH_MALE", "legacy_wrong_voice")
    settings = _settings(ELEVENLABS_VOICE_ID_BFF="dung_voice")

    assert not hasattr(settings, "elevenlabs_voice_id_crush_male")
    assert resolve_elevenlabs_voice_id(settings=settings, voice_style_id="warm_friend") == "dung_voice"
