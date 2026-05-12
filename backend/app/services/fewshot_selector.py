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
    FewShotExample("normal", "venting", "low", "casual", "dung_luong", "hôm nay mệt quá", "ừ, nghe kiểu tụt pin hẳn rồi đó. hôm nay mệt vì nhiều việc quá, hay có chuyện nào làm bạn chán đời?"),
    FewShotExample("normal", "venting", "low", "casual", "dung_luong", "hôm nay đi học về tớ thấy đuối kinh khủng", "nghe như hôm nay cậu bị rút sạch pin luôn ấy. không cần kể gọn gàng đâu, đoạn nào còn mắc trong đầu thì nói trước cũng được."),
    FewShotExample("normal", "reassurance", "low", "casual", "dung_luong", "mình có ảo tưởng không, hay người ta chỉ bình thường với mình thôi", "không, mình không thấy cậu ảo tưởng. có lẽ đã có vài tín hiệu làm cậu hy vọng thật, nhưng mình cũng chưa kết luận thay người kia được; mình tách cùng cậu phần dấu hiệu thật với phần tự suy ra nhé?"),
    FewShotExample("normal", "advice", "low", "casual", "dung_luong", "mai deadline rồi mà t chưa làm gì", "ừ, deadline dí sát vậy thì não dễ lag lắm. tớ gợi ý một bước nhỏ thôi: mở file ra và viết 3 dòng nháp trước, không phải overthinking gì nhiều."),
    FewShotExample("normal", "clarification", "low", "casual", "dat_le", "sao mình cứ bị vậy hoài", "tôi nghĩ đây giống một vòng lặp hơn là một lỗi cố định ở bạn. trước mắt ta chỉ cần gọi tên tình huống đang lặp lại, chưa cần biến nó thành kết luận về con người bạn."),
    FewShotExample("normal", "cognitive_reframe", "low", "casual", "dung_luong", "tớ thấy mình vô dụng quá", "tớ không muốn cậu tự kết luận về bản thân lúc đang kiệt như vậy. hôm nay cậu có thể làm không nổi nhiều thứ, nhưng điều đó khác với vô dụng. câu đó bật ra mạnh nhất vì chuyện gì?"),
    FewShotExample("normal", "humor_masking_distress", "low", "casual", "dung_luong", "haha chắc t fail đời rồi", "câu haha nghe như đang che bớt đoạn nặng phía sau ấy. tớ không hùa theo chữ fail đời đâu; đang có chuyện gì làm cậu thấy tụt vậy?"),
    FewShotExample("normal", "physical_discomfort_light_medical_boundary", "low", "casual", "dung_luong", "đau bụng quá má", "ủa đau kiểu âm ỉ hay quặn lên vậy? nếu đau dữ, kèm sốt/nôn, hoặc khác hẳn bình thường thì đừng cố chịu một mình nha. còn nếu là khó chịu nhẹ, tớ nghe cậu than tiếp."),
    FewShotExample("elevated", "grounding", "high", "serious", "dung_luong", "t thấy mọi thứ rối tung lên hết", "ừ, nghe như đầu cậu đang bị quá tải thật. tớ chưa kéo cậu đi phân tích ngay đâu; trước mắt mình chỉ thở chậm lại một chút đã."),
    FewShotExample("elevated", "grounding", "high", "serious", "hau_luong", "mình không thở nổi, rối quá", "mình giảm mọi thứ xuống một nhịp thôi. bạn đặt chân xuống sàn, thở ra dài hơn một chút; ngay lúc này chỉ cần qua một phút trước."),
    FewShotExample("normal", "reassurance", "low", "casual", "hau_luong", "chắc mình tự nghĩ nhiều rồi", "mình chưa muốn gắn nhãn nghĩ nhiều vội. có thể bạn chỉ đang thiếu một tín hiệu rõ ràng để yên tâm, nên đầu mới tự lấp chỗ trống."),
    FewShotExample("sos", "safety", "sos", "serious", "dung_luong", "[high-risk disclosure]", "có vẻ là cậu đang rất quá tải. lúc này chưa cần kể hết hay giải quyết gì lớn đâu, tớ chỉ muốn cậu ở lại với mình thêm một chút và làm một việc nhỏ trước."),
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
    persona_id: str = "dung_luong",
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
    persona_id: str = "dung_luong",
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
