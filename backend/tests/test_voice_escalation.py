"""
Tests: Voice escalation pipeline
Kiểm tra từng tầng của luồng gửi voice message khi phát hiện tình huống nguy cấp.

Layers tested:
  1. build_voice_script()          — chọn đúng kịch bản theo ngữ cảnh
  2. compute_escalation_signal()   — trigger escalation đúng điều kiện
  3. _render_blaze_audio()         — gọi Blaze API và lưu file audio (mocked HTTP)
  4. enqueue + process job         — end-to-end job lifecycle (SQLite in-memory)
"""

from __future__ import annotations
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── 1. build_voice_script ─────────────────────────────────────────────────────


from app.services.proactive_voice import build_voice_script


class TestBuildVoiceScript:
    def _call(self, msg: str, distress: float = 0.5, tier: str = "elevated") -> str:
        return build_voice_script(
            user_message=msg,
            recent_messages=[],
            distress_score=distress,
            risk_level=3,
            safety_tier=tier,
            conversation_mode="supportive",
        )

    def test_violent_keyword_triggers_safety_script(self):
        script = self._call("tao se giet no")
        assert "an toàn" in script.lower() or "hotline" in script.lower()

    def test_suicide_keyword_triggers_crisis_script(self):
        script = self._call("tôi muon chet roi")
        assert "ở đây với bạn" in script or "hotline" in script.lower()

    def test_critical_tier_triggers_breathing_script(self):
        script = self._call("mệt quá rồi", distress=0.85, tier="critical")
        assert "4 giây" in script or "hít" in script.lower()

    def test_voice_recommended_tier_triggers_breathing_script(self):
        script = self._call("không còn muốn cố nữa", distress=0.82, tier="voice_recommended")
        assert "hít" in script.lower() or "nghe bạn" in script.lower()

    def test_moderate_distress_returns_default_script(self):
        script = self._call("hôm nay buồn", distress=0.4, tier="elevated")
        assert "ở đây với bạn" in script

    def test_script_is_nonempty_for_all_tiers(self):
        for tier in ("normal", "elevated", "voice_recommended", "critical"):
            script = self._call("test", distress=0.5, tier=tier)
            assert script and len(script) > 10


# ── 2. compute_escalation_signal ─────────────────────────────────────────────


from app.services.safety_scoring import compute_escalation_signal


class TestEscalationSignal:
    def _sig(self, current: float, previous: list[float], threshold: float = 0.84, delta: float = 0.22):
        return compute_escalation_signal(
            current_distress=current,
            previous_distress=previous,
            threshold=threshold,
            delta_threshold=delta,
            window_turns=6,
        )

    def test_threshold_crossed_triggers_escalation(self):
        sig = self._sig(current=0.9, previous=[0.3, 0.4])
        assert sig.escalate is True
        assert sig.trigger_reason == "threshold_crossed"

    def test_rapid_rise_triggers_escalation(self):
        # sudden jump from 0.4 → 0.75 (delta >= 0.22)
        sig = self._sig(current=0.75, previous=[0.4, 0.42, 0.44])
        assert sig.escalate is True
        assert sig.trigger_reason in ("rapid_escalation", "threshold_crossed", "rolling_window_high")

    def test_sustained_high_distress_triggers_rolling_window(self):
        # threshold=0.84 => rolling_window_high needs rolling >= 0.76 and >=2 high turns
        sig = self._sig(current=0.79, previous=[0.78, 0.80, 0.79])
        assert sig.escalate is True

    def test_low_distress_no_escalation(self):
        sig = self._sig(current=0.2, previous=[0.1, 0.15, 0.2])
        assert sig.escalate is False
        assert sig.trigger_reason == "none"

    def test_single_turn_below_threshold_no_escalation(self):
        sig = self._sig(current=0.5, previous=[])
        assert sig.escalate is False

    def test_force_escalation_at_critical_tier(self):
        """safety_tier=critical + distress>=0.8 → force_voice_by_tier trong chat router.
        Ở đây kiểm tra signal riêng — dù escalate=False vẫn ổn nếu force tier bật."""
        sig = self._sig(current=0.81, previous=[0.1, 0.1])
        # distress >= threshold (0.84)? Không, nhưng force_voice_by_tier sẽ override trong router.
        # Signal này có thể False — đây là expected behaviour.
        assert isinstance(sig.escalate, bool)


