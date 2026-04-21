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

    return (
        f"Distress score hiện tại: {float(state.get('distress_score') or 0.0):.2f}\n"
        f"{mood_line}\n"
        f"Long-term memory về người dùng:\n{memory_blob}\n"
        f"Lịch sử gần đây:\n{transcript}\n"
        f"Gợi ý analyst (nếu có): {state.get('analyst_instruction') or '(không có)'}"
    )


def _needs_deeper_empathy_reply(reply: str) -> bool:
    stripped = str(reply or "").strip()
    if not stripped:
        return True
    if len(stripped.split()) < 25:
        return True
    normalized = _normalize_guard_text(stripped)
    has_emotion_reflection = any(
        marker in normalized
        for marker in (
            "cam giac",
            "miet",
            "bat an",
            "buc xuc",
            "ap luc",
            "kho",
            "rat de hieu",
        )
    )
    return not has_emotion_reflection


def _enforce_reply_quality(reply: str, user_message: str, distress_score: float) -> str:
    if not _needs_deeper_empathy_reply(reply):
        return reply
    if distress_score >= 0.6:
        return (
            "Mình nghe rõ là bạn đang rất quá tải và cảm giác này nặng nề thật, nhất là khi mọi thứ cứ dồn cùng lúc "
            "khiến bạn khó thở và khó nghĩ thông suốt. Phản ứng đó là dễ hiểu, và mình muốn đi cùng bạn từng bước nhỏ: "
            "mình có thể cùng bạn làm một nhịp thở chậm 60 giây hoặc tách điều đang làm bạn sợ nhất ra trước. "
            "Ngay lúc này, điều nào đang đè nặng bạn nhất để mình giúp đúng chỗ?"
        )
    return (
        "Mình nghe được bạn đang bối rối và mệt vì chuyện này cứ lặp lại trong đầu, nên thấy bức bối là điều rất dễ hiểu. "
        "Nếu bạn đồng ý, mình gợi ý một bước nhỏ trong 5 phút: viết nhanh điều bạn cần nhất lúc này và điều bạn có thể làm ngay "
        "để tự đỡ áp lực hơn một chút. Bạn muốn bắt đầu từ việc làm rõ cảm xúc của mình hay từ một hành động cụ thể trước?"
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
    user_payload = f"{mood_note}\nLịch sử gần đây:\n{transcript}\nTin mới: {state.get('user_message', '')}"

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
        "Reply ngắn gọn 2-3 câu: phản chiếu cảm xúc + một gợi ý nhỏ làm ngay + một câu hỏi mở. "
        "Tránh sáo rỗng, tránh lan man. "
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
    user_payload = user_text if distress_now < 0.42 and len(user_text) <= 140 else f"{friend_context}\n\nTin nhắn mới:\n{user_text}"

    payload: dict[str, Any] = {
        "reply": "Mình nghe bạn. Mình ở đây cùng bạn, và bạn có thể kể thêm điều đang làm bạn nặng lòng nhất lúc này không?",
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
                "Bạn tên là Mây. Luôn xưng mình/bạn, không dùng mày/tao. "
                "Trả lời tiếng Việt 2-3 câu, cụ thể, không sáo rỗng, kết thúc bằng câu hỏi mở."
            )
            friend_context = _build_friend_context(state)
            user_payload = user_text if distress_now < 0.42 and len(user_text) <= 140 else f"{friend_context}\n\nTin nhắn mới:\n{user_text}"
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
            )
            yield {"type": "final", "turn": fallback}
            return
    else:
        reply_text = "Mình nghe bạn. Mình ở đây cùng bạn, và bạn có thể kể thêm điều đang làm bạn nặng lòng nhất lúc này không?"

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
