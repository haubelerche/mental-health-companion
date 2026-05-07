"""
Deterministic CrisisInterventionPlan builder.

Produces structured plans with separate visible_text (chat) and voice_script (TTS).
LLM may optionally write a plan after the deterministic SOS trigger fires, but any
LLM-generated output must pass validation or fall back to this template.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CrisisInterventionPlan(BaseModel):
    visible_text: str
    voice_script: str  # shorter, plain text, no markdown/URLs — TTS only
    action_cards: list[dict]
    follow_up_question: str
    safety_reason_codes: list[str]
    should_enqueue_voice: bool
    source: Literal["llm", "fallback_template"]


_VOICE_SCRIPTS = [
    (
        "Mình ở đây với bạn. "
        "Hít thở cùng mình nhé: hít vào 4 giây, giữ 4 giây, thở ra 6 giây. "
        "Bạn không một mình."
    ),
    (
        "Mình vẫn ở đây cùng bạn. "
        "Cảm ơn bạn đã tin tưởng mình. "
        "Hãy thử hít thở sâu một lần nữa cùng mình nhé."
    ),
    (
        "Bạn rất can đảm. Mình ở đây. "
        "Hãy đặt tay lên ngực và hít thở chậm rãi cùng mình."
    ),
]

_VOICE_SCRIPT_ALONE = (
    "Mình ở đây cùng bạn. "
    "Bạn không một mình. "
    "Hãy hít thở sâu và kể cho mình nghe."
)

_ACTION_CARDS = [
    {"type": "grounding", "id": "grounding_54321", "label": "Bài tập 5-4-3-2-1"},
    {"type": "breathing", "id": "breath_478", "label": "Hít thở 4-7-8"},
    {"type": "hotline", "id": "hotline_cta", "label": "Gọi đường dây hỗ trợ"},
]


def build_fallback_plan(
    visible_text: str,
    *,
    is_alone: bool = False,
    session_sos_count: int = 0,
    safety_reason_codes: list[str] | None = None,
    should_enqueue_voice: bool = True,
) -> CrisisInterventionPlan:
    """Build a deterministic crisis plan — no LLM involved."""
    if is_alone:
        voice_script = _VOICE_SCRIPT_ALONE
    else:
        idx = min(session_sos_count, len(_VOICE_SCRIPTS) - 1)
        voice_script = _VOICE_SCRIPTS[idx]

    follow_up = (
        "Bạn đang cảm thấy thế nào ngay lúc này?"
        if session_sos_count == 0
        else "Điều gì đang làm bạn khó thở nhất ngay lúc này?"
    )

    return CrisisInterventionPlan(
        visible_text=visible_text,
        voice_script=voice_script,
        action_cards=_ACTION_CARDS,
        follow_up_question=follow_up,
        safety_reason_codes=safety_reason_codes or ["sos_gate_triggered"],
        should_enqueue_voice=should_enqueue_voice,
        source="fallback_template",
    )
