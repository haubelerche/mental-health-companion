"""Deterministic CrisisInterventionPlan builder.

The deterministic SOS gate decides risk. This module only renders a validated
user-facing crisis plan after that gate has fired.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
    voice_script: str = Field(min_length=80, max_length=1200)
    additional_voice_scripts: list[str] = Field(default_factory=list, max_length=3)
    follow_up_texts: list[str] = Field(default_factory=list, max_length=3)
    action_cards: list[CrisisActionCard] = Field(default_factory=list, max_length=3)
    follow_up_question: str = Field(min_length=1, max_length=180)
    safety_reason_codes: list[str] = Field(default_factory=list, max_length=8)
    should_enqueue_voice: bool = True
    source: Literal["llm", "fallback_template"] = "fallback_template"

    @property
    def all_voice_scripts(self) -> list[str]:
        scripts = [self.voice_script]
        scripts.extend(s for s in self.additional_voice_scripts if s and str(s).strip())
        return scripts


_CARD_BREATHING = CrisisActionCard(
    id="breathing_timer",
    type="breathing_timer",
    title="Thở chậm vài nhịp",
    description="Một nhịp thở ngắn, đủ để hạ bớt độ gắt của khoảnh khắc này.",
    action="start_breathing_timer",
    priority=90,
)

_CARD_HOTLINE = CrisisActionCard(
    id="hotline_cta",
    type="hotline",
    title="Mở hỗ trợ khẩn",
    description="Nếu nguy hiểm đang rất gần, mở danh sách hỗ trợ đã được chuẩn bị sẵn.",
    action="open_hotline_sheet",
    priority=70,
)

_CARD_CONTINUE = CrisisActionCard(
    id="continue_chat",
    type="continue_chat",
    title="Kể tiếp từng chút",
    description="Không cần mạch lạc; chỉ chọn phần dễ nói nhất ngay lúc này.",
    action="continue_chat",
    priority=50,
)

_DEFAULT_ACTION_CARDS = [_CARD_BREATHING, _CARD_HOTLINE, _CARD_CONTINUE]

_VOICE_SCRIPTS = [
    (
        "Bạn thử đặt điện thoại xuống thấp hơn một chút. Đặt hai chân chạm sàn. "
        "Hít vào nhẹ thôi, rồi thở ra dài hơn một nhịp. Chưa cần nghĩ đến chuyện tiếp theo; "
        "chỉ ở lại với mình trong vài hơi thở này."
    ),
    (
        "Mình sẽ đi chậm. Nhìn quanh và gọi thầm tên một vật ở gần bạn. "
        "Chạm tay vào mặt bàn hoặc áo của mình. Hít vào một nhịp ngắn, thở ra chậm hơn. "
        "Việc duy nhất lúc này là giữ bạn an toàn thêm một phút."
    ),
    (
        "Nếu có thể, bạn ngồi xuống hoặc tựa lưng vào đâu đó. Nới lỏng hàm, thả vai xuống. "
        "Mình đếm cùng bạn ba nhịp thở chậm; trong lúc này chưa cần giải thích gì cả."
    ),
]

_VOICE_SCRIPT_ALONE = (
    "Bạn thử nhìn quanh phòng và chọn một điểm cố định để nhìn. "
    "Đặt một tay lên ngực hoặc lên mặt bàn. Hít vào rất nhẹ, thở ra chậm hơn một chút. "
    "Lúc này mình chỉ cần bạn ở lại thêm vài nhịp."
)

_VISIBLE_VARIANTS = [
    "Mình nghe thấy lúc này đang rất nặng. Trước mắt mình chỉ muốn bạn ở lại đây với mình thêm một chút.",
    "Đoạn này nguy hiểm cho bạn rồi, nên mình sẽ nói thật chậm. Mình ở đây, và mình muốn mình cùng làm một việc nhỏ trước.",
    "Mình nghe rõ cảm giác tuyệt vọng trong câu bạn vừa viết. Chưa cần quyết gì lúc này; mình giữ nhịp với bạn từng chút.",
]

_VISIBLE_ALONE = (
    "Mình nghe bạn đang một mình và đoạn này không nhẹ chút nào. "
    "Trước mắt mình chỉ muốn giữ bạn ở lại thêm một chút, từng nhịp thôi."
)

_FOLLOW_UPS = [
    "Bạn chỉ cần nói một chút thôi: lúc này phần nào đang nghẹn nhất?",
    "Ngay bây giờ, bạn đang ở gần ai hoặc gần chỗ nào an toàn hơn không?",
    "Bạn muốn mình ở lại với phần cảm giác nào trước?",
]

_ALLOWED_ACTIONS = {
    "play_voice_grounding",
    "start_breathing_timer",
    "open_hotline_sheet",
    "open_clinic_map",
    "open_grounding_video",
    "continue_chat",
}

_FORBIDDEN_CONTENT_PATTERNS = [
    re.compile(r"\b\d{4,}\b"),
    re.compile(r"\b(diagnos|chẩn đoán|chan doan)\b", re.IGNORECASE),
    re.compile(r"\b(tỉ lệ|xác suất|probability|chance of)\b", re.IGNORECASE),
    re.compile(
        r"\b(bạn không đơn độc|ban khong don doc|mọi chuyện rồi sẽ ổn|moi chuyen roi se on|bạn rất can đảm|ban rat can dam)\b",
        re.IGNORECASE,
    ),
]
_SIMILARITY_THRESHOLD = 0.65


def _text_similarity(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


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
    """Build a deterministic crisis plan; no LLM involved."""
    del user_message, recent_messages, persona_id, distress_score, risk_level, safety_tier
    idx = min(max(int(session_sos_count or 0), 0), len(_VISIBLE_VARIANTS) - 1)
    visible_text = _VISIBLE_ALONE if is_alone else _VISIBLE_VARIANTS[idx]
    voice_script = _VOICE_SCRIPT_ALONE if is_alone else _VOICE_SCRIPTS[idx]
    follow_up = _FOLLOW_UPS[min(idx, len(_FOLLOW_UPS) - 1)]
    return CrisisInterventionPlan(
        visible_text=visible_text,
        voice_script=voice_script,
        action_cards=_DEFAULT_ACTION_CARDS,
        follow_up_question=follow_up,
        safety_reason_codes=reason_codes or ["sos_gate_triggered"],
        should_enqueue_voice=should_enqueue_voice,
        source="fallback_template",
    )


def validate_crisis_plan(plan: CrisisInterventionPlan) -> CrisisInterventionPlan:
    if len(plan.visible_text) > 500:
        raise ValueError("visible_text exceeds 500 chars")
    if not (80 <= len(plan.voice_script) <= 1200):
        raise ValueError(f"voice_script length {len(plan.voice_script)} out of [80, 1200]")
    if _text_similarity(plan.visible_text, plan.voice_script) >= _SIMILARITY_THRESHOLD:
        raise ValueError("visible_text and voice_script too similar")
    if len(plan.action_cards) > 3:
        raise ValueError("action_cards must have at most 3 entries")
    for card in plan.action_cards:
        if card.action not in _ALLOWED_ACTIONS:
            raise ValueError(f"Disallowed action: {card.action!r}")
        if card.route is not None and not card.route.startswith("/serene/"):
            raise ValueError(f"card.route must start with /serene/; got {card.route!r}")
    combined = f"{plan.visible_text} {plan.voice_script}"
    for pattern in _FORBIDDEN_CONTENT_PATTERNS:
        if pattern.search(combined):
            raise ValueError(f"Forbidden content pattern matched: {pattern.pattern!r}")
    return plan


def build_fallback_plan(
    visible_text: str,
    *,
    is_alone: bool = False,
    session_sos_count: int = 0,
    safety_reason_codes: list[str] | None = None,
    should_enqueue_voice: bool = True,
) -> CrisisInterventionPlan:
    """Backward-compatible wrapper. The visible_text arg is ignored intentionally."""
    del visible_text
    return build_fallback_crisis_plan(
        is_alone=is_alone,
        session_sos_count=session_sos_count,
        reason_codes=safety_reason_codes,
        should_enqueue_voice=should_enqueue_voice,
    )


_LLM_CRISIS_SYSTEM_PROMPT = """\
Bạn tạo CrisisInterventionPlan cho app hỗ trợ tinh thần tiếng Việt sau khi deterministic SOS gate đã kích hoạt.
Trả về JSON một dòng, chỉ gồm visible_text, voice_script, follow_up_question.

