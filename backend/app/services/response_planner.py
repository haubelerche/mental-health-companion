"""ResponsePlan construction and deterministic repair for Vietnamese chat quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.emotional_state_detector import detect_emotional_state
from app.services.fewshot_selector import FewShotExample, select_fewshots
from app.services.interaction_need_classifier import InteractionNeed, classify_interaction_need
from app.services.microcopy_library import contains_generic_empathy
from app.services.natural_texting_renderer import render_final_text
from app.services.safety_output_validator import count_questions
from app.services.sos_handler import _normalize_text
from app.services.vietnamese_style_controller import VietnameseStyleState, choose_vietnamese_style

RiskMode = Literal["normal", "elevated", "sos"]


@dataclass(frozen=True)
class SereneResponsePlan:
    risk_mode: RiskMode
    interaction_need: InteractionNeed
    emotional_state: str
    situation_read: str
    stance: str
    allowed_moves: list[str]
    visible_text: str
    voice_script: str | None
    follow_up_question: str | None
    action_cards: list[dict]
    forbidden_moves: list[str]
    advice_allowed: bool
    safety_mode: bool
    style_state: dict
    fewshot_examples: list[FewShotExample]


def risk_mode_for(*, distress_score: float, sos_triggered: bool = False) -> RiskMode:
    if sos_triggered or distress_score >= 0.88:
        return "sos"
    if distress_score >= 0.55:
        return "elevated"
    return "normal"



def _situation_read(user_message: str, interaction_need: InteractionNeed, emotional_state: str) -> str:
    normalized = _normalize_text(user_message)
    if interaction_need == "physical_discomfort_light_medical_boundary":
        return "user is reporting physical discomfort; respond naturally and include a light safety boundary without acting as a clinician"
    if interaction_need == "reassurance":
        return "user is asking whether their perception is wrong; reassure conditionally and separate evidence from interpretation"
    if emotional_state == "self_blame" or interaction_need == "cognitive_reframe":
        return "user is turning a painful moment into a conclusion about their worth"
    if interaction_need == "grounding":
        return "user sounds overloaded and needs a simple immediate action more than analysis"
    if interaction_need == "clarification":
        return "user wants to understand a confusing pattern without being diagnosed"
    if any(k in normalized for k in ("deadline", "han nop", "bai tap")):
        return "pressure is making the user freeze, so the response should reduce the task to one next step"
    return "user is sharing distress and needs a specific reflection before any suggestion"


def _stance_for(interaction_need: InteractionNeed, emotional_state: str) -> str:
    if interaction_need == "physical_discomfort_light_medical_boundary":
        return "take discomfort seriously; ask one concrete symptom question or suggest seeking help if severe, feverish, vomiting, or unusual"
    if interaction_need == "reassurance":
        return "the user is not treated as delusional; validate the reason they hoped while avoiding certainty about other people's intent"
    if emotional_state == "self_blame" or interaction_need == "cognitive_reframe":
        return "separate what happened from the user's global self-judgment"
    if interaction_need == "grounding":
        return "slow the turn down and offer one immediate stabilizing action"
    return "warm, specific, non-clinical, and not forced-positive"


def _allowed_moves_for(interaction_need: InteractionNeed) -> list[str]:
    moves_by_need: dict[str, list[str]] = {
        "physical_discomfort_light_medical_boundary": ["ask_one_symptom_question", "light_medical_boundary", "offer_to_listen"],
        "reassurance": ["validate", "balanced_interpretation", "reduce_self_blame", "ask_one_small_question"],
        "advice": ["validate", "one_small_next_step"],
        "problem_solving": ["validate", "one_small_next_step"],
        "clarification": ["soft_pattern_name", "avoid_diagnosis", "ask_one_small_question"],
        "grounding": ["reduce_analysis", "one_immediate_action"],
        "humor_masking_distress": ["notice_masked_distress", "stay_light_but_not_dismissive"],
        "cognitive_reframe": ["separate_fact_from_story", "reduce_self_blame"],
    }
    return moves_by_need.get(interaction_need, ["validate", "specific_reflection", "optional_one_question"])


def _fallback_visible_text(user_message: str) -> str:
    excerpt = (user_message or "").strip()[:60]
    return f"điều bạn vừa kể — {excerpt} — mình muốn hiểu thêm một chút."


def _single_question(text: str) -> str:
    if count_questions(text) <= 1:
        return text
    first_q = text.find("?")
    if first_q < 0:
        return text
    return text[: first_q + 1].strip()



def build_response_plan(
    *,
    user_message: str,
    candidate_text: str,
    distress_score: float,
    persona_id: str = "dung_luong",
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
    stripped_candidate = (candidate_text or "").strip()
    if not stripped_candidate:
        # Fixed technical-failure message — must not be context-aware so that
        # identical empty-candidate calls always produce the same output.
        visible_text = "ừ, hụt phản hồi lần này, cậu thử kể lại được không?"
    else:
        visible_text = render_final_text(stripped_candidate, style=style_state, emotional_chat=True)
        visible_text = _single_question(visible_text)
        if contains_generic_empathy(visible_text) or contains_generic_empathy(_normalize_text(visible_text)):
            visible_text = _fallback_visible_text(user_message)
    return SereneResponsePlan(
        risk_mode=risk_mode,
        interaction_need=interaction_need,
        emotional_state=emotional_state,
        situation_read=_situation_read(user_message, interaction_need, emotional_state),
        stance=_stance_for(interaction_need, emotional_state),
        allowed_moves=_allowed_moves_for(interaction_need),
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
            "quote_user_verbatim",
            "possessive_or_dependency_building_persona",
        ],
        advice_allowed=interaction_need in {"advice", "problem_solving", "grounding", "physical_discomfort_light_medical_boundary"},
        safety_mode=risk_mode == "sos",
        style_state=style_state.model_dump(),
        fewshot_examples=fewshots,
    )
