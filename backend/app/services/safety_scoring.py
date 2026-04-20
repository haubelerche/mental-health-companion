"""
Map distress_score (0–1) ↔ risk_level (0–5) ↔ safety_tier (API_SPEC).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EscalationReason = Literal["none", "threshold_crossed", "rapid_escalation"]



"""nhận đầu vào là điểm số bất ổn tâm lý (distress score) từ 0 đến 1 (có thể do Agent LLM đánh giá trả về) 
và chuyển đổi điểm số đó thành các mức độ rủi ro, 
trạng thái an toàn, và thái độ/phương thức mà chatbot nên dùng để phản hồi"""


SafetyTier = Literal["normal", "elevated", "voice_recommended", "critical"]


ConversationMode = Literal["normal", "supportive", "de_escalation"]


@dataclass(frozen=True)
class SafetySnapshot:
    distress_score: float
    risk_level: int
    safety_tier: SafetyTier
    conversation_mode: ConversationMode


@dataclass(frozen=True)
class EscalationSignal:
    rolling_window_turns: int
    rolling_score: float
    delta_score: float
    escalate: bool
    trigger_reason: str


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))   # buộc điểm số nằm trong khoảng 0 đến 1


def distress_to_risk_level(score: float) -> int:
    s = clamp01(score)

    # đoạn này ép điểm số về thang đánh giá rủi ro 0-5
    if s < 0.2:
        return 0
    if s < 0.35:
        return 1
    if s < 0.5:
        return 2
    if s < 0.65:
        return 3
    if s < 0.8:
        return 4
    return 5


def distress_to_safety_tier(score: float, *, voice_hint: float, critical: float) -> SafetyTier:
    # đoạn này điểm số quyết định phản ứng của chatbot để nó quyết định nên làm gì

    s = clamp01(score)
    if s > critical:
        return "critical"
    if s >= voice_hint:
        return "voice_recommended"
    if s >= 0.35:
        return "elevated"
    return "normal"


def tier_to_conversation_mode(tier: SafetyTier, *, sos: bool) -> ConversationMode:

    """ Quyết định chế độ nói chuyện của Bot.
    Bình thường bot chat ở chế độ normal.
    Nếu tâm lý bất ổn (critical, elevated, voice_recommended) -> Bot chuyển sang supportive (giọng điệu hỗ trợ, đồng cảm).
    Đặc biệt, nếu hệ thống có bật phát tín hiệu cấp cứu (sos=True) -> Bot lập tức chuyển đổi sang chế độ de_escalation (vỗ về, giảm căng thẳng rủi ro tính mạng)."""
    if sos:
        return "de_escalation"
    if tier == "critical":
        return "supportive"
    if tier in ("elevated", "voice_recommended"):
        return "supportive"
    return "normal"


def build_snapshot(
    distress_score: float,
    *,
    sos_triggered: bool,
    voice_hint: float,
    critical: float,
) -> SafetySnapshot:
    s = clamp01(distress_score)
    tier = distress_to_safety_tier(s, voice_hint=voice_hint, critical=critical)
    if sos_triggered:
        tier = "critical"
    rl = distress_to_risk_level(s)
    if sos_triggered:
        rl = max(rl, 4)
    mode = tier_to_conversation_mode(tier, sos=sos_triggered)
    return SafetySnapshot(
        distress_score=s,
        risk_level=rl,
        safety_tier=tier,
        conversation_mode=mode,
    )


def compute_escalation_signal(
    *,
    current_distress: float,
    previous_distress: list[float],
    threshold: float,
    delta_threshold: float,
    window_turns: int,
) -> EscalationSignal:
    window = [clamp01(x) for x in previous_distress[-max(0, window_turns - 1) :]]
    window.append(clamp01(current_distress))
    if not window:
        return EscalationSignal(rolling_window_turns=0, rolling_score=0.0, delta_score=0.0, escalate=False, trigger_reason="none")

    rolling_score = sum(window) / float(len(window))
    baseline = window[0]
    delta = clamp01(window[-1] - baseline)

    if window[-1] >= threshold:
        return EscalationSignal(
            rolling_window_turns=len(window),
            rolling_score=rolling_score,
            delta_score=delta,
            escalate=True,
            trigger_reason="threshold_crossed",
        )
    if window[-1] >= 0.7 and delta >= delta_threshold:
        return EscalationSignal(
            rolling_window_turns=len(window),
            rolling_score=rolling_score,
            delta_score=delta,
            escalate=True,
            trigger_reason="rapid_escalation",
        )
    return EscalationSignal(
        rolling_window_turns=len(window),
        rolling_score=rolling_score,
        delta_score=delta,
        escalate=False,
        trigger_reason="none",
    )