from __future__ import annotations

from app.advisors.base import BaseAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.services.schemas.contracts import AdvisorAdvice


class ReflectionAdvisor(BaseAdvisor):
    advisor_id = "reflection_advisor"

    def __init__(self, *, knowledge_store: AdvisorKnowledgeStore | None = None) -> None:
        self._knowledge = knowledge_store or AdvisorKnowledgeStore()

    def run(self, *, user_message: str, context_summary: str = "") -> AdvisorAdvice:
        records = self._knowledge.retrieve(
            advisor_id=self.advisor_id,
            user_message=user_message,
            context_summary=context_summary,
            limit=1,
        )
        if not records:
            return AdvisorAdvice(advisor_id=self.advisor_id, confidence=0.0, should_use=False)
        record = records[0]
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.7,
            evidence_refs=[record.item_id],
            advice_to_friend=record.advice_lines(limit=2),
            suggested_response_moves=record.move_lines(limit=1),
            forbidden_moves=["multi_question_interview"],
            should_use=True,
        )
