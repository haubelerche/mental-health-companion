from __future__ import annotations

from app.advisors.base import BaseAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.services.schemas.contracts import AdvisorAdvice


class RelevanceNaturalnessCritic(BaseAdvisor):
    advisor_id = "relevance_naturalness_critic"

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
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.66,
            evidence_refs=[record.item_id for record in records],
            advice_to_friend=[line for record in records for line in record.advice_lines(limit=2)][:3],
            suggested_response_moves=[line for record in records for line in record.move_lines(limit=1)][:2],
            forbidden_moves=["robotic_tone"],
            should_use=len(user_message) > 240,
        )
