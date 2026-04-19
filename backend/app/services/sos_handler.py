"""
Rule-based SOS handler (no LLM for crisis decision). BACKEND_PLAN §6.3, §7.2.
"""

from __future__ import annotations

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
        + IMPLICIT_MEDIUM_RISK
        + HOPELESSNESS
        + GENZ_VARIANTS
        + FAREWELL_SIGNALS
        + SELF_WORTH
        + EXHAUSTION
    )
)


def keyword_hit(message: str) -> bool:
    lowered = message.lower()
    return any(key in lowered for key in SOS_KEYWORDS)


def heuristic_distress(message: str) -> float:
    """Cheap lexical score 0–1 for routing (auditable keywords)."""
    if keyword_hit(message):
        return 0.94
    lowered = message.lower()
    score = 0.12
    if any(w in lowered for w in ("buon", "met", "stress", "lo lang", "suy nghi tieu cuc")):
        score += 0.15
    if any(w in lowered for w in ("chet", "tu tu", "khong song")):
        score = max(score, 0.85)
    return clamp01(score)


def decide_sos(message: str) -> tuple[bool, float]:
    """
    Returns (sos_triggered, distress_score).
    SOS = explicit keyword path OR distress at/above critical heuristic.
    """
    raw = heuristic_distress(message)
    if keyword_hit(message):
        return True, max(raw, 0.94)
    # Elevated text without explicit SOS keywords stays in LLM path
    return False, raw


_ASSISTANT_TEXT_SOS_VI = (
    "Mình đang ở đây với cậu. Mình muốn giúp cậu an toàn ngay lúc này"
    "nếu được, mình muốn cậu thử một việc nhỏ cùng mình trong lúc cậu cân nhắc thêm bước tiếp theo."
)


def assistant_text_for_stored_message_sos() -> str:
    return _ASSISTANT_TEXT_SOS_VI


def build_sos_chat_response_data(
    session_id: str,
    snapshot: SafetySnapshot,
    *,
    voice_hint_text: str | None = None,
) -> dict[str, Any]:
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
        "assistant_text": _ASSISTANT_TEXT_SOS_VI,
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
    }


def snapshot_for_sos(distress: float) -> SafetySnapshot:
    return build_snapshot(
        distress,
        sos_triggered=True,
        voice_hint=DISTRESS_VOICE_HINT,
        critical=DISTRESS_CRITICAL,
    )
