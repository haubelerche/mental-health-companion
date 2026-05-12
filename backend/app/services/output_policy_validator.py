from __future__ import annotations

import re

from app.safety.output_validator import validate_output as validate_surface_output
from app.safety.verdicts import OutputSafetyVerdict
from app.services.safety_output_validator import count_sentences, validate_serene_response
from app.services.schemas.contracts import SafetyPolicyDecision

_INTERNAL_FIELD_PATTERNS = [
    re.compile(r"\bdistress_score\b", re.IGNORECASE),
    re.compile(r"\brisk_level\b", re.IGNORECASE),
    re.compile(r"\bsafety_tier\b", re.IGNORECASE),
    re.compile(r"\breason_codes?\b", re.IGNORECASE),
]

_INTERNAL_NAME_PATTERNS = [
    re.compile(r"\bFriendAgent\b", re.IGNORECASE),
    re.compile(r"\bAnalystAgent\b", re.IGNORECASE),
    re.compile(r"\bEmpathyAdvisor\b", re.IGNORECASE),
    re.compile(r"\bCBTPatternAdvisor\b", re.IGNORECASE),
    re.compile(r"\bReflectionAdvisor\b", re.IGNORECASE),
    re.compile(r"\bStrategyResourceAdvisor\b", re.IGNORECASE),
    re.compile(r"\bNutritionSupportAdvisor\b", re.IGNORECASE),
    re.compile(r"\bRelevanceNaturalnessCritic\b", re.IGNORECASE),
]

_HARMFUL_METHOD_PATTERNS = [
    re.compile(r"\bstep\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b(use|take|mix)\b.{0,40}\b(pills|rope|knife|bleach|overdose)\b", re.IGNORECASE),
    re.compile(r"\bhang yourself\b", re.IGNORECASE),
    re.compile(r"\boverdose\b", re.IGNORECASE),
]

_UNSUPPORTED_CLINICAL_PATTERNS = [
    re.compile(r"\byou have\b.{0,30}\b(depression|anxiety disorder|bipolar|ptsd)\b", re.IGNORECASE),
    re.compile(r"\bban bi\b.{0,30}\btram cam|roi loan lo au|roi loan luong cuc\b", re.IGNORECASE),
    re.compile(r"\b(i am|i'm|toi la|minh la)\b.{0,20}\b(therapist|doctor|licensed|bac si|chuyen gia tri lieu)\b", re.IGNORECASE),
    re.compile(r"\b(diagnose|diagnosis|chan doan|dieu tri)\b.{0,30}\b(you|ban|ban dang|cau)\b", re.IGNORECASE),
]

_RAW_CLINICAL_LABEL_PATTERNS = [
    re.compile(r"\b(catastrophizing|mind_reading|self_blame|people_pleasing|helplessness_belief)\b", re.IGNORECASE),
    re.compile(r"\b(cognitive distortion|cbt pattern)\b", re.IGNORECASE),
]

_HURTFUL_OR_PROFANE_PATTERNS = [
    re.compile(r"\b(dm|dcm|vl|vcl|cc|clm|dit|du ma)\b", re.IGNORECASE),
    re.compile(r"\b(may|mày)\s+(ngu|te|vo dung|phiền|dien)\b", re.IGNORECASE),
]

_PLAYFUL_SLANG_PATTERNS = [
    re.compile(r"\b(lag|lụm|lumm|meme|não mở|deadline dí|giáo trình|marathon)\b", re.IGNORECASE),
]


def validate_final_response(
    text: str,
    *,
    surface: str = "chat",
    policy_decision: SafetyPolicyDecision | None = None,
) -> OutputSafetyVerdict:
    surface_verdict = validate_surface_output(text, surface=surface)
    if surface_verdict.verdict == "block":
        return surface_verdict

    reason_codes: list[str] = []
    flagged_fragments: list[str] = []

    for pattern in _INTERNAL_FIELD_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("internal_score_leakage")
            flagged_fragments.append(match.group(0))

    for pattern in _INTERNAL_NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("internal_actor_leakage")
            flagged_fragments.append(match.group(0))

    for pattern in _HARMFUL_METHOD_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("harmful_method_detail")
            flagged_fragments.append(match.group(0))

    for pattern in _UNSUPPORTED_CLINICAL_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("unsupported_clinical_claim")
            flagged_fragments.append(match.group(0))

    for pattern in _RAW_CLINICAL_LABEL_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("raw_counseling_label_leakage")
            flagged_fragments.append(match.group(0))

    for pattern in _HURTFUL_OR_PROFANE_PATTERNS:
        match = pattern.search(text)
        if match:
            reason_codes.append("hurtful_or_profane_persona_language")
            flagged_fragments.append(match.group(0))

    if policy_decision and float(policy_decision.persona_style_strength) < 0.3:
        for pattern in _PLAYFUL_SLANG_PATTERNS:
            match = pattern.search(text)
            if match:
                reason_codes.append("playful_slang_during_constrained_turn")
                flagged_fragments.append(match.group(0))

    if reason_codes:
        return OutputSafetyVerdict(
            verdict="block",
            reason_codes=sorted(set(reason_codes)),
            flagged_fragments=flagged_fragments,
        )

    max_sentences = 3 if policy_decision and policy_decision.policy_action == "supportive_continuation" else 4
    quality_verdict = validate_serene_response(
        text,
        require_context_anchor=True,
        max_sentences=max_sentences,
        max_questions=1,
        emotional_chat=(surface == "chat"),
    )
    if not quality_verdict.ok:
        return OutputSafetyVerdict(
            verdict="rewrite_required",
            reason_codes=quality_verdict.reason_codes,
            flagged_fragments=[],
        )

    if policy_decision and policy_decision.policy_action == "supportive_continuation" and count_sentences(text) > 3:
        return OutputSafetyVerdict(
            verdict="rewrite_required",
            reason_codes=["too_many_sentences"],
            flagged_fragments=[],
        )

    return OutputSafetyVerdict(verdict="allow", reason_codes=[], flagged_fragments=[])
