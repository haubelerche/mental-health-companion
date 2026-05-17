"""
Unit tests for analyst_sanitizer.

Verifies that:
1. AnalystBundle with diagnosis terms is sanitized before reaching FriendNode.
2. AnalystBundle with risk indicators does not reach FriendNode raw.
3. Dashboard safe output does not expose internal rationale or clinical labels.
4. Rewrite logic converts clinical labels to non-clinical phrasing.
5. assert_no_clinical_labels raises on diagnosis content.
"""
import pytest

from app.services.analyst_sanitizer import (
    assert_no_clinical_labels,
    sanitize_analyst_bundle_for_dashboard,
    sanitize_analyst_bundle_for_friend_context,
)
from app.services.schemas.contracts import AnalystBundle


def _make_bundle(**kwargs) -> AnalystBundle:
    defaults = dict(
        user_id="usr_test",
        time_window={"start": "2026-05-01", "end": "2026-05-16"},
        confidence="medium",
    )
    return AnalystBundle(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# FriendNode context sanitizer tests
# ---------------------------------------------------------------------------

class TestFriendContextSanitizer:
    def test_diagnosis_terms_removed_from_emotions(self):
        bundle = _make_bundle(dominant_emotions=["bạn bị rối loạn lo âu", "buồn"])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        emotions = result.get("dominant_emotions", [])
        assert "bạn bị rối loạn lo âu" not in emotions
        # "buồn" should remain (safe)
        assert "buồn" in emotions

    def test_disorder_label_rewritten_not_removed(self):
        bundle = _make_bundle(dominant_emotions=["rối loạn lo âu mức cao"])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        emotions = result.get("dominant_emotions", [])
        # Should be rewritten to non-clinical
        text = " ".join(emotions)
        assert "rối loạn lo âu" not in text.lower()
        assert "lo lắng" in text.lower() or "lo âu kéo dài" in text.lower()

    def test_coping_preferences_pass_through(self):
        bundle = _make_bundle(coping_preferences=["viết nhật ký", "đi bộ"])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        assert result.get("coping_preferences") == ["viết nhật ký", "đi bộ"]

    def test_clinical_triggers_rewritten(self):
        bundle = _make_bundle(recurring_triggers=["MDD episode", "học tập áp lực"])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        triggers = result.get("recurring_triggers", [])
        text = " ".join(triggers)
        assert "MDD" not in text
        assert "học tập áp lực" in text

    def test_evidence_refs_stripped(self):
        bundle = _make_bundle(evidence_refs=["jsonl://corpus/case_001", "jsonl://corpus/case_002"])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        assert "evidence_refs" not in result

    def test_cognitive_patterns_stripped(self):
        bundle = _make_bundle(cognitive_patterns=[{"type": "catastrophizing", "severity": "high"}])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        assert "cognitive_patterns" not in result

    def test_nutrition_patterns_stripped(self):
        bundle = _make_bundle(nutrition_patterns=[{"observation": "bỏ bữa sáng 5/7 ngày"}])
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        assert "nutrition_patterns" not in result

    def test_confidence_stripped(self):
        bundle = _make_bundle(confidence="high")
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        assert "confidence" not in result

    def test_empty_bundle_returns_empty_dict(self):
        bundle = _make_bundle()
        result = sanitize_analyst_bundle_for_friend_context(bundle)
        # Minimal bundle with no content should return minimal/empty result
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Dashboard sanitizer tests
# ---------------------------------------------------------------------------

class TestDashboardSanitizer:
    def test_severity_band_derived_from_confidence(self):
        bundle = _make_bundle(confidence="high")
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert result["severity_band"] == "elevated"

    def test_medium_confidence_maps_to_moderate(self):
        bundle = _make_bundle(confidence="medium")
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert result["severity_band"] == "moderate"

    def test_evidence_count_correct(self):
        bundle = _make_bundle(evidence_refs=["ref1", "ref2", "ref3"])
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert result["evidence_count"] == 3

    def test_no_cognitive_patterns_in_dashboard(self):
        bundle = _make_bundle(cognitive_patterns=[{"type": "black_white_thinking"}])
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert "cognitive_patterns" not in result

    def test_no_nutrition_patterns_in_dashboard(self):
        bundle = _make_bundle(nutrition_patterns=[{"observation": "skip breakfast"}])
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert "nutrition_patterns" not in result

    def test_no_evidence_refs_in_dashboard(self):
        bundle = _make_bundle(evidence_refs=["jsonl://corpus/001"])
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert "evidence_refs" not in result

    def test_no_time_window_in_dashboard(self):
        bundle = _make_bundle()
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert "time_window" not in result

    def test_no_user_id_in_dashboard(self):
        bundle = _make_bundle()
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        assert "user_id" not in result

    def test_caller_provided_summary_used(self):
        bundle = _make_bundle()
        result = sanitize_analyst_bundle_for_dashboard(bundle, user_safe_summary="Dấu hiệu căng thẳng nhẹ")
        assert result["user_safe_summary"] == "Dấu hiệu căng thẳng nhẹ"

    def test_default_summary_not_clinical(self):
        bundle = _make_bundle(dominant_emotions=["rối loạn lo âu"])
        result = sanitize_analyst_bundle_for_dashboard(bundle)
        summary = result.get("user_safe_summary", "")
        assert "rối loạn lo âu" not in summary.lower()


# ---------------------------------------------------------------------------
# assert_no_clinical_labels
# ---------------------------------------------------------------------------

class TestAssertNoClinicalLabels:
    def test_raises_on_diagnosis_phrase(self):
        with pytest.raises(AssertionError, match="Clinical label detected"):
            assert_no_clinical_labels({"text": "bạn bị trầm cảm nặng"})

    def test_raises_on_mdd(self):
        with pytest.raises(AssertionError):
            assert_no_clinical_labels({"emotion": "MDD episode ongoing"})

    def test_passes_for_clean_data(self):
        # Should not raise
        assert_no_clinical_labels({"text": "Bạn đang lo lắng nhiều, điều đó dễ hiểu."})

    def test_passes_for_empty(self):
        assert_no_clinical_labels({})
