"""Tests for ContextPackBuilder completeness, fallback, and compaction."""

from __future__ import annotations

import pytest

from app.services.context_pack_builder import ContextPackBuilder
from app.services.schemas.contracts import SafetyPolicyDecision


def _make_policy() -> SafetyPolicyDecision:
    return SafetyPolicyDecision(
        policy_action="allow",
        risk_level=0,
        distress_score=0.0,
        persona_style_strength=1.0,
    )


def _make_builder() -> ContextPackBuilder:
    return ContextPackBuilder(timeout_ms=300)


RECENT = [{"role": "user", "content": "hello"}]


# ---------------------------------------------------------------------------
# 1. All providers populated → complete pack
# ---------------------------------------------------------------------------

def test_all_providers_populated_returns_complete_pack():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: {"key": "val"},
        onboarding_provider=lambda: {"step": 1},
        mood_provider=lambda: {"mood": "happy"},
        nutrition_provider=lambda: {"calories": 2000},
        screening_provider=lambda: {
            "phq9_score": 5,
            "gad7_score": 3,
            "phq9_band": "mild",
            "gad7_band": "minimal",
        },
        resource_candidates_provider=lambda: [
            {
                "resource_id": f"r{i}",
                "title": f"Resource {i}",
                "why_this": "relevant",
            }
            for i in range(3)
        ],
        persona_provider=lambda: {"selected": "default"},
    )

    assert pack.mood_context is not None
    assert pack.nutrition_context is not None
    assert pack.screening_summary is not None
    assert "phq9_score" in pack.screening_summary
    assert pack.active_memory is not None
    assert pack.onboarding_summary is not None
    assert pack.persona_context is not None
    assert isinstance(pack.resource_candidates, list)


# ---------------------------------------------------------------------------
# 2. Failing provider → None field + reason recorded
# ---------------------------------------------------------------------------

def test_failing_provider_returns_none_and_records_reason():
    builder = _make_builder()

    def bad_mood():
        raise RuntimeError("db unavailable")

    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=bad_mood,
        nutrition_provider=lambda: None,
        screening_provider=lambda: None,
        resource_candidates_provider=lambda: [],
        persona_provider=lambda: None,
    )

    assert pack.mood_context is None
    assert "mood" in builder.last_fallback_reasons


# ---------------------------------------------------------------------------
# 3. Screening compaction strips internal/extra fields
# ---------------------------------------------------------------------------

def test_screening_summary_compact_strips_internal_fields():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=lambda: None,
        nutrition_provider=lambda: None,
        screening_provider=lambda: {
            "phq9_score": 8,
            "gad7_score": 6,
            "phq9_band": "moderate",
            "gad7_band": "mild",
            "raw_answers": [1, 2, 3, 0],
            "clinical_notes": "internal note",
        },
        resource_candidates_provider=lambda: [],
        persona_provider=lambda: None,
    )

    assert pack.screening_summary is not None
    assert "raw_answers" not in pack.screening_summary
    assert "clinical_notes" not in pack.screening_summary


# ---------------------------------------------------------------------------
# 4. Empty screening dict → None (not empty dict)
# ---------------------------------------------------------------------------

def test_missing_phq9_gad7_returns_none_not_empty_dict():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=lambda: None,
        nutrition_provider=lambda: None,
        screening_provider=lambda: {},
        resource_candidates_provider=lambda: [],
        persona_provider=lambda: None,
    )

    assert pack.screening_summary is None


# ---------------------------------------------------------------------------
# 5. Resource candidates capped at five
# ---------------------------------------------------------------------------

def test_resource_candidates_capped_at_five():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=lambda: None,
        nutrition_provider=lambda: None,
        screening_provider=lambda: None,
        resource_candidates_provider=lambda: [
            {
                "resource_id": f"r{i}",
                "title": f"Resource {i}",
                "why_this": "relevant",
            }
            for i in range(10)
        ],
        persona_provider=lambda: None,
    )

    assert len(pack.resource_candidates) <= 5


# ---------------------------------------------------------------------------
# 6. Both phq9 and gad7 fields preserved after compaction
# ---------------------------------------------------------------------------

def test_screening_phq9_and_gad7_both_preserved():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=lambda: None,
        nutrition_provider=lambda: None,
        screening_provider=lambda: {
            "phq9_score": 10,
            "gad7_score": 8,
            "phq9_band": "moderate",
            "gad7_band": "mild",
        },
        resource_candidates_provider=lambda: [],
        persona_provider=lambda: None,
    )

    assert pack.screening_summary is not None
    assert pack.screening_summary["phq9_score"] == 10
    assert pack.screening_summary["gad7_score"] == 8
    assert pack.screening_summary["phq9_band"] == "moderate"
    assert pack.screening_summary["gad7_band"] == "mild"


# ---------------------------------------------------------------------------
# 7. Persona context passed through unchanged
# ---------------------------------------------------------------------------

def test_persona_context_passed_through():
    builder = _make_builder()
    pack = builder.build(
        safety_policy=_make_policy(),
        recent_messages=RECENT,
        active_memory_provider=lambda: None,
        onboarding_provider=lambda: None,
        mood_provider=lambda: None,
        nutrition_provider=lambda: None,
        screening_provider=lambda: None,
        resource_candidates_provider=lambda: [],
        persona_provider=lambda: {"selected": "hau_luong"},
    )

    assert pack.persona_context is not None
    assert pack.persona_context["selected"] == "hau_luong"
