"""Small risk-aware few-shot selector for Vietnamese chat style references."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.interaction_need_classifier import classify_interaction_need


@dataclass(frozen=True)
class FewShotExample:
    risk_mode: str
    interaction_need: str
    distress_band: str
    user_tone: str
    persona_id: str
    user: str
    assistant: str


_EXAMPLES: tuple[FewShotExample, ...] = (
    FewShotExample("normal", "venting", "low", "casual", "ban_than", "hôm nay mệt quá", "ừ, nghe kiểu tụt pin hẳn rồi đó. hôm nay mệt vì nhiều việc quá, hay có chuyện nào làm bạn chán đời?"),
    FewShotExample("normal", "advice", "low", "casual", "ban_than", "mai deadline rồi mà t chưa làm gì", "ừ, deadline dí sát vậy thì não dễ lag lắm. mình gợi ý một bước nhỏ thôi: mở file ra và viết 3 dòng nháp trước, không phải overthinking gì nhiều."),
    FewShotExample("elevated", "grounding", "high", "serious", "ban_than", "t thấy mọi thứ rối tung lên hết", "ừ, nghe như đầu bạn đang bị quá tải thật. mình chưa kéo bạn đi phân tích ngay đâu; trước mắt mình chỉ muốn bạn thở chậm lại một chút đã."),
    FewShotExample("sos", "safety", "sos", "serious", "ban_than", "[high-risk disclosure]", "có vẻ là bạn đang rất quá tải. lúc này chưa cần kể hết hay giải quyết gì lớn đâu, mình chỉ muốn bạn ở lại với mình thêm một chút và làm một việc nhỏ trước."),
)


def _band(distress_score: float, risk_mode: str) -> str:
    if risk_mode in {"sos", "safety"}:
        return "sos"
    if distress_score >= 0.55:
        return "high"
    return "low"


def select_fewshots(
    *,
    risk_mode: str,
    interaction_need: str,
    distress_score: float,
    user_tone: str = "casual",
    persona_id: str = "ban_than",
    limit: int = 3,
) -> list[FewShotExample]:
    normalized_risk = "sos" if risk_mode == "safety" else risk_mode
    band = _band(distress_score, normalized_risk)

    def score(example: FewShotExample) -> int:
        return sum(
            (
                example.risk_mode == normalized_risk,
                example.interaction_need == interaction_need,
                example.distress_band == band,
                example.user_tone == user_tone,
                example.persona_id == persona_id,
            )
        )

    ranked = sorted(_EXAMPLES, key=score, reverse=True)
    return ranked[: max(0, min(limit, 3))]


def build_fewshot_style_block(
    *,
    user_message: str,
    risk_mode: str,
    distress_score: float,
    persona_id: str = "ban_than",
    limit: int = 3,
) -> str:
    interaction_need = classify_interaction_need(
        user_message,
        distress_score=distress_score,
        sos_triggered=risk_mode in {"sos", "safety"},
    )
    examples = select_fewshots(
        risk_mode=risk_mode,
        interaction_need=interaction_need,
        distress_score=distress_score,
        user_tone="serious" if distress_score >= 0.55 else "casual",
        persona_id=persona_id,
        limit=limit,
    )
    if not examples:
        return ""
    lines = [
        "[STYLE REFERENCES - do not copy verbatim]",
        "Use these only for Vietnamese texting rhythm, brevity, and safety level.",
    ]
    for idx, example in enumerate(examples, start=1):
        lines.append(f"{idx}. User: {example.user}")
        lines.append(f"   Serene: {example.assistant}")
    return "\n".join(lines)
