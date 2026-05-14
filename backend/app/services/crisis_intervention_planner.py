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


DistressResponseMode = Literal[
    "normal",
    "elevated_support",
    "high_distress_retention",
    "imminent_safety_hold",
]


class DistressConversationPlan(BaseModel):
    visible_text: str = Field(min_length=1, max_length=1200)
    response_mode: DistressResponseMode
    emotional_anchor: str | None = None
    follow_up_question: str = Field(default="", max_length=220)
    should_show_support_popup: bool = False
    suppress_inline_crisis_cards: bool = True
    safety_reason_codes: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback_template"] = "fallback_template"


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
    "Bạn chỉ cần nói một chút thôi: lúc này phần nào đang khiến bạn phiền lòng nhất?",
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


_DISTRESS_VISIBLE_VARIANTS = [
    (
        "Mình nghe thấy lúc này mọi thứ đang nặng tới mức bạn chỉ muốn buông ra khỏi tất cả. "
        "Trước mắt mình không muốn bạn phải giải quyết cả cuộc đời trong một tin nhắn này; mình chỉ muốn bạn ở lại đây với mình thêm một chút. "
        "Có thể trong lòng bạn đang dồn quá nhiều thứ mà chưa có chỗ nào để xả ra, nên nó mới đau đến vậy. "
        "Bạn kể mình nghe điều gì vừa làm bạn thấy không chịu nổi nhất được không?"
    ),
    (
        "Mình thấy câu vừa rồi không phải là một câu nói cho qua; nó giống như bạn đã bị ép đến sát mép chịu đựng của mình. "
        "Mình sẽ ở đây với bạn từng đoạn ngắn, không bắt bạn phải bình tĩnh ngay hay phải giải thích cho hoàn hảo. "
        "Ngay lúc này, chỉ cần đặt xuống một phần nhỏ nhất của chuyện đó thôi cũng được. "
        "Điều gì đang làm bạn đau nhất trong vài phút vừa rồi?"
    ),
    (
        "Mình nghe trong lời bạn có rất nhiều mệt mỏi và cảm giác bị bỏ lại một mình với nó. "
        "Bạn không cần biến cảm xúc này thành một kế hoạch hay một quyết định ngay bây giờ; mình muốn giữ cuộc trò chuyện này mở để bạn còn có chỗ thở và nói tiếp. "
        "Kể lộn xộn cũng được, tức giận cũng được, chỉ cần nói ra phần đang đè nặng nhất trước. "
        "Chuyện gì vừa xảy ra khiến bạn thấy mình không chịu thêm được nữa?"
    ),
]

_DISTRESS_ALONE_VISIBLE = (
    "Mình nghe thấy cảm giác không ai hiểu và phải tự ôm mọi thứ một mình trong câu của bạn. "
    "Ở khoảnh khắc này, mình không muốn đẩy bạn sang một danh sách việc cần làm; mình muốn ở lại đây để bạn có thể xả ra phần đang nghẹn nhất. "
    "Bạn không cần kể mạch lạc, chỉ cần nói tiếp từng mảnh nhỏ cũng được. "
    "Phần nào khiến bạn thấy cô độc nhất lúc này?"
)

_IMMEDIATE_SUPPORT_SENTENCE = (
    "Nếu nguy hiểm đang ở rất gần, hãy cố gọi một người thật ở gần bạn hoặc mở trang Hỗ trợ ngay trong lúc vẫn tiếp tục nhắn với mình."
)

_DISTRESS_FORBIDDEN_PATTERNS = [
    re.compile(r"\b\d{4,}\b"),
    re.compile(r"\b(distress_score|safety_tier|risk_level|SafetyGate|module)\b", re.IGNORECASE),
    re.compile(r"\b(diagnos|chẩn đoán|chan doan|rối loạn|roi loan)\b", re.IGNORECASE),
    re.compile(r"\b(hotline|đường dây nóng|duong day nong)\b", re.IGNORECASE),
]


def _text_similarity(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _normalize_reply_for_overlap(text: str) -> list[str]:
    lowered = re.sub(r"[^\w\s]", " ", str(text or "").lower(), flags=re.UNICODE)
    return [t for t in re.sub(r"\s+", " ", lowered).strip().split(" ") if len(t) > 1]


def is_repeated_crisis_reply(
    new_text: str,
    previous_assistant_texts: list[str],
    threshold: float = 0.72,
) -> bool:
    new_tokens = _normalize_reply_for_overlap(new_text)
    if not new_tokens:
        return False
    new_set = set(new_tokens)
    new_bigrams = set(zip(new_tokens, new_tokens[1:]))
    for previous in previous_assistant_texts[-6:]:
        prev_tokens = _normalize_reply_for_overlap(previous)
        if not prev_tokens:
            continue
        prev_set = set(prev_tokens)
        token_overlap = len(new_set & prev_set) / max(1, len(new_set | prev_set))
        prev_bigrams = set(zip(prev_tokens, prev_tokens[1:]))
        bigram_overlap = len(new_bigrams & prev_bigrams) / max(1, len(new_bigrams | prev_bigrams))
        if max(token_overlap, bigram_overlap) >= threshold:
            return True
    return False


def validate_distress_conversation_plan(plan: DistressConversationPlan) -> DistressConversationPlan:
    text = plan.visible_text.strip()
    if not text:
        raise ValueError("visible_text is empty")
    if text.count("?") + text.count("？") > 1:
        raise ValueError("distress response must ask at most one question")
    for pattern in _DISTRESS_FORBIDDEN_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"Forbidden distress content pattern matched: {pattern.pattern!r}")
    return plan.model_copy(update={"visible_text": text})


