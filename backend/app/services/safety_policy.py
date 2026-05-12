from __future__ import annotations

import re

from app.core.product_constants import (
    DISTRESS_CONSTRAIN_RESPONSE_MIN,
    DISTRESS_SUPPORTIVE_CONTINUATION_MIN,
)
from app.services.schemas.contracts import SafetyPolicyDecision
from app.services.sos_handler import decide_sos_debug

_HARMFUL_INSTRUCTION_PATTERNS = [
    re.compile(r"\b(best|easy|effective)\s+way\s+to\s+(die|kill myself|hurt myself)\b", re.IGNORECASE),
    re.compile(r"\bhow\s+to\s+(kill myself|hurt myself|end my life)\b", re.IGNORECASE),
    re.compile(r"\b(cach|lam sao|huong dan)\s+(tu tu|tu lam hai|minh chet)\b", re.IGNORECASE),
    re.compile(r"\b(phuong phap|cach)\s+(chet|tu tu)\b", re.IGNORECASE),
]

_DISTRESS_DISCLOSURE_PATTERNS = [
    re.compile(r"\bi feel (empty|hopeless|numb|exhausted)\b", re.IGNORECASE),
    re.compile(r"\btoi (met|qua met|kiet suc|tuyet vong|that bai|khong on)\b", re.IGNORECASE),
    re.compile(r"\bkhong con suc nua\b", re.IGNORECASE),
    re.compile(r"\bsong de lam gi\b", re.IGNORECASE),
]


def _is_harmful_instruction_request(message: str) -> bool:
    text = (message or "").strip()
    return any(pattern.search(text) for pattern in _HARMFUL_INSTRUCTION_PATTERNS)


def _is_distress_disclosure(message: str) -> bool:
    text = (message or "").strip()
    return any(pattern.search(text) for pattern in _DISTRESS_DISCLOSURE_PATTERNS)


def evaluate_safety_policy(
    user_message: str,
    recent_user_messages: list[str] | None = None,
) -> SafetyPolicyDecision:
    debug = decide_sos_debug(user_message, recent_user_messages)
    must_avoid = [
        "diagnosis_or_disorder_probability",
        "multiple_questions",
        "robotic_safety_essay",
        "playful_romantic_tone",
    ]

    if _is_harmful_instruction_request(user_message):
        return SafetyPolicyDecision(
            policy_action="block_harmful_instruction",
            risk_level=4,
            distress_score=debug.distress_score,
            must_include=[
                "warm_refusal",
                "brief_safety_refocus",
                "offer_safe_support",
            ],
            must_avoid=must_avoid + ["harmful_method_detail"],
            persona_style_strength=0.1,
            ui_support_mode="optional_sheet",
            audit_required=True,
            reason_codes=["harmful_instruction_request", *debug.reason_codes],
        )

    if debug.sos_triggered:
        return SafetyPolicyDecision(
            policy_action="supportive_continuation",
            risk_level=5,
            distress_score=debug.distress_score,
            must_include=[
                "short_validation",
                "context_specific_reflection",
                "one_open_continuation_question",
            ],
            must_avoid=must_avoid + ["hard_stop_language"],
            persona_style_strength=0.05,
            ui_support_mode="optional_sheet",
            audit_required=True,
            reason_codes=["sos_triggered", *debug.reason_codes],
        )

    if _is_distress_disclosure(user_message) or debug.distress_score >= DISTRESS_SUPPORTIVE_CONTINUATION_MIN:
        return SafetyPolicyDecision(
            policy_action="supportive_continuation",
            risk_level=3,
            distress_score=debug.distress_score,
            must_include=[
                "short_validation",
                "context_specific_reflection",
                "one_open_continuation_question",
            ],
            must_avoid=must_avoid,
            persona_style_strength=0.2,
            ui_support_mode="optional_sheet",
            audit_required=False,
            reason_codes=["distress_disclosure_or_elevated_distress", *debug.reason_codes],
        )

    if debug.distress_score >= DISTRESS_CONSTRAIN_RESPONSE_MIN:
        return SafetyPolicyDecision(
            policy_action="constrain_response",
            risk_level=2,
            distress_score=debug.distress_score,
            must_include=["brief_reflection"],
            must_avoid=must_avoid,
            persona_style_strength=0.45,
            ui_support_mode="none",
            audit_required=False,
            reason_codes=["elevated_distress", *debug.reason_codes],
        )

    return SafetyPolicyDecision(
        policy_action="allow",
        risk_level=0,
        distress_score=debug.distress_score,
        must_include=[],
        must_avoid=[],
        persona_style_strength=1.0,
        ui_support_mode="none",
        audit_required=False,
        reason_codes=["normal_distress", *debug.reason_codes],
    )
