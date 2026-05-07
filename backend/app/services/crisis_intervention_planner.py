"""
Deterministic CrisisInterventionPlan builder.

Produces structured plans with separate visible_text (chat) and voice_script (TTS).
LLM may optionally write a plan after the deterministic SOS trigger fires, but any
LLM-generated output must pass validation or fall back to this template.

Spec: serene_sos_voice_intervention_plan.md §2, §3
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Schema ──────────────────────────────────────────────────────────────────


class CrisisActionCard(BaseModel):
    id: str
    type: Literal[
        "voice_grounding",
        "breathing_timer",
        "trusted_contact",
        "hotline",
        "clinic_map",
        "video_grounding",
        "continue_chat",
    ]
    title: str = Field(max_length=80)
    description: str = Field(max_length=180)
    action: str
    route: str | None = None
    priority: int = Field(ge=0, le=100)


class CrisisInterventionPlan(BaseModel):
    visible_text: str = Field(min_length=1, max_length=500)
    voice_script: str = Field(min_length=10, max_length=1200)
    action_cards: list[CrisisActionCard] = Field(default_factory=list, max_length=3)
    follow_up_question: str = Field(min_length=1, max_length=180)
    safety_reason_codes: list[str] = Field(default_factory=list, max_length=8)
    should_enqueue_voice: bool = True
    source: Literal["llm", "fallback_template"] = "fallback_template"


# ─── Curated action cards ─────────────────────────────────────────────────────

_CARD_BREATHING = CrisisActionCard(
    id="breathing_timer_478",
    type="breathing_timer",
    title="Hít thở 4-7-8",
    description="Hít vào 4 giây, giữ 7, thở ra 8 — giúp hạ nhịp tim ngay.",
    action="start_breathing_timer",
    priority=90,
)

_CARD_HOTLINE = CrisisActionCard(
    id="hotline_cta",
    type="hotline",
    title="Gọi đường dây hỗ trợ",
    description="Đường dây miễn phí, bảo mật, 24/7 — nghe giọng người thật giúp ích nhiều.",
    action="open_hotline_sheet",
    priority=80,
)

_CARD_CONTINUE = CrisisActionCard(
    id="continue_chat",
    type="continue_chat",
    title="Tiếp tục nói chuyện",
    description="Mình vẫn ở đây — kể cho mình nghe điều bạn đang cảm thấy.",
    action="continue_chat",
    priority=50,
)

_CARD_GROUNDING_VIDEO = CrisisActionCard(
    id="grounding_video",
    type="video_grounding",
    title="Bài tập 5-4-3-2-1",
    description="Kỹ thuật grounding nhẹ nhàng để đưa tâm trí về khoảnh khắc hiện tại.",
    action="open_grounding_video",
    route="/serene/exercises",
    priority=60,
)

# Default 3-card set used by the fallback plan
_DEFAULT_ACTION_CARDS = [_CARD_BREATHING, _CARD_HOTLINE, _CARD_CONTINUE]

# ─── Voice script pool ────────────────────────────────────────────────────────

_VOICE_SCRIPTS = [
    (
        "Mình ở đây với bạn. "
        "Hít thở cùng mình nhé: hít vào 4 giây, giữ 4 giây, thở ra 6 giây. "
        "Bạn không một mình."
    ),
    (
        "Mình vẫn ở đây cùng bạn. "
        "Cảm ơn bạn đã tin tưởng mình. "
        "Hãy thử hít thở sâu một lần nữa cùng mình nhé. "
        "Mình lắng nghe từng điều bạn chia sẻ."
    ),
    (
        "Bạn rất can đảm. Mình ở đây. "
        "Hãy đặt tay lên ngực và hít thở chậm rãi cùng mình. "
        "Bạn đã vượt qua được đến đây, và mình tin bạn sẽ tiếp tục được."
    ),
]

_VOICE_SCRIPT_ALONE = (
    "Mình ở đây cùng bạn. "
    "Bạn không một mình. "
    "Hãy hít thở sâu và kể cho mình nghe — mình lắng nghe từng điều bạn nói."
)

# ─── Validation constants ─────────────────────────────────────────────────────

_ALLOWED_ACTIONS = {
    "play_voice_grounding",
    "start_breathing_timer",
    "open_hotline_sheet",
    "open_clinic_map",
    "open_grounding_video",
    "continue_chat",
}

_FORBIDDEN_CONTENT_PATTERNS = [
    re.compile(r"\b\d{4,}\b"),              # invented multi-digit numbers (potential phone numbers)
    re.compile(r"\b(diagnos|chẩn đoán)\b", re.IGNORECASE),
    re.compile(r"\b(tỉ lệ|xác suất|probability|chance of)\b", re.IGNORECASE),
]

# Similarity threshold: if visible_text and voice_script overlap too much, reject.
_SIMILARITY_THRESHOLD = 0.65


def _text_similarity(a: str, b: str) -> float:
    """Cheap token-overlap Jaccard similarity."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    inter = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return inter / union if union else 0.0


