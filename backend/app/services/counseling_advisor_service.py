from __future__ import annotations

import re
import unicodedata

from app.core.config import get_settings
from app.services.advisor_case_retriever import AdvisorCaseRetriever
from app.services.schemas.advisors import AdvisorCase, CounselingGuidance
from app.services.schemas.contracts import AdvisorAdvice


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.replace("Ä‘", "d").lower()).strip()


def _first_nonempty(items: list[str], fallback: str = "") -> str:
    for item in items:
        text = str(item or "").strip()
        if text:
            return text
    return fallback


def _dedupe(items: list[str], *, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        key = _normalize(text)
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text[:280])
        if len(out) >= limit:
            break
    return out


def _infer_patterns(user_message: str) -> list[str]:
    text = _normalize(user_message)
    patterns: list[str] = []
    if any(k in text for k in ("loi tai minh", "tu trach", "do minh", "minh te", "vo dung", "lam hong")):
        patterns.append("self_blame")
    if any(k in text for k in ("chac", "kieu gi cung", "fail", "hong het", "khong con cach")):
        patterns.append("catastrophizing")
    if any(k in text for k in ("ho nghi", "ho ghe", "bi danh gia", "khong ai thich")):
        patterns.append("mind_reading")
    if any(k in text for k in ("khong biet lam sao", "bat luc", "mac ket", "het cach")):
        patterns.append("helplessness_belief")
    if any(k in text for k in ("lam vua long", "so that vong", "khong dam tu choi")):
        patterns.append("people_pleasing")
    if any(k in text for k in ("qua tai", "kiet suc", "het pin", "can kiet", "met")):
        patterns.append("overload_loop")
    return patterns[:5]


def _fallback_guidance(user_message: str, interaction_need: str | None) -> CounselingGuidance:
    patterns = _infer_patterns(user_message)
    text = _normalize(user_message)
    if any(k in text for k in ("bo bua", "khong an", "u an khong ngon", "mat ngu", "khong ngu")):
        step = "chọn một việc chăm thân rất nhỏ trước: nước, món dễ nuốt, hoặc nằm nghỉ không màn hình vài phút"
        goal = "giúp người dùng giảm tải cơ thể trước khi phân tích sâu"
    elif any(k in text for k in ("deadline", "qua tai", "can kiet", "het minh", "lam viec")):
        step = "chọn một việc làm được trong 10 phút để lấy lại chút quyền điều khiển"
        goal = "giúp người dùng tách quá tải khỏi kết luận rằng mình thất bại"
    elif "self_blame" in patterns:
        step = "tách một cột sự kiện thật và một cột phần não đang tự kết tội mình"
        goal = "giảm tự trách và đưa người dùng về dữ kiện cụ thể"
    else:
        step = "chọn một mảnh cụ thể nhất của chuyện này để gỡ trước"
        goal = "giúp người dùng thấy vấn đề có thể được chia nhỏ"
    return CounselingGuidance(
        case_understanding="Người dùng đang đưa ra một tín hiệu căng thẳng có nhu cầu được hiểu và gỡ rối có cấu trúc.",
        likely_patterns=patterns,
        response_goal=goal,
        recommended_moves=[
            "validate briefly without turning the whole reply into empathy only",
            "name the main loop in everyday language",
            "offer one small next step",
        ],
        one_reflection_question="Phần nào là chuyện thật sự đã xảy ra, phần nào là phần não đang suy diễn thêm?",
        one_practical_step=step,
        avoid=["diagnosis", "generic reassurance", "too many questions", "raw clinical labels"],
        case_refs=[],
        metadata={"source": "heuristic", "interaction_need": interaction_need or "unknown"},
    )


class CounselingAdvisorService:
    """Build internal counseling guidance without writing final user-facing text."""

    advisor_id = "counseling_advisor"

    def __init__(self, *, retriever: AdvisorCaseRetriever | None = None) -> None:
        settings = get_settings()
        self._retriever = retriever or AdvisorCaseRetriever(api_key=settings.openai_api_key)

    def build_guidance(
        self,
        *,
        user_message: str,
        interaction_need: str | None = None,
        top_k: int = 4,
    ) -> CounselingGuidance:
        result = self._retriever.retrieve(
            user_message,
            interaction_need=interaction_need,
            top_k=top_k,
            approved_only=True,
        )
        if not result.cases:
            return _fallback_guidance(user_message, interaction_need)
        return self._from_cases(result.cases, user_message=user_message, interaction_need=interaction_need)

    def as_advisor_advice(self, *, guidance: CounselingGuidance) -> AdvisorAdvice:
        moves = _dedupe(
            [
                guidance.one_practical_step or "",
                guidance.one_reflection_question or "",
                guidance.response_goal,
                *[move for move in guidance.recommended_moves if not re.search(r"\b(validate|formulate|offer|briefly)\b", move, re.IGNORECASE)],
            ],
            limit=4,
        )
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.82 if guidance.case_refs else 0.68,
            evidence_refs=guidance.case_refs,
            advice_to_friend=[
                guidance.case_understanding,
                guidance.response_goal,
            ],
            suggested_response_moves=moves,
            forbidden_moves=list(guidance.avoid),
            should_use=True,
        )

    @staticmethod
    def _from_cases(
        cases: list[AdvisorCase],
        *,
        user_message: str,
        interaction_need: str | None,
    ) -> CounselingGuidance:
        primary = cases[0]
        patterns = _dedupe(
            [tag for case in cases for tag in case.cognitive_pattern_tags] + _infer_patterns(user_message),
            limit=5,
        )
        intervention_steps = _dedupe([step for case in cases for step in case.intervention_steps], limit=4)
        reflection_questions = _dedupe([q for case in cases for q in case.reflection_questions], limit=3)
        avoid = _dedupe(
            [item for case in cases for item in case.do_not_say]
            + [flag for case in cases for flag in case.risk_flags]
            + ["diagnosis", "generic reassurance", "too many questions", "copying source response"],
            limit=8,
        )
        recommended = _dedupe(
            [
                primary.recommended_approach or "",
                *intervention_steps,
                _first_nonempty([item for case in cases for item in case.do_say]),
            ],
            limit=5,
        )
        return CounselingGuidance(
            case_understanding=(
                primary.primary_problem
                or primary.source_response_summary
                or "Người dùng đang mô tả một khó khăn cảm xúc cần được hiểu và gỡ từng bước."
            ),
            likely_patterns=patterns,
            response_goal=primary.counseling_goal or "giúp người dùng nhìn rõ vấn đề và chọn một bước nhỏ an toàn",
            recommended_moves=recommended or [
                "validate briefly",
                "formulate the pattern in plain language",
                "offer one small practical step",
            ],
            one_reflection_question=reflection_questions[0] if reflection_questions else None,
            one_practical_step=intervention_steps[0] if intervention_steps else None,
            avoid=avoid,
            case_refs=[case.case_id for case in cases],
            metadata={
                "source": "advisor_case_library",
                "interaction_need": interaction_need or primary.interaction_need or "unknown",
                "case_count": len(cases),
            },
        )
