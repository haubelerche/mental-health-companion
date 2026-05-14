from __future__ import annotations

import re
import unicodedata

from app.advisors.base import BaseAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.services.schemas.contracts import AdvisorAdvice


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.replace("đ", "d").replace("Đ", "D").lower()).strip()


class NutritionSupportAdvisor(BaseAdvisor):
    advisor_id = "nutrition_support_advisor"

    def __init__(self, *, knowledge_store: AdvisorKnowledgeStore | None = None) -> None:
        self._knowledge = knowledge_store or AdvisorKnowledgeStore()

    def run(self, *, user_message: str, context_summary: str = "") -> AdvisorAdvice:
        text = _normalize(user_message)
        should_use = any(k in text for k in (
            "an gi",
            "dinh duong",
            "bo bua",
            "khong an",
            "bua sang",
            "bua trua",
            "bua toi",
            "goi y dinh duong",
            "calo",
            "protein",
            "meal",
            "nutrition",
            "an com",
            "dop gi",
            "hoc gi",
            "nap vao",
            "da bat",
        ))
        records = self._knowledge.retrieve(
            advisor_id=self.advisor_id,
            user_message=user_message,
            context_summary=context_summary,
            limit=2,
        )
        if not records:
            return AdvisorAdvice(advisor_id=self.advisor_id, confidence=0.0, should_use=False)
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.75 if should_use else 0.45,
            evidence_refs=[record.item_id for record in records],
            advice_to_friend=[line for record in records for line in record.advice_lines(limit=2)][:3],
            suggested_response_moves=[line for record in records for line in record.move_lines(limit=1)][:2],
            forbidden_moves=[
                "medical_nutrition_claim",
                "cure_claim",
                "shame_or_guilt_language",
            ],
            should_use=should_use,
        )