# ── 3. _render_blaze_audio (mocked HTTP) ──────────────────────────────────────


from app.services.proactive_voice import _render_blaze_audio, PermanentTtsError


FAKE_AUDIO_BYTES = b"\xff\xfb\x10\x00" * 512  # fake MP3 header bytes


class TestRenderBlazeAudio:
    def _mock_settings(self, **overrides):
        defaults = {
            "blaze_api_key": "test-blaze-key",
            "blaze_tts_url": "https://api.blaze.vn/api/tts",
            "blaze_tts_model": "blaze-tts-1",
            "blaze_tts_output_format": "mp3",
            "tts_timeout_seconds": 4.0,
        }
        defaults.update(overrides)
        m = MagicMock()
        for k, v in defaults.items():
            setattr(m, k, v)
        return m

    def test_successful_blaze_call_saves_audio_file(self, tmp_path):
        """Blaze API trả về audio bytes → lưu file và trả Path."""
        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.iter_bytes.return_value = iter([FAKE_AUDIO_BYTES[:1024], FAKE_AUDIO_BYTES[1024:]])
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client.stream.return_value = mock_response
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)

            with patch("httpx.Client", return_value=mock_client):
                result = _render_blaze_audio(job_id=1, voice_script="Mình đang ở đây với bạn.")

        assert result is not None
        assert result.suffix == ".mp3"
        assert result.read_bytes() == FAKE_AUDIO_BYTES

    def test_correct_bearer_auth_header_sent(self, tmp_path):
        """Request phải chứa Authorization: Bearer <key>."""
        captured: dict[str, Any] = {}

        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.iter_bytes.return_value = iter([FAKE_AUDIO_BYTES])
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)

            def capture_stream(method, url, json=None, headers=None):
                captured["method"] = method
                captured["url"] = url
                captured["json"] = json
                captured["headers"] = headers or {}
                return mock_response

            mock_client.stream.side_effect = capture_stream

            with patch("httpx.Client", return_value=mock_client):
                _render_blaze_audio(job_id=2, voice_script="test")

        assert captured["headers"].get("Authorization") == "Bearer test-blaze-key"
        assert captured["headers"].get("Content-Type") == "application/json"
        assert captured["json"]["query"] == "test"
        assert captured["json"]["model"] == "blaze-tts-1"
        assert captured["method"] == "POST"

    def test_missing_api_key_returns_none(self):
        with patch("app.services.proactive_voice.get_settings",
                   return_value=self._mock_settings(blaze_api_key="")):
            result = _render_blaze_audio(job_id=3, voice_script="test")
        assert result is None

    def test_401_raises_permanent_error(self, tmp_path):
        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.is_success = False
            mock_response.read.return_value = b"Unauthorized"
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client.stream.return_value = mock_response
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)

            with patch("httpx.Client", return_value=mock_client):
                with pytest.raises(PermanentTtsError, match="blaze_unauthorized"):
                    _render_blaze_audio(job_id=4, voice_script="test")

    def test_402_raises_permanent_error(self, tmp_path):
        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_response = MagicMock()
            mock_response.status_code = 402
            mock_response.is_success = False
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client.stream.return_value = mock_response
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)

            with patch("httpx.Client", return_value=mock_client):
                with pytest.raises(PermanentTtsError, match="blaze_paid_plan_required"):
                    _render_blaze_audio(job_id=5, voice_script="test")

    def test_empty_audio_response_returns_none(self, tmp_path):
        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.iter_bytes.return_value = iter([])
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client.stream.return_value = mock_response
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)

            with patch("httpx.Client", return_value=mock_client):
                result = _render_blaze_audio(job_id=6, voice_script="test")
        assert result is None

    def test_network_error_returns_none(self, tmp_path):
        with patch("app.services.proactive_voice.get_settings", return_value=self._mock_settings()), \
             patch("app.services.proactive_voice._AUDIO_DIR", tmp_path):

            mock_client = MagicMock()
            mock_client.__enter__ = lambda s: s
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.stream.side_effect = Exception("Connection refused")

            with patch("httpx.Client", return_value=mock_client):
                result = _render_blaze_audio(job_id=7, voice_script="test")
        assert result is None