Luật bắt buộc:
- visible_text: 1-3 câu, ngắn, bám chi tiết người dùng, không khẩu hiệu.
- voice_script: khác visible_text, hướng dẫn một hành động grounding cụ thể ngay lúc này, 80-260 ký tự.
- follow_up_question: đúng một câu hỏi nhỏ, không tra khảo.
- Không chẩn đoán, không mô tả phương thức gây hại, không bịa hotline/số điện thoại/URL.
- Không dùng: "bạn không đơn độc", "mọi chuyện rồi sẽ ổn", "bạn rất can đảm", "hãy bình tĩnh".
- Persona chỉ ảnh hưởng rất nhẹ; safety override luôn thắng.
""".strip()


async def build_llm_crisis_plan(
    *,
    user_message: str,
    session_sos_count: int = 0,
    is_alone: bool = False,
    openai_api_key: str | None = None,
) -> CrisisInterventionPlan:
    if not openai_api_key:
        raise ValueError("openai_api_key not set")

    context_note = f"session_sos_count={int(session_sos_count or 0)}; is_alone={bool(is_alone)}"
    user_payload = f"{context_note}\nTin nhắn người dùng: {user_message}"

    from openai import OpenAI
    from app.core.config import get_settings as _get_settings

    model = _get_settings().openai_model_analyst or "gpt-4o-mini"
    client = OpenAI(api_key=openai_api_key, timeout=2.5)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.7,
        max_tokens=320,
        messages=[
            {"role": "system", "content": _LLM_CRISIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    parsed = json.loads(raw)

    plan = CrisisInterventionPlan(
        visible_text=str(parsed.get("visible_text") or "").strip()[:500],
        voice_script=str(parsed.get("voice_script") or "").strip()[:1200],
        action_cards=_DEFAULT_ACTION_CARDS,
        follow_up_question=str(parsed.get("follow_up_question") or "").strip()[:180],
        safety_reason_codes=["sos_gate_triggered"],
        should_enqueue_voice=True,
        source="llm",
    )
    return validate_crisis_plan(plan)


async def build_llm_crisis_messages(
    *,
    user_message: str,
    session_sos_count: int = 0,
    is_alone: bool = False,
    openai_api_key: str | None = None,
) -> tuple[list[str], list[str]]:
    plan = await build_llm_crisis_plan(
        user_message=user_message,
        session_sos_count=session_sos_count,
        is_alone=is_alone,
        openai_api_key=openai_api_key,
    )
    return [plan.follow_up_question], plan.all_voice_scripts
