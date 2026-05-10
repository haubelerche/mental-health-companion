"""ResponsePlan construction and deterministic repair for Vietnamese chat quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.emotional_state_detector import detect_emotional_state
from app.services.fewshot_selector import FewShotExample, select_fewshots
from app.services.interaction_need_classifier import InteractionNeed, classify_interaction_need
from app.services.microcopy_library import GRIEF_ANCHORS, OVERWHELM_ANCHORS, SELF_BLAME_ANCHORS
from app.services.natural_texting_renderer import render_final_text
from app.services.safety_output_validator import count_questions, validate_serene_response
from app.services.sos_handler import _normalize_text
from app.services.vietnamese_style_controller import VietnameseStyleState, choose_vietnamese_style

RiskMode = Literal["normal", "elevated", "sos"]


@dataclass(frozen=True)
class SereneResponsePlan:
    risk_mode: RiskMode
    interaction_need: InteractionNeed
    emotional_state: str
    visible_text: str
    voice_script: str | None
    follow_up_question: str | None
    action_cards: list[dict]
    forbidden_moves: list[str]
    style_state: dict
    fewshot_examples: list[FewShotExample]


def risk_mode_for(*, distress_score: float, sos_triggered: bool = False) -> RiskMode:
    if sos_triggered or distress_score >= 0.88:
        return "sos"
    if distress_score >= 0.55:
        return "elevated"
    return "normal"


def _extract_context_anchor(user_message: str, emotional_state: str) -> str:
    normalized = _normalize_text(user_message)
    if emotional_state == "grief_loss":
        if "me" in normalized:
            return "chuyện liên quan đến mẹ"
        if "ba" in normalized or "bo" in normalized or "cha" in normalized:
            return "chuyện liên quan đến ba"
        if "nguoi than" in normalized:
            return "mất một người thân"
        return "mất mát này"
    if "mat ngu" in normalized or "khong ngu" in normalized:
        return "việc mất ngủ"
    if "gia dinh" in normalized:
        return "áp lực từ gia đình"
    if "tien" in normalized or "no" in normalized or "luong" in normalized:
        return "gánh nặng tiền bạc"
    if "co don" in normalized or "mot minh" in normalized:
        return "cảm giác một mình"
    if "chia tay" in normalized or "bo da" in normalized:
        return "chuyện chia tay"
    if "deadline" in normalized or "han nop" in normalized:
        return "deadline đang dí sát"
    if "kem coi" in normalized or "vo dung" in normalized:
        return "cảm giác kém cỏi"
    return "điều bạn vừa kể"


def _single_question(text: str) -> str:
    if count_questions(text) <= 1:
        return text
    first_q = text.find("?")
    if first_q < 0:
        return text
    return text[: first_q + 1].strip()


def _fallback_visible_text(user_message: str, *, emotional_state: str, interaction_need: InteractionNeed) -> str:
    anchor = _extract_context_anchor(user_message, emotional_state)
    if interaction_need == "grief":
        lead = GRIEF_ANCHORS[0]
        return (
            f"{lead} mình nghe {anchor} đang làm mọi thứ như rơi xuống, không phải chỉ là buồn thoáng qua. "
            "không cần kể cho thật mạch lạc đâu; lúc này phần nào đang nghẹn nhất?"
        )
    if emotional_state == "self_blame":
        return (
            f"{SELF_BLAME_ANCHORS[0]} với {anchor}, phản ứng rối và tự trách như vậy là dễ hiểu. "
            "mình đi chậm thôi; phần nào đang nặng nhất ngay lúc này?"
        )
    if interaction_need == "grounding":
        return (
            f"{OVERWHELM_ANCHORS[0]} mình nghe {anchor} đang làm bạn quá tải. "
            "bạn thử thở ra dài hơn một nhịp rồi nói cho mình phần dễ nói nhất được không?"
        )
    return (
        f"ừ, mình nghe {anchor} đang đè lên bạn khá nặng. "
        "mình chưa vội khuyên gì dài; phần nào đang khó chịu nhất lúc này?"
    )


def build_response_plan(
    *,
    user_message: str,
    candidate_text: str,
    distress_score: float,
    persona_id: str = "ban_than",
    sos_triggered: bool = False,
) -> SereneResponsePlan:
    risk_mode = risk_mode_for(distress_score=distress_score, sos_triggered=sos_triggered)
    interaction_need = classify_interaction_need(user_message, distress_score=distress_score, sos_triggered=sos_triggered)
    emotional_state = detect_emotional_state(user_message, distress_score=distress_score)
    style_state: VietnameseStyleState = choose_vietnamese_style(
        persona_id=persona_id,
        distress_score=distress_score,
        risk_mode=risk_mode,
    )
    fewshots = select_fewshots(
        risk_mode=risk_mode,
        interaction_need=interaction_need,
        distress_score=distress_score,
        user_tone="serious" if distress_score >= 0.55 else "casual",
        persona_id=persona_id,
    )
    visible_text = render_final_text(
        (candidate_text or "").strip(),
        style=style_state,
        emotional_chat=True,
    )
    verdict = validate_serene_response(
        visible_text,
        require_context_anchor=True,
        max_sentences=style_state.max_sentences,
        max_questions=style_state.max_questions,
        emotional_chat=True,
    )
    if not verdict.ok:
        visible_text = render_final_text(
            _fallback_visible_text(
                user_message,
                emotional_state=emotional_state,
                interaction_need=interaction_need,
            ),
            style=style_state,
            emotional_chat=True,
        )
    visible_text = _single_question(visible_text)
    return SereneResponsePlan(
        risk_mode=risk_mode,
        interaction_need=interaction_need,
        emotional_state=emotional_state,
        visible_text=visible_text,
        voice_script=None,
        follow_up_question=None,
        action_cards=[],
        forbidden_moves=[
            "generic_empathy_loop",
            "forced_positivity",
            "diagnosis",
            "multiple_questions",
            "playful_romantic_in_safety",
        ],
        style_state=style_state.model_dump(),
        fewshot_examples=fewshots,
    )