# ─── Fallback plan builder ────────────────────────────────────────────────────


def build_fallback_crisis_plan(
    *,
    user_message: str = "",
    recent_messages: list[dict] | None = None,
    persona_id: str = "default",
    distress_score: float = 0.9,
    risk_level: int = 2,
    safety_tier: str = "critical",
    session_sos_count: int = 0,
    reason_codes: list[str] | None = None,
    is_alone: bool = False,
    should_enqueue_voice: bool = True,
) -> CrisisInterventionPlan:
    """Build a deterministic crisis plan — no LLM involved."""
    del recent_messages, persona_id, distress_score, risk_level, safety_tier  # reserved

    # visible_text: short, reassuring, 1-3 sentences
    if is_alone:
        visible_text = (
            "Mình nghe bạn đang một mình và điều đó có thể rất nặng nề lúc này. "
            "Bạn không phải mang điều này một mình — mình đang ở đây."
        )
        voice_script = _VOICE_SCRIPT_ALONE
    else:
        _visible_variants = [
            "Mình nghe bạn, và mình đang ở đây với bạn ngay lúc này. Bạn không cần đối mặt với điều này một mình.",
            "Mình vẫn ở đây cùng bạn. Cảm ơn bạn đã tin tưởng mình với điều này.",
            "Bạn đã rất can đảm khi chia sẻ. Mình ở đây và lắng nghe từng điều bạn nói.",
        ]
        idx = min(session_sos_count, len(_visible_variants) - 1)
        visible_text = _visible_variants[idx]
        voice_script = _VOICE_SCRIPTS[min(session_sos_count, len(_VOICE_SCRIPTS) - 1)]

    follow_up = (
        "Bạn đang cảm thấy thế nào ngay lúc này?"
        if session_sos_count == 0
        else "Điều gì đang làm bạn khó thở nhất ngay lúc này?"
    )

    return CrisisInterventionPlan(
        visible_text=visible_text,
        voice_script=voice_script,
        action_cards=_DEFAULT_ACTION_CARDS,
        follow_up_question=follow_up,
        safety_reason_codes=reason_codes or ["sos_gate_triggered"],
        should_enqueue_voice=should_enqueue_voice,
        source="fallback_template",
    )


# ─── Safety validator ─────────────────────────────────────────────────────────


def validate_crisis_plan(plan: CrisisInterventionPlan) -> CrisisInterventionPlan:
    """
    Validate an LLM-generated CrisisInterventionPlan.
    Returns the plan unchanged if it passes; raises ValueError on critical issues.
    Spec: serene_sos_voice_intervention_plan.md §3
    """
    # 1. Length checks (Pydantic already enforces min/max, but belt-and-suspenders)
    if len(plan.visible_text) > 500:
        raise ValueError("visible_text exceeds 500 chars")
    if not (10 <= len(plan.voice_script) <= 1200):
        raise ValueError(f"voice_script length {len(plan.voice_script)} out of [10, 1200]")

    # 2. Similarity guard
    sim = _text_similarity(plan.visible_text, plan.voice_script)
    if sim >= _SIMILARITY_THRESHOLD:
        raise ValueError(f"visible_text and voice_script too similar (similarity={sim:.2f})")

    # 3. Max action cards
    if len(plan.action_cards) > 3:
        raise ValueError("action_cards must have at most 3 entries")

    # 4. Action allowlist + route prefix
    for card in plan.action_cards:
        if card.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Disallowed action: {card.action!r}")
        if card.route is not None and not card.route.startswith("/serene/"):
            raise ValueError(f"card.route must start with /serene/ — got {card.route!r}")

    # 5. Forbidden content patterns
    combined = f"{plan.visible_text} {plan.voice_script}"
    for pat in _FORBIDDEN_CONTENT_PATTERNS:
        if pat.search(combined):
            raise ValueError(f"Forbidden content pattern matched: {pat.pattern!r}")

    return plan


# ─── Backward-compat aliases used by existing callers ────────────────────────


def build_fallback_plan(
    visible_text: str,
    *,
    is_alone: bool = False,
    session_sos_count: int = 0,
    safety_reason_codes: list[str] | None = None,
    should_enqueue_voice: bool = True,
) -> CrisisInterventionPlan:
    """Backward-compat wrapper. Prefer build_fallback_crisis_plan() for new call sites."""
    return build_fallback_crisis_plan(
        user_message="",
        is_alone=is_alone,
        session_sos_count=session_sos_count,
        reason_codes=safety_reason_codes,
        should_enqueue_voice=should_enqueue_voice,
    )