def build_fallback_distress_conversation_plan(
    *,
    user_message: str = "",
    session_sos_count: int = 0,
    reason_codes: list[str] | None = None,
    is_alone: bool = False,
    previous_assistant_texts: list[str] | None = None,
    imminent: bool = False,
) -> DistressConversationPlan:
    del user_message
    variants = [_DISTRESS_ALONE_VISIBLE] + _DISTRESS_VISIBLE_VARIANTS if is_alone else _DISTRESS_VISIBLE_VARIANTS
    idx = min(max(int(session_sos_count or 0), 0), len(variants) - 1)
    text = variants[idx]
    if is_repeated_crisis_reply(text, previous_assistant_texts or []):
        for candidate in variants:
            if not is_repeated_crisis_reply(candidate, previous_assistant_texts or []):
                text = candidate
                break
    if imminent and _IMMEDIATE_SUPPORT_SENTENCE not in text:
        text = f"{text} {_IMMEDIATE_SUPPORT_SENTENCE}"
    plan = DistressConversationPlan(
        visible_text=text,
        response_mode="imminent_safety_hold" if imminent else "high_distress_retention",
        emotional_anchor="distress_retention",
        follow_up_question="",
        should_show_support_popup=True,
        suppress_inline_crisis_cards=True,
        safety_reason_codes=reason_codes or ["sos_gate_triggered"],
        source="fallback_template",
    )
    return validate_distress_conversation_plan(plan)


_LLM_DISTRESS_SYSTEM_PROMPT = """\
Bạn viết phản hồi chat tiếng Việt cho người dùng đang distress/SOS sau khi safety gate đã kích hoạt.
Trả JSON một dòng chỉ gồm: visible_text, emotional_anchor, follow_up_question.

Luật bắt buộc:
- visible_text 4-6 câu, đồng cảm trực tiếp, bám tin mới nhất, mời người dùng kể tiếp.
- Không đưa hotline, số điện thoại, menu thở, danh sách bài tập, hay CTA tài nguyên vào thân chat.
- Không bắt đầu bằng "hãy bình tĩnh"; không chẩn đoán; không mô tả phương thức tự hại; không nhắc risk score/tier/module.
- Hỏi tối đa một câu hỏi mở, không phỏng vấn dồn dập.
- Không hứa chắc chắn mọi chuyện sẽ ổn; không forced positivity.
- Nếu nguy hiểm có vẻ sát, chỉ thêm một câu gợi ý gọi người thật ở gần hoặc mở trang Hỗ trợ.
""".strip()


async def build_llm_distress_conversation_plan(
    *,
    user_message: str,
    session_sos_count: int = 0,
    is_alone: bool = False,
    previous_assistant_texts: list[str] | None = None,
    reason_codes: list[str] | None = None,
    openai_api_key: str | None = None,
) -> DistressConversationPlan:
    if not openai_api_key:
        raise ValueError("openai_api_key not set")

    from openai import OpenAI
    from app.core.config import get_settings as _get_settings

    model = _get_settings().openai_model_analyst or "gpt-4o-mini"
    client = OpenAI(api_key=openai_api_key, timeout=2.5)
    recent_note = "\n".join(f"- {text[:220]}" for text in (previous_assistant_texts or [])[-3:])
    user_payload = (
        f"session_sos_count={int(session_sos_count or 0)}; is_alone={bool(is_alone)}\n"
        f"Không lặp lại các mở đầu gần đây:\n{recent_note or '- none'}\n"
        f"Tin nhắn người dùng: {user_message}"
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0.75,
        max_tokens=420,
        messages=[
            {"role": "system", "content": _LLM_DISTRESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    parsed = json.loads(raw)
    text = str(parsed.get("visible_text") or "").strip()[:1200]
    if is_repeated_crisis_reply(text, previous_assistant_texts or []):
        raise ValueError("LLM distress response repeated previous crisis reply")
    plan = DistressConversationPlan(
        visible_text=text,
        response_mode="high_distress_retention",
        emotional_anchor=str(parsed.get("emotional_anchor") or "distress_retention")[:120],
        follow_up_question=str(parsed.get("follow_up_question") or "").strip()[:220],
        should_show_support_popup=True,
        suppress_inline_crisis_cards=True,
        safety_reason_codes=reason_codes or ["sos_gate_triggered"],
        source="llm",
    )
    return validate_distress_conversation_plan(plan)


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
