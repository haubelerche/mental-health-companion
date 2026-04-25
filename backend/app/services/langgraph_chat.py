"""
LangGraph: Analyst → Friend for non-SOS turns. SOS is handled outside (rule-based finalizer).
BACKEND_PLAN §3.3, MVP_CANVAS.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Iterator, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.product_constants import CHAT_AGENT_DISPLAY_NAME
from app.services.safety_scoring import build_snapshot

logger = logging.getLogger(__name__)


class ChatGraphState(TypedDict, total=False):
    user_message: str
    recent_messages: list[dict[str, Any]]
    mood_today: dict[str, Any] | None
    long_term_memories: list[str]
    mem0_facts: list[str]
    user_traits: dict[str, Any] | None
    top_triggers: list[str]
    active_goals: list[str]
    effective_coping: list[str]
    clinical_trajectory: str | None
    distress_score: float
    routing_history: list[str]
    analyst_calls_this_turn: int
    crisis_route_finalized: bool
    use_fast_friend_model: bool
    analyst_instruction: str
    supervisor_route: str
    supervisor_reason: str
    reply: str
    tone_cam_xuc: str
    goi_y_nhanh: list[str]
    the_dinh_kem: list[dict[str, Any]]


_GREETING_RE = re.compile(r"\b(chao|hi|hello|helo|xin chao|yo|hey)\b", re.IGNORECASE)
_DISTRESS_HINT_RE = re.compile(
    r"\b(buon|met|kiet suc|ap luc|bat an|stress|lo au|that bai|khong on)\b",
    re.IGNORECASE,
)
_ANALYST_TRIGGER_RE = re.compile(
    r"\b(phan tich|ke hoach|khong biet lam sao|khong biet phai lam gi|toi roi|hoang mang)\b",
    re.IGNORECASE,
)
_ANALYST_CALLS_CAP = 2
_QUICK_THANKS_RE = re.compile(r"\b(cam on|thanks|thank you)\b", re.IGNORECASE)
_QUICK_GREETING_ONLY_RE = re.compile(r"^(chao|xin chao|hi|hello|hey|yo|ok|oke|d a|da|uhm|hmm|bn oi|e|ey|eyy|ei)\W*$", re.IGNORECASE)
_GENERIC_FOLLOWUP_RE = re.compile(
    r"(ban co the (noi|chia se|ke) them|noi them (cho|minh)|chia se them|ke them|muon noi them)",
    re.IGNORECASE,
)


def _normalize_guard_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")
    compact = re.sub(r"[^a-z0-9\s]", " ", no_accent)
    return re.sub(r"\s+", " ", compact).strip()


def _sanitize_assistant_reply(reply: str) -> str:
    cleaned = str(reply or "").strip()
    if not cleaned:
        return "Mình đang ở đây với bạn. Bạn có thể chia sẻ thêm để mình hỗ trợ bạn tốt hơn nhé."

    normalized = _normalize_guard_text(cleaned)
    forbidden_tokens = {"tao", "may", "mi", "bon", "bay"}
    tokens = normalized.split()
    if "tao" in tokens or ("may" in tokens and "minh" not in tokens):
        return "Mình đang ở đây để lắng nghe bạn. Bạn có thể nói thêm điều đang làm bạn quá tải lúc này không?"
    if any(tok in tokens for tok in forbidden_tokens) and ("ban" not in tokens):
        return "Mình sẽ giữ cách nói an toàn để đồng hành cùng bạn. Bạn có thể chia sẻ thêm điều đang khiến bạn khó thở nhất lúc này không?"
    if re.search(r"\b(di chet|tu tu)\b", normalized):
        return "Mình nghe bạn và mình rất quan tâm đến sự an toàn của bạn ngay lúc này. Mình ở đây cùng bạn."
    return cleaned[:1200]


def _rule_based_reply(user_text: str) -> str | None:
    normalized = _normalize_guard_text(user_text)
    if re.search(r"\b(muon giet|se giet|dinh giet|kill)\b", normalized):
        return (
            "Mình cần nói rõ: ý định làm hại người khác là nguy hiểm và cần dừng lại ngay. "
            "Bạn hãy rời khỏi nơi có xung đột, đặt các vật sắc nhọn ra xa, và nói cho mình biết bạn đang ở đâu để mình hỗ trợ bước tiếp theo."
        )
    if any(k in normalized for k in ("bo da", "chia tay", "that tinh")):
        return (
            "Mình hiểu đây là cú sốc lớn và cảm giác mất mát đang rất thật. "
            "Lúc này điều nào đau nhất với bạn: bị bỏ rơi, tự trách, hay sợ tương lai?"
        )
    if any(k in normalized for k in ("chia xa", "tam biet", "roi xa", "xa nhau")):
        return (
            "Mình nghe rõ nỗi buồn chia xa của bạn, nhất là khi mới quen nhưng đã thấy rất thân. "
            "Cảm giác hụt hẫng và trống vắng lúc này là điều hoàn toàn dễ hiểu. "
            "Bạn muốn mình cùng bạn giữ lại một điều đẹp từ mối kết nối này, hay giúp bạn đi qua khoảnh khắc buồn tối nay trước?"
        )
    if any(k in normalized for k in ("toi dua thui", "toi dua", "just kidding")):
        return "Mình hiểu bạn đang đùa, nhưng mình vẫn muốn giữ an toàn cho bạn. Dạo này có điều gì làm bạn căng quá không?"
    return None


def _default_user_quick_replies(user_message: str, distress_score: float) -> list[str]:
    lowered = user_message.lower()
    if distress_score >= 0.55:
        return [
            "Mình đang rất quá tải, cậu giúp mình từng bước nhé.",
            "Mình muốn nói thêm điều làm mình sợ nhất lúc này.",
            "Cậu hướng dẫn mình một bài thở ngắn ngay bây giờ nhé.",
        ]
    if any(k in lowered for k in ("khong ngu", "mat ngu", "ngu")):
        return [
            "Mình khó ngủ mấy hôm nay, cậu giúp mình ổn định lại nhé.",
            "Mình muốn thử một cách thư giãn trước khi ngủ.",
            "Mình cần một kế hoạch nhẹ cho tối nay.",
        ]
    return [
        "Mình muốn kể thêm về chuyện này.",
        "Mình đang thấy khó chịu và cần cậu lắng nghe.",
        "Cậu gợi ý cho mình một bước nhỏ lúc này nhé.",
    ]


def _normalize_user_quick_replies(
    replies: list[str] | None,
    *,
    user_message: str,
    distress_score: float,
) -> list[str]:
    defaults = _default_user_quick_replies(user_message, distress_score)
    if not replies:
        return defaults

    cleaned: list[str] = []
    for text in replies:
        s = str(text or "").strip()
        if not s:
            continue
        s = s.replace("\n", " ")
        if len(s) > 80:
            s = s[:77].rstrip() + "..."
        cleaned.append(s)

    if len(cleaned) < 3:
        return defaults

    # Ensure quick replies are in user's voice (first person) instead of asking the user questions.
    forbidden_in_quick_reply = {"tao", "may", "mi", "nguoi"}
    user_voice = [
        s
        for s in cleaned
        if re.search(r"\b(minh|em|toi)\b", _normalize_guard_text(s), re.IGNORECASE)
        and not any(tok in _normalize_guard_text(s).split() for tok in forbidden_in_quick_reply)
    ]
    if len(user_voice) >= 3:
        return user_voice[:3]
    return defaults


def _build_friend_context(state: ChatGraphState) -> str:
    mood = state.get("mood_today") or {}
    mood_line = "Không có mood check-in hôm nay."
    if mood:
        mood_line = f"Mood hôm nay: {mood.get('mood', '')} {mood.get('emoji', '')}. Ghi chú: {mood.get('note', '')}"

    transcript_lines: list[str] = []
    for turn in (state.get("recent_messages") or [])[-6:]:
        role = str(turn.get("role", "")).strip() or "unknown"
        content = str(turn.get("content", "")).strip()
        if content:
            transcript_lines.append(f"{role}: {content}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "(chưa có lịch sử)"
    memory_lines = [str(item or "").strip() for item in (state.get("long_term_memories") or []) if str(item or "").strip()]
    memory_blob = "\n".join(f"- {item}" for item in memory_lines[:3]) if memory_lines else "(chưa có memory dài hạn)"
    mem0_facts = [str(item or "").strip() for item in (state.get("mem0_facts") or []) if str(item or "").strip()]
    mem0_blob = "\n".join(f"- {item}" for item in mem0_facts[:5]) if mem0_facts else "(chưa có memory theo ngữ cảnh)"
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    triggers_line = ", ".join(top_triggers[:3]) if top_triggers else "(chưa rõ)"
    coping = [str(item or "").strip() for item in (state.get("effective_coping") or []) if str(item or "").strip()]
    coping_line = ", ".join(coping[:3]) if coping else "(chưa rõ)"
    goals = [str(item or "").strip() for item in (state.get("active_goals") or []) if str(item or "").strip()]
    goals_line = "; ".join(goals[:2]) if goals else "(chưa có mục tiêu)"
    traits = dict(state.get("user_traits") or {})
    preferred_tone = str(traits.get("preferred_tone") or "").strip() or "(chưa rõ)"
    communication_style = str(traits.get("communication_style") or "").strip() or "(chưa rõ)"
    trajectory = str(state.get("clinical_trajectory") or "").strip() or "(chưa đủ dữ liệu)"

    return (
        f"Distress score hiện tại: {float(state.get('distress_score') or 0.0):.2f}\n{mood_line}\n"
        f"--- Hồ sơ người dùng ---\n"
        f"Giao tiếp: {communication_style} | Tông ưa thích: {preferred_tone}\n"
        f"Chủ đề hay gặp: {triggers_line}\n"
        f"Đối phó hiệu quả: {coping_line}\n"
        f"Mục tiêu hiện tại: {goals_line}\n"
        f"Hành trình: {trajectory}\n"
        f"--- Ký ức liên quan (Mem0) ---\n{mem0_blob}\n"
        f"Long-term memory về người dùng:\n"
        f"--- Tóm tắt session gần đây ---\n{memory_blob}\n"
        f"Lịch sử gần đây:\n{transcript}\n"
        f"Gợi ý analyst (nếu có): {state.get('analyst_instruction') or '(không có)'}"
    )


def _build_personality_hint(state: ChatGraphState) -> str:
    traits = dict(state.get("user_traits") or {})
    preferred_tone = str(traits.get("preferred_tone") or "").strip()
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    trigger_hint = ", ".join(top_triggers[:2]) if top_triggers else "chưa rõ trigger"
    tone_hint = preferred_tone or "dịu dàng"
    return f"[User profile: tone={tone_hint}; hay gặp={trigger_hint}]"


def _detect_hardship_signals(text: str) -> list[str]:
    normalized = _normalize_guard_text(text)
    cues: list[tuple[str, tuple[str, ...]]] = [
        ("mat_ngu", ("khong ngu", "mat ngu", "thuc dem", "ngu khong duoc")),
        ("tai_chinh", ("tien", "luong", "no", "thue", "chi phi")),
        ("gia_dinh", ("gia dinh", "con cai", "bo me", "bao hieu")),
        ("kiet_suc", ("kiet suc", "qua tai", "met moi", "ap luc", "that vong")),
        ("co_don", ("co don", "khong ai", "mot minh", "khong duoc hieu")),
    ]
    matches: list[str] = []
    for key, keywords in cues:
        if any(word in normalized for word in keywords):
            matches.append(key)
    return matches


def _build_empathy_anchor(user_message: str, distress_score: float) -> str:
    signals = _detect_hardship_signals(user_message)
    if "tai_chinh" in signals and "gia_dinh" in signals:
        return (
            "Mình nghe rất rõ gánh nặng phải gồng tài chính cho gia đình, nhất là khi bạn đã cố hết sức mà vẫn thấy chưa đủ. "
            "Cảm giác bất lực trong hoàn cảnh đó là thật và rất đau."
        )
    if "mat_ngu" in signals and "kiet_suc" in signals:
        return (
            "Mất ngủ kéo dài làm mọi thứ nặng hơn rất nhiều, nên việc bạn thấy kiệt sức và dễ vỡ là phản ứng rất người. "
            "Không phải bạn yếu, mà là cơ thể và tâm trí đang báo đã quá tải."
        )
    if "co_don" in signals:
        return (
            "Nghe như bạn đã phải ôm quá nhiều thứ một mình quá lâu, nên cảm giác trống và mệt là điều dễ hiểu. "
            "Đôi khi chỉ cần có người thật sự hiểu cũng đã là một chỗ tựa quan trọng."
        )
    if "kiet_suc" in signals:
        return (
            "Mình nghe bạn đang bị dồn nén từ nhiều phía, và cảm giác nghẹt thở đó không hề nhỏ. "
            "Trong trạng thái này, việc bạn chao đảo là điều hoàn toàn có thể hiểu."
        )
    if distress_score >= 0.6:
        return (
            "Mình nghe bạn đang phải chống đỡ quá nhiều thứ cùng lúc. "
            "Khi cảm xúc bị dồn như vậy, thấy rối và mệt là phản ứng rất thật."
        )
    return (
        "Mình nghe bạn và mình tin rằng cảm giác bạn đang mang là có lý do của nó, không hề 'làm quá'. "
        "Đôi khi sống sót qua một ngày khó đã là một nỗ lực lớn."
    )


def _needs_deeper_empathy_reply(reply: str, user_message: str = "") -> bool:
    stripped = str(reply or "").strip()
    if not stripped:
        return True
    if len(stripped.split()) < 25:
        return True
    normalized = _normalize_guard_text(stripped)
    if _GENERIC_FOLLOWUP_RE.search(normalized) and len(normalized.split()) < 55:
        return True
    has_emotion_reflection = any(
        marker in normalized
        for marker in (
            "cam giac",
            "met",
            "bat an",
            "buc xuc",
            "ap luc",
            "kho",
            "rat de hieu",
            "qua tai",
            "bat luc",
        )
    )
    if not has_emotion_reflection:
        return True
    if user_message:
        user_signals = _detect_hardship_signals(user_message)
        if user_signals:
            mentions_context = any(token in normalized for token in ("mat ngu", "tien", "luong", "gia dinh", "kiet suc", "mot minh", "qua tai"))
            if not mentions_context:
                return True
    return False


def _enforce_reply_quality(reply: str, user_message: str, distress_score: float) -> str:
    if not _needs_deeper_empathy_reply(reply, user_message):
        return reply
    normalized_user = _normalize_guard_text(user_message)
    if any(k in normalized_user for k in ("chia xa", "tam biet", "roi xa", "xa nhau")):
        return (
            "Mình nghe bạn đang buồn sâu vì sắp phải chia xa những người bạn mới quen, và cảm giác quyến luyến đến nhanh như vậy "
            "thật sự có thể làm tim mình trống đi một nhịp. Phản ứng đó rất người và rất dễ hiểu, nhất là khi bạn đã kịp thấy "
            "an toàn, được kết nối. Nếu bạn muốn, mình có thể cùng bạn giữ lại một điều ý nghĩa từ quãng thời gian này, rồi chọn "
            "một cách nhẹ để đi qua tối nay. Điều bạn sợ nhất khi phải tạm xa họ là gì?"
        )
    if any(k in normalized_user for k in ("co don", "mot minh", "lac long", "khong ai hieu")):
        return (
            "Mình nghe bạn đang rất cô đơn và cảm giác như không ai thật sự hiểu mình, nên mệt và tủi lúc này là điều rất dễ hiểu. "
            "Bạn không cần gồng lên một mình ở đây, mình sẽ đi cùng bạn từng chút một. Nếu được, mình muốn bắt đầu từ điều đang "
            "làm bạn thấy lạc lõng nhất ngay lúc này, bạn kể cho mình nghe nhé?"
        )
    anchor = _build_empathy_anchor(user_message, distress_score)
    if distress_score >= 0.6:
        return (
            f"{anchor} "
            "Mình không muốn ép bạn phải ổn ngay. Nếu được, mình đề nghị một bước rất nhỏ và thực tế lúc này: "
            "thả lỏng vai, thở chậm 4 nhịp, rồi nói cho mình một điều đang đè nặng nhất ngay trong tối nay để mình ở đây cùng bạn gỡ từng lớp."
        )
    return (
        f"{anchor} "
        "Nếu bạn đồng ý, mình sẽ không nói lý thuyết dài: mình cùng bạn chọn một bước nhỏ đủ thực tế trong 5 phút tới để bớt nặng đi một chút. "
        "Bạn muốn bắt đầu bằng việc đặt tên cảm xúc đang lớn nhất, hay chốt một việc nhỏ có thể làm ngay?"
    )


def _quick_non_sos_turn(
    *,
    user_message: str,
    distress_score: float,
    mood_today: dict[str, Any] | None,
) -> dict[str, Any] | None:
    normalized = _normalize_guard_text(user_message)
    if distress_score >= 0.38 or _DISTRESS_HINT_RE.search(normalized):
        return None
    if _ANALYST_TRIGGER_RE.search(normalized):
        return None

    if len(normalized) <= 18 and _QUICK_GREETING_ONLY_RE.search(normalized):
        return {
            "reply": "Mình ở đây với bạn. Hôm nay bạn muốn tâm sự nhẹ nhàng hay cần mình giúp gỡ rối một chuyện cụ thể?",
            "tone_cam_xuc": "vui_tuoi",
            "goi_y_nhanh": [
                "Mình muốn kể một chuyện đang làm mình bận tâm.",
                "Mình cần một bước nhỏ để đỡ căng thẳng.",
                "Mình muốn bạn lắng nghe thôi.",
            ],
            "the_dinh_kem": [],
            "routing_history": ["supervisor", "friend_fastpath"],
        }

    if len(normalized) <= 40 and _QUICK_THANKS_RE.search(normalized):
        return {
            "reply": "Mình rất vui vì giúp được bạn. Nếu còn điều gì lăn tăn, mình vẫn ở đây để đi cùng bạn nhé?",
            "tone_cam_xuc": "xac_nhan",
            "goi_y_nhanh": _default_user_quick_replies(user_message, distress_score),
            "the_dinh_kem": [],
            "routing_history": ["supervisor", "friend_fastpath"],
        }

    if mood_today and len(normalized) <= 36 and normalized in {"minh on", "toi on", "on roi", "tam on"}:
        return {
            "reply": "Mừng vì nghe bạn nói vậy. Nếu muốn, mình có thể giúp bạn giữ nhịp ổn này bằng một thói quen nhỏ cho tối nay?",
            "tone_cam_xuc": "vui_tuoi",
            "goi_y_nhanh": _default_user_quick_replies(user_message, distress_score),
            "the_dinh_kem": [],
            "routing_history": ["supervisor", "friend_fastpath"],
        }
    return None


def supervisor_node(state: ChatGraphState) -> dict[str, Any]:
    hist = list(state.get("routing_history") or [])
    hist.append("supervisor")

    msg = (state.get("user_message") or "").strip()
    lowered = msg.lower()
    calls = int(state.get("analyst_calls_this_turn") or 0)
    distress = float(state.get("distress_score") or 0.0)
    mood = (state.get("mood_today") or {}).get("mood")

    if state.get("crisis_route_finalized"):
        route = "friend"
        reason = "crisis_already_finalized"
    elif calls >= _ANALYST_CALLS_CAP:
        route = "friend"
        reason = "analyst_cap_reached"
    elif distress >= 0.72:
        route = "analyst"
        reason = "distress_or_mood_signal"
    elif mood in {"stressed", "restless", "melancholic"} and distress >= 0.58:
        route = "analyst"
        reason = "mood_plus_distress_signal"
    elif _ANALYST_TRIGGER_RE.search(lowered):
        route = "analyst"
        reason = "explicit_analysis_request"
    elif len(msg) <= 60 and _GREETING_RE.search(lowered) and not _DISTRESS_HINT_RE.search(lowered):
        route = "friend"
        reason = "light_greeting"
    elif len(msg) <= 180 and not _DISTRESS_HINT_RE.search(lowered):
        route = "friend"
        reason = "low_latency_friend_path"
    else:
        route = "friend"
        reason = "default_low_latency_friend"

    return {
        "routing_history": hist,
        "supervisor_route": route,
        "supervisor_reason": reason,
    }


def route_after_supervisor(state: ChatGraphState) -> str:
    route = state.get("supervisor_route")
    return "analyst" if route == "analyst" else "friend"


def analyst_node(state: ChatGraphState) -> dict[str, Any]:
    settings = get_settings()
    calls = int(state.get("analyst_calls_this_turn") or 0) + 1
    hist = list(state.get("routing_history") or [])
    hist.append("analyst")

    mood_note = ""
    m = state.get("mood_today")
    if m:
        mood_note = f"Mood hôm nay: {m.get('mood', '')} {m.get('emoji', '')}."

    ctx_lines = []
    for turn in (state.get("recent_messages") or [])[-8:]:
        ctx_lines.append(f"{turn.get('role', '')}: {turn.get('content', '')}")
    transcript = "\n".join(ctx_lines)

    instruction = (
        "Bạn là Analyst ẩn danh. Trả lời JSON một dòng với khóa: "
        '`clinical_note` (ngắn, tiếng Việt), `suggested_probe` (một câu gợi mở cho Friend hỏi thêm nếu cần). '
        "Không chẩn đoán. Không nhắc PII."
    )
    mem0_facts = [str(item or "").strip() for item in (state.get("mem0_facts") or []) if str(item or "").strip()]
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    effective_coping = [str(item or "").strip() for item in (state.get("effective_coping") or []) if str(item or "").strip()]
    context_lines = []
    if mem0_facts:
        context_lines.append(f"Ký ức liên quan: {'; '.join(mem0_facts[:3])}")
    if top_triggers:
        context_lines.append(f"Trigger lặp lại: {', '.join(top_triggers[:3])}")
    if effective_coping:
        context_lines.append(f"Coping từng giúp: {', '.join(effective_coping[:3])}")
    trajectory = str(state.get("clinical_trajectory") or "").strip()
    if trajectory:
        context_lines.append(f"Hành trình tâm lý: {trajectory}")
    profile_context = "\n".join(context_lines) if context_lines else "(chưa có profile context)"
    user_payload = (
        f"{profile_context}\n"
        f"{mood_note}\n"
        f"Lịch sử gần đây:\n{transcript}\n"
        f"Tin mới: {state.get('user_message', '')}"
    )

    text_out = ""
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 2.8))
            resp = client.chat.completions.create(
                model=settings.openai_model_analyst,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_payload},
                ],
            )
            text_out = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("analyst llm failed: %s", exc)
            text_out = '{"clinical_note": "", "suggested_probe": ""}'
    else:
        text_out = '{"clinical_note": "Người dùng đang chia sẻ căng thẳng.", "suggested_probe": "Bạn muốn kể thêm về điều đó không?"}'

    return {
        "analyst_calls_this_turn": calls,
        "routing_history": hist,
        "analyst_instruction": text_out[:2000],
    }


def friend_node(state: ChatGraphState) -> dict[str, Any]:
    settings = get_settings()
    hist = list(state.get("routing_history") or [])
    hist.append("friend")

    system = (
        "Bạn tên là Mây, đồng hành ấm áp và thực tế. "
        "Luôn xưng 'mình' và 'bạn', tuyệt đối không dùng 'mày/tao', không bắt chước chửi thề. "
        "Mục tiêu là khiến người đang đau thấy được thấu hiểu thật sự, không phải trả lời cho có. "
        "Reply 3-5 câu ngắn, có chiều sâu: (1) phản chiếu chính xác nỗi đau cụ thể từ tin nhắn, "
        "(2) xác nhận phản ứng của họ là hợp lý trong hoàn cảnh đó, "
        "(3) đưa một bước nhỏ rất thực tế làm ngay, "
        "(4) mời họ tiếp tục nếu họ muốn. "
        "Ưu tiên ngôn ngữ đời thường, chân thành, có chút chiêm nghiệm nhưng không bi lụy, không giáo điều. "
        "Không lặp công thức 'Bạn có thể chia sẻ thêm...?' ở mọi lượt. "
        "Không hứa hẹn phi thực tế, không phán xét, không biến câu trả lời thành checklist khô cứng. "
        "Trả lời JSON với các khóa: reply, tone_cam_xuc (ho_tro|xac_nhan|vui_tuoi|lam_diu), "
        "goi_y_nhanh (3 chuỗi), the_dinh_kem (mảng object {type, id, title}). "
        "Gợi ý analyst: "
        + (state.get("analyst_instruction") or "")
    )
    user_text = state.get("user_message", "")
    distress_now = float(state.get("distress_score") or 0.0)
    use_fast_model = bool(state.get("use_fast_friend_model")) and distress_now < 0.55
    preferred_friend_model = (
        settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
    )
    friend_context = _build_friend_context(state)
    if distress_now < 0.42 and len(user_text) <= 140:
        user_payload = f"{_build_personality_hint(state)}\n{user_text}"
    else:
        user_payload = f"{friend_context}\n\nTin nhắn mới:\n{user_text}"

    payload: dict[str, Any] = {
        "reply": _enforce_reply_quality("", user_text, distress_now),
        "tone_cam_xuc": "xac_nhan",
        "goi_y_nhanh": ["Kể thêm đi cậu", "Mình nên làm gì bây giờ?", "Chỉ cần lắng nghe thôi"],
        "the_dinh_kem": [{"type": "breathing_exercise", "id": "breath_478", "title": "Thở 4-7-8 — Giảm căng thẳng"}],
    }

    rule_based = _rule_based_reply(user_text)
    if rule_based:
        payload["reply"] = rule_based
    elif settings.openai_api_key:
        try:
            import json
            import re

            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 3.5))
            try:
                resp = client.chat.completions.create(
                    model=preferred_friend_model,
                    temperature=0.65 if use_fast_model else 0.75,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_payload},
                    ],
                )
            except Exception:
                if preferred_friend_model != settings.openai_model_friend:
                    resp = client.chat.completions.create(
                        model=settings.openai_model_friend,
                        temperature=0.75,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_payload},
                        ],
                    )
                else:
                    raise
            raw = (resp.choices[0].message.content or "").strip()
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                raw = m.group(1).strip()
            parsed = json.loads(raw)
            payload.update(parsed)
        except Exception as exc:
            logger.warning("friend llm failed: %s", exc)

    improved_reply = _enforce_reply_quality(str(payload.get("reply") or ""), user_text, distress_now)
    safe_reply = _sanitize_assistant_reply(improved_reply)
    if distress_now >= 0.6 and "?" not in safe_reply:
        safe_reply = safe_reply.rstrip(".! ") + ". Bạn có thể nói thêm điều đang làm bạn thấy tệ nhất lúc này không?"

    return {
        "routing_history": hist,
        "reply": safe_reply,
        "tone_cam_xuc": str(payload.get("tone_cam_xuc") or "xac_nhan"),
        "goi_y_nhanh": _normalize_user_quick_replies(
            list(payload.get("goi_y_nhanh") or []),
            user_message=user_text,
            distress_score=float(state.get("distress_score") or 0.0),
        ),
        "the_dinh_kem": list(payload.get("the_dinh_kem") or []),
    }


def build_chat_graph():
    g = StateGraph(ChatGraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("analyst", analyst_node)
    g.add_node("friend", friend_node)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"analyst": "analyst", "friend": "friend"},
    )
    g.add_edge("analyst", "friend")
    g.add_edge("friend", END)
    return g.compile()


_COMPILED = None


def get_chat_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_chat_graph()
    return _COMPILED


def run_non_sos_turn(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    mood_today: dict[str, Any] | None,
    distress_score: float,
    long_term_memories: list[str] | None = None,
    mem0_facts: list[str] | None = None,
    user_traits: dict[str, Any] | None = None,
    top_triggers: list[str] | None = None,
    active_goals: list[str] | None = None,
    effective_coping: list[str] | None = None,
    clinical_trajectory: str | None = None,
) -> dict[str, Any]:
    """Run Analyst→Friend. Caller builds API `data` envelope with safety ladder."""
    settings = get_settings()
    snap = build_snapshot(
        distress_score,
        sos_triggered=False,
        voice_hint=settings.distress_voice_hint,
        critical=settings.distress_critical,
    )
    quick_turn = _quick_non_sos_turn(user_message=user_message, distress_score=distress_score, mood_today=mood_today)
    if quick_turn is not None:
        return {
            "session_fields": snap,
            "reply": quick_turn.get("reply", ""),
            "tone_cam_xuc": quick_turn.get("tone_cam_xuc", "xac_nhan"),
            "goi_y_nhanh": quick_turn.get("goi_y_nhanh", []),
            "the_dinh_kem": quick_turn.get("the_dinh_kem", []),
            "routing_history": quick_turn.get("routing_history", []),
        }
    graph = get_chat_graph()
    out = graph.invoke(
        {
            "user_message": user_message,
            "recent_messages": recent_messages,
            "mood_today": mood_today,
            "long_term_memories": list(long_term_memories or []),
            "mem0_facts": list(mem0_facts or []),
            "user_traits": dict(user_traits or {}),
            "top_triggers": list(top_triggers or []),
            "active_goals": list(active_goals or []),
            "effective_coping": list(effective_coping or []),
            "clinical_trajectory": clinical_trajectory or "",
            "distress_score": distress_score,
            "crisis_route_finalized": False,
            "analyst_calls_this_turn": 0,
            "use_fast_friend_model": snap.safety_tier != "critical" and distress_score < 0.65,
            "routing_history": [],
        }
    )
    return {
        "session_fields": snap,
        "reply": out.get("reply", ""),
        "tone_cam_xuc": out.get("tone_cam_xuc", "xac_nhan"),
        "goi_y_nhanh": out.get("goi_y_nhanh", []),
        "the_dinh_kem": out.get("the_dinh_kem", []),
        "routing_history": out.get("routing_history", []),
    }


def stream_non_sos_turn_events(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    mood_today: dict[str, Any] | None,
    distress_score: float,
    long_term_memories: list[str] | None = None,
    mem0_facts: list[str] | None = None,
    user_traits: dict[str, Any] | None = None,
    top_triggers: list[str] | None = None,
    active_goals: list[str] | None = None,
    effective_coping: list[str] | None = None,
    clinical_trajectory: str | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Yield streaming events for non-SOS turn:
    - {"type":"token","text":"..."} while model is generating
    - {"type":"final","turn":{...}} when completed
    """
    settings = get_settings()
    snap = build_snapshot(
        distress_score,
        sos_triggered=False,
        voice_hint=settings.distress_voice_hint,
        critical=settings.distress_critical,
    )

    quick_turn = _quick_non_sos_turn(user_message=user_message, distress_score=distress_score, mood_today=mood_today)
    if quick_turn is not None:
        yield {
            "type": "final",
            "turn": {
                "session_fields": snap,
                "reply": quick_turn.get("reply", ""),
                "tone_cam_xuc": quick_turn.get("tone_cam_xuc", "xac_nhan"),
                "goi_y_nhanh": quick_turn.get("goi_y_nhanh", []),
                "the_dinh_kem": quick_turn.get("the_dinh_kem", []),
                "routing_history": quick_turn.get("routing_history", []),
            },
        }
        return

    state: ChatGraphState = {
        "user_message": user_message,
        "recent_messages": recent_messages,
        "mood_today": mood_today,
        "long_term_memories": list(long_term_memories or []),
        "mem0_facts": list(mem0_facts or []),
        "user_traits": dict(user_traits or {}),
        "top_triggers": list(top_triggers or []),
        "active_goals": list(active_goals or []),
        "effective_coping": list(effective_coping or []),
        "clinical_trajectory": clinical_trajectory or "",
        "distress_score": distress_score,
        "crisis_route_finalized": False,
        "analyst_calls_this_turn": 0,
        "use_fast_friend_model": snap.safety_tier != "critical" and distress_score < 0.65,
        "routing_history": [],
    }
    state.update(supervisor_node(state))
    if route_after_supervisor(state) == "analyst":
        state.update(analyst_node(state))

    user_text = state.get("user_message", "")
    distress_now = float(state.get("distress_score") or 0.0)
    hist = list(state.get("routing_history") or [])
    hist.append("friend")
    tone = "xac_nhan"
    attachments: list[dict[str, Any]] = [{"type": "breathing_exercise", "id": "breath_478", "title": "Thở 4-7-8 — Giảm căng thẳng"}]

    reply_text = ""
    rule_based = _rule_based_reply(user_text)
    if rule_based:
        reply_text = rule_based
    elif settings.openai_api_key:
        try:
            from openai import OpenAI

            use_fast_model = bool(state.get("use_fast_friend_model")) and distress_now < 0.55
            model = settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
            system = (
                "Bạn tên là Mây, đồng hành ấm áp và thực tế. "
                "Luôn xưng mình/bạn, tuyệt đối không dùng mày/tao. "
                "Viết 3-5 câu tiếng Việt, phản chiếu nỗi đau cụ thể, xác nhận cảm xúc là hợp lý, "
                "và đưa một bước nhỏ thực tế có thể làm ngay. "
                "Tránh sáo rỗng, không trả lời kiểu mẫu, không hỏi dồn dập."
            )
            friend_context = _build_friend_context(state)
            if distress_now < 0.42 and len(user_text) <= 140:
                user_payload = f"{_build_personality_hint(state)}\n{user_text}"
            else:
                user_payload = f"{friend_context}\n\nTin nhắn mới:\n{user_text}"
            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 15.0))
            stream = client.chat.completions.create(
                model=model,
                temperature=0.65 if use_fast_model else 0.75,
                stream=True,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_payload},
                ],
            )
            for chunk in stream:
                delta = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if not delta:
                    continue
                reply_text += delta
                yield {"type": "token", "text": delta}
        except Exception as exc:
            logger.warning("friend stream failed, fallback to sync: %s", exc)
            fallback = run_non_sos_turn(
                user_message=user_message,
                recent_messages=recent_messages,
                mood_today=mood_today,
                distress_score=distress_score,
                long_term_memories=long_term_memories,
                mem0_facts=mem0_facts,
                user_traits=user_traits,
                top_triggers=top_triggers,
                active_goals=active_goals,
                effective_coping=effective_coping,
                clinical_trajectory=clinical_trajectory,
            )
            yield {"type": "final", "turn": fallback}
            return
    else:
        reply_text = _enforce_reply_quality("", user_text, distress_now)

    improved_reply = _enforce_reply_quality(reply_text, user_text, distress_now)
    safe_reply = _sanitize_assistant_reply(improved_reply)
    if distress_now >= 0.6 and "?" not in safe_reply:
        safe_reply = safe_reply.rstrip(".! ") + ". Bạn có thể nói thêm điều đang làm bạn thấy tệ nhất lúc này không?"

    yield {
        "type": "final",
        "turn": {
            "session_fields": snap,
            "reply": safe_reply,
            "tone_cam_xuc": tone,
            "goi_y_nhanh": _default_user_quick_replies(user_text, distress_now),
            "the_dinh_kem": attachments,
            "routing_history": hist,
        },
    }


def build_normal_envelope(
    session_id: str,
    *,
    snap,
    reply: str,
    tone_cam_xuc: str,
    goi_y_nhanh: list[str],
    the_dinh_kem: list[dict[str, Any]],
    voice_hint: str | None = None,
    routing_history: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "agent_display_name": CHAT_AGENT_DISPLAY_NAME,
        "conversation_mode": snap.conversation_mode,
        "distress_score": snap.distress_score,
        "safety_tier": snap.safety_tier,
        "voice_session_offered": snap.safety_tier == "voice_recommended",
        "suggest_voice": snap.safety_tier == "voice_recommended",
        "voice_hint": voice_hint,
        "emergency_actions": None,
        "reply": reply,
        "tone_cam_xuc": tone_cam_xuc,
        "goi_y_nhanh": goi_y_nhanh,
        "the_dinh_kem": the_dinh_kem,
        "sos_triggered": False,
        "routing_history": routing_history or [],
    }
