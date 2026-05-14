from __future__ import annotations

import re
import unicodedata

from app.advisors.base import BaseAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.services.schemas.contracts import AdvisorAdvice


_SAFETY_TRIGGER_RE = re.compile(
    r"\b(tram cam|roi loan|chan doan|benh gi|bipolar|luong cuc|panic|tu tu|tu hai|chet)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", no_accent.replace("đ", "d"))


class SafetyBoundaryAdvisor(BaseAdvisor):
    advisor_id = "safety_policy_layer"

    def __init__(self, *, knowledge_store: AdvisorKnowledgeStore | None = None) -> None:
        self._knowledge = knowledge_store or AdvisorKnowledgeStore()

    def run(self, *, user_message: str, context_summary: str = "") -> AdvisorAdvice:
        records = self._knowledge.retrieve(
            advisor_id=self.advisor_id,
            user_message=user_message,
            context_summary=context_summary,
            limit=2,
        )
        if not records:
            return AdvisorAdvice(advisor_id=self.advisor_id, confidence=0.0, should_use=False)
        text = _normalize(f"{user_message} {context_summary}")
        should_use = bool(_SAFETY_TRIGGER_RE.search(text)) or any(
            any(token in text for token in ("diagnosis", "clinical_boundary", "non_diagnostic"))
            for record in records
        )
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.9 if should_use else 0.55,
            evidence_refs=[record.item_id for record in records],
            advice_to_friend=[line for record in records for line in record.advice_lines(limit=2)][:3],
            suggested_response_moves=[
                "Không chẩn đoán; phản hồi bằng mô tả cảm xúc đời thường và gợi ý bước an toàn tiếp theo.",
                "Nếu người dùng hỏi trực tiếp về bệnh, nói rõ rằng Serene không thể chẩn đoán qua chat.",
            ],
            forbidden_moves=[line for record in records for line in record.forbidden_moves][:3],
            should_use=should_use,
        )