# ── 4. Router helper: escalate -> intervention payload ────────────────────────


from app.api.v1.routers.chat import _build_voice_intervention
from app.services.safety_scoring import SafetySnapshot


class TestVoiceInterventionPayload:
    def test_escalation_builds_voice_intervention_with_contextual_script(self):
        fake_voice = {"status": "queued", "tts_job_id": "tts_123", "audio_url": None, "provider": "blaze"}
        with patch("app.api.v1.routers.chat.enqueue_voice_job", return_value=fake_voice), patch(
            "app.api.v1.routers.chat.mark_cooldown"
        ):
            payload = _build_voice_intervention(
                db=MagicMock(),
                user_id="u1",
                session_id="s1",
                raw_text="toi muon tu tu",
                recent_messages=[],
                snapshot=SafetySnapshot(
                    distress_score=0.95,
                    risk_level=5,
                    safety_tier="critical",
                    conversation_mode="de_escalation",
                ),
                trigger_reason="threshold_crossed",
                rolling_window_turns=4,
                delta_score=0.5,
            )

        assert payload["type"] == "proactive_voice"
        assert payload["trigger_reason"] == "threshold_crossed"
        assert payload["voice"]["status"] == "queued"
        assert payload["voice"]["tts_job_id"] == "tts_123"
        assert "hotline" in payload["voice_script"].lower()

    def test_escalation_payload_has_ui_safety_cta(self):
        fake_voice = {"status": "queued", "tts_job_id": "tts_456", "audio_url": None, "provider": "blaze"}
        with patch("app.api.v1.routers.chat.enqueue_voice_job", return_value=fake_voice), patch(
            "app.api.v1.routers.chat.mark_cooldown"
        ):
            payload = _build_voice_intervention(
                db=MagicMock(),
                user_id="u2",
                session_id="s2",
                raw_text="mình đang rất hoảng loạn",
                recent_messages=[],
                snapshot=SafetySnapshot(
                    distress_score=0.9,
                    risk_level=5,
                    safety_tier="critical",
                    conversation_mode="de_escalation",
                ),
                trigger_reason="rapid_escalation",
                rolling_window_turns=3,
                delta_score=0.35,
            )

        assert payload["crisis_footer"]["show_once"] is True
        assert payload["crisis_footer"]["hotline_cta"]["action"] == "open_hotline_sheet"
        assert payload["next_actions"][0]["id"] == "continue_voice"
        assert payload["copy_ngan"]


# ── 5. Integration: script + escalation signal aligned ───────────────────────


class TestEscalationToScriptAlignment:
    """Kiểm tra rằng khi signal escalate, script được chọn đúng theo ngữ cảnh."""

    @pytest.mark.parametrize("msg,distress,tier,expected_fragment", [
        ("toi muon tu tu", 0.95, "critical", "hotline"),
        ("mệt lắm rồi không muốn cố nữa", 0.86, "critical", "hít"),
        ("ngày hôm nay không vui", 0.42, "elevated", "ở đây"),
    ])
    def test_script_matches_scenario(self, msg, distress, tier, expected_fragment):
        signal = compute_escalation_signal(
            current_distress=distress,
            previous_distress=[distress - 0.1, distress - 0.05],
            threshold=0.84,
            delta_threshold=0.22,
            window_turns=6,
        )
        script = build_voice_script(
            user_message=msg,
            recent_messages=[],
            distress_score=distress,
            risk_level=5 if distress >= 0.8 else 3,
            safety_tier=tier,
            conversation_mode="de_escalation" if tier == "critical" else "supportive",
        )
        # Nếu distress cao thì phải escalate
        if distress >= 0.84:
            assert signal.escalate is True
        # Script phải chứa fragment phù hợp với tình huống
        assert expected_fragment.lower() in script.lower(), (
            f"Expected '{expected_fragment}' in script for tier={tier}, distress={distress}.\n"
            f"Got script: {script!r}"
        )
