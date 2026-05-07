"""
Deterministic SOS handler (no LLM for crisis decision).
Role mapping reference: docs/PRD.md + docs/GLOSSARY_RUNTIME.md.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.product_constants import CHAT_AGENT_DISPLAY_NAME, DISTRESS_CRITICAL, DISTRESS_VOICE_HINT
from app.services.vn_hotlines import hotline_cards_sos
from app.services.safety_scoring import SafetySnapshot, build_snapshot, clamp01

EXPLICIT_HIGH_RISK = [
    "muon chet",
    "muon tu tu",
    "toi muon chet",
    "toi muon tu tu",
    "khong muon song nua",
    "khong muon ton tai nua",
    "chet di cho roi",
    "chet cho xong",
    "toi se tu tu",
    "toi sap tu tu",
    "toi nghi den tu tu",
    "toi dang nghi den viec chet",
    "toi muon bien mat",
    "toi muon ket thuc moi thu",
]

VIOLENCE_HIGH_RISK = [
    "muon giet no",
    "muon giet nguoi",
    "toi muon giet",
    "tao muon giet",
    "toi se giet",
    "tao se giet",
    "dam chet",
    "ban chet",
    "tra thu no",
    "xu no",
    "kill him",
    "kill her",
    "kill them",
]

IMPLICIT_MEDIUM_RISK = [
    "met qua roi",
    "het suc roi",
    "khong con suc nua",
    "song de lam gi",
    "song co y nghia gi dau",
    "toi vo dung",
    "toi la ganh nang",
    "toi khong xung dang ton tai",
    "khong ai can toi",
    "toi chang co gia tri gi",
    "muon bien khoi the gioi nay",
    "gia nhu toi chua tung ton tai",
]

HOPELESSNESS = [
    "tat ca deu vo nghia",
    "khong co loi thoat",
    "khong co tuong lai",
    "khong co hy vong",
    "cu doi toi tan roi",
    "toi that bai het roi",
    "toi khong the tiep tuc duoc nua",
]

FAREWELL_SIGNALS = [
    "tam biet moi nguoi",
    "bye moi nguoi",
    "cam on vi tat ca",
    "cam on vi da ben toi",
    "day co the la lan cuoi",
    "toi di day",
    "toi se roi di",
    "mong moi nguoi song tot",
]

SELF_WORTH = [
    "toi that bai",
    "toi vo dung",
    "toi la ganh nang cua moi nguoi",
    "toi lam gi cung hong",
    "toi chi lam phien nguoi khac",
]

EXHAUSTION = [
    "met moi qua",
    "kiet suc roi",
    "khong con suc nua",
    "toi sap guc nga",
    "toi khong chiu noi nua",
]

GENZ_VARIANTS = [
    "muon dang xuat",
    "muon die",
    "muon out",
    "end game di",
    "quit game di",
    "toi muon off",
    "toi out day",
    "bye cuoc doi",
    "goodbye moi nguoi",
    "toi sap roi",
    "toi khong tru duoc nua",
    "muon chet",
    "ko muon song",
    "k muon song nua",
    "chan song roi",
    "met vl roi",
    "toi vo gia tri",
    "song lam gi",
    "i want to die",
    "i wanna die",
    "kill myself",
    "end my life",
    "no reason to live",
    "im done with life",
]

SOS_KEYWORDS = list(
    set(
        EXPLICIT_HIGH_RISK
        + VIOLENCE_HIGH_RISK
        + IMPLICIT_MEDIUM_RISK
        + HOPELESSNESS
        + GENZ_VARIANTS
        + FAREWELL_SIGNALS
        + SELF_WORTH
        + EXHAUSTION
    )
)


def _normalize_text(message: str) -> str:
    lowered = (message or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")
    compact = re.sub(r"[^a-z0-9\s]", " ", no_accent)
    compact = re.sub(r"\s+", " ", compact).strip()
    slang_map = {
        "ko": "khong",
        "k ": "khong ",
        "khum": "khong",
        "dc": "duoc",
        "chetme": "chet me",
        "vl": "rat",
    }
    for src, dst in slang_map.items():
        compact = compact.replace(src, dst)
    return re.sub(r"\s+", " ", compact).strip()


_SOS_KEYWORDS_NORMALIZED = {_normalize_text(key) for key in SOS_KEYWORDS if _normalize_text(key)}
_HIGH_RISK_PATTERNS = [
    re.compile(r"\b(tao|toi|minh|t)\s*(dang|se|di|muon)?\s*(di\s*)?chet\b"),
    re.compile(r"\b(tao|toi|minh|t)\s*(se|dang)?\s*(di|roi)\s*day\b"),
    re.compile(r"\b(di|dinh)\s*chet\s*(day|thoi|cho\s*xong)?\b"),
    re.compile(r"\b(di|de)\s*chet\b"),
    re.compile(r"\b(tu\s*tu|tu\stu)\b"),
    re.compile(r"\b(kill\s*myself|end\s*my\s*life|want\s*to\s*die)\b"),
    re.compile(r"\b(muon|se|dinh)\s*giet\s*(no|nguoi|thang|con)\b"),
    re.compile(r"\b(tao|toi|minh)\s*(muon|se|dinh)\s*giet\b"),
    re.compile(r"\b(kill\s*(him|her|them|someone)|hurt\s*someone)\b"),
]


def keyword_hit(message: str) -> bool:
    normalized = _normalize_text(message)
    if any(key in normalized for key in _SOS_KEYWORDS_NORMALIZED):
        return True
    return any(p.search(normalized) is not None for p in _HIGH_RISK_PATTERNS)


def violence_keyword_hit(message: str) -> bool:
    normalized = _normalize_text(message)
    violence_terms = ("muon giet", "se giet", "dinh giet", "kill him", "kill her", "kill them", "hurt someone")
    return any(term in normalized for term in violence_terms) or any(
        p.search(normalized) is not None for p in _HIGH_RISK_PATTERNS[-3:]
    )


def heuristic_distress(message: str) -> float:
    """Cheap lexical score 0–1 for routing (auditable keywords)."""
    normalized = _normalize_text(message)
    if violence_keyword_hit(normalized):
        return 0.97
    if keyword_hit(normalized):
        return 0.96
    score = 0.12
    if any(w in normalized for w in ("buon", "met", "stress", "lo lang", "suy nghi tieu cuc", "tuyet vong")):
        score += 0.15
    if any(w in normalized for w in ("chet", "tu tu", "khong song", "khong muon song", "giet")):
        score = max(score, 0.88)
    if any(w in normalized for w in ("tao", "may", "choi voi", "dieu nay ket thuc")):
        score += 0.04
    return clamp01(score)


def contextual_distress(message: str, recent_user_messages: list[str] | None = None, *, max_turns: int = 4) -> float:
    current = heuristic_distress(message)
    history = [heuristic_distress(m) for m in (recent_user_messages or []) if str(m or "").strip()]
    if not history:
        return current
    window = history[-max_turns:] + [current]
    # Exponential weighting to emphasize latest turns in a short crisis window.
    weighted_total = 0.0
    weighted_sum = 0.0
    for idx, score in enumerate(window, start=1):
        weight = 1.45**idx
        weighted_total += score * weight
        weighted_sum += weight
    rolling = weighted_total / weighted_sum if weighted_sum else current
    trend_boost = 0.0
    if len(window) >= 3 and window[-1] >= window[-2] >= window[-3]:
        trend_boost += 0.08
    if len(window) >= 3 and all(v >= 0.72 for v in window[-3:]):
        trend_boost += 0.12
    if window[:-1]:
        spike = max(0.0, current - min(window[:-1]))
        if spike >= 0.25:
            trend_boost += 0.07
    severe_history_count = sum(1 for v in history[-max_turns:] if v >= 0.9)
    if severe_history_count >= 2 and current >= 0.1:
        return 0.94
    return clamp01(max(current, rolling + trend_boost))


def decide_sos(message: str, recent_user_messages: list[str] | None = None) -> tuple[bool, float]:
    """
    Returns (sos_triggered, distress_score).
    SOS = explicit keyword path OR distress at/above critical heuristic.
    recent_user_messages: optional context for future pattern analysis (reserved).
    """
    current = heuristic_distress(message)
    combined = contextual_distress(message, recent_user_messages)
    if violence_keyword_hit(message):
        return True, max(combined, 0.97)
    if keyword_hit(message):
        return True, max(combined, 0.96)
    if combined >= 0.9:
        return True, combined
    if current >= 0.86 and combined >= 0.84:
        return True, combined
    # Elevated text without explicit SOS keywords stays in LLM path
    return False, combined


# --- SOS message variants (rule-based, no LLM) ---
# Turn 0: first contact — warm + urgent safety, open question about location/company.
# Turn 1: follow-up — acknowledge they're still here, encourage calling hotline.
# Turn 2+: sustained — validate courage, grounding step, ask what's hardest right now.
_ASSISTANT_TEXTS_SOS_VI = [
    (
        "Mình nghe bạn, và mình đang ở đây với bạn ngay lúc này. "
        "Mình lo lắng cho bạn — hãy tạm rời các vật có thể gây hại "
        "và cố gắng ở nơi có người khác nếu được. "
        "Các đường dây hỗ trợ bên dưới luôn sẵn sàng lắng nghe, hoàn toàn bảo mật. "
        "Bạn có thể nói cho mình biết bạn đang ở đâu và có ai ở gần không?"
    ),
    (
        "Mình vẫn ở đây cùng bạn và mình nghe từng điều bạn chia sẻ. "
        "Bạn không cần phải một mình với cảm giác này — mình và các đường dây hỗ trợ đều ở đây cho bạn. "
        "Nếu cảm giác quá nặng, chỉ cần gọi một trong những số bên dưới — "
        "nghe giọng ai đó đôi khi cũng giúp được rất nhiều. "
        "Bạn đang cảm thấy thế nào ngay lúc này?"
    ),
    (
        "Mình vẫn ở đây — bạn đã rất can đảm khi tiếp tục chia sẻ. "
        "Mình muốn bạn an toàn hơn bao giờ hết. "
        "Nếu cảm giác đang rất khó, hãy gọi ngay đường dây khẩn cấp bên dưới. "
        "Nếu bạn có thể, hãy thử hít vào 4 giây, thở ra 6 giây — mình sẽ ở đây chờ. "
        "Điều gì đang làm bạn khó thở nhất ngay lúc này?"
    ),
]

# Variant for when user expresses isolation/loneliness (e.g. "không ai cả, tôi sống một mình").
_ASSISTANT_TEXT_SOS_ALONE_VI = (
    "Mình nghe bạn đang một mình và điều đó có thể rất nặng nề lúc này. "
    "Bạn không phải mang điều này một mình — mình đang ở đây, "
    "và các đường dây hỗ trợ bên dưới cũng sẵn sàng lắng nghe bất kỳ lúc nào, hoàn toàn bảo mật. "
    "Bạn có thể kể cho mình nghe điều gì đang xảy ra với bạn không?"
)

# Backward-compat default (used by tests and any legacy callers).
_ASSISTANT_TEXT_SOS_VI = _ASSISTANT_TEXTS_SOS_VI[0]

_ALONE_KEYWORDS_NORMALIZED = {
    "song mot minh", "khong ai ca", "khong co ai", "mot minh", "co don",
    "lonely", "alone", "khong ai hieu", "khong ai quan tam", "khong ai can",
}


def is_alone_signal(user_message: str) -> bool:
    """Return True when the user message expresses isolation or loneliness."""
    normalized = _normalize_text(user_message)
    return any(kw in normalized for kw in _ALONE_KEYWORDS_NORMALIZED)


def assistant_text_for_sos(user_message: str = "", session_sos_count: int = 0) -> str:
    """Select an SOS response variant based on user context and turn depth.

    session_sos_count: number of previous SOS assistant turns in this session.
    """
    normalized = _normalize_text(user_message)
    if any(kw in normalized for kw in _ALONE_KEYWORDS_NORMALIZED):
        return _ASSISTANT_TEXT_SOS_ALONE_VI
    idx = min(session_sos_count, len(_ASSISTANT_TEXTS_SOS_VI) - 1)
    return _ASSISTANT_TEXTS_SOS_VI[idx]


def assistant_text_for_stored_message_sos() -> str:
    """Backward-compat alias. Prefer assistant_text_for_sos() for new call sites."""
    return _ASSISTANT_TEXT_SOS_VI


def build_sos_chat_response_data(
    session_id: str,
    snapshot: SafetySnapshot,
    *,
    assistant_text: str | None = None,
    voice_hint_text: str | None = None,
) -> dict[str, Any]:
    text = assistant_text or _ASSISTANT_TEXT_SOS_VI
    vhint = voice_hint_text or (
        "Cậu có thể bấm gọi để nói chuyện trực tiếp với tổng đài hỗ trợ để nhận sự trợ giúp chuyên sâu hơn. "
        "Mình vẫn ở đây trong lúc cậu cân nhắc."
    )
    return {
        "session_id": session_id,
        "sos_triggered": True,
        "conversation_mode": "de_escalation",
        "distress_score": snapshot.distress_score,
        "safety_tier": snapshot.safety_tier,
        "voice_session_offered": True,
        "suggest_voice": True,
        "voice_hint": vhint,
        "emergency_actions": {
            "outbound_call_to_user_queued": False,
            "trusted_contact_notification_queued": False,
            "user_alert_sent": False,
        },
        "risk_level": snapshot.risk_level,
        "agent_display_name": CHAT_AGENT_DISPLAY_NAME,
        "reply": None,
        "assistant_text": text,
        "assistant_strategy": {
            "keep_engaged": True,
            "encourage_external_help": True,
            "avoid_hard_stop": True,
        },
        "micro_actions": [
            {
                "type": "grounding",
                "label": "Nhắm mắt lại và nghĩ về 5 kí ức khiến cậu hạnh phúc nhất",
            },
            {"type": "breathing", "label": "Hít vào 4 giây, giữ 4 giây, thở ra 6 giây"},
        ],
        "hotline_cards": hotline_cards_sos(),
        "grounding_actions": [{"id": "grounding_54321"}, {"id": "breath_478"}],
        "referral_options": [{"type": "counselor"}, {"type": "trusted_contact"}],
        "followup_priority": True,
        "routing_history": ["sos_handler"],
    }


def snapshot_for_sos(distress: float) -> SafetySnapshot:
    return build_snapshot(
        distress,
        sos_triggered=True,
        voice_hint=DISTRESS_VOICE_HINT,
        critical=DISTRESS_CRITICAL,
    )
