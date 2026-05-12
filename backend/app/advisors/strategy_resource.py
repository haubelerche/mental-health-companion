from __future__ import annotations

from app.advisors.base import BaseAdvisor
from app.advisors.knowledge_store import AdvisorKnowledgeStore
from app.services.resource_selector import ResourceSelector
from app.services.schemas.contracts import AdvisorAdvice
from app.services.schemas.resources import ResourceSelectionInput


class StrategyResourceAdvisor(BaseAdvisor):
    advisor_id = "strategy_resource_advisor"

    def __init__(self, *, knowledge_store: AdvisorKnowledgeStore | None = None) -> None:
        self._selector = ResourceSelector()
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
        pick = self._selector.select(
            ResourceSelectionInput(
                conversation_need="task_breakdown",
                emotion="overwhelmed",
                time_available_minutes=5,
                user_preference="short",
            )
        )
        return AdvisorAdvice(
            advisor_id=self.advisor_id,
            confidence=0.78,
            evidence_refs=[record.item_id for record in records] + [pick.resource_id],
            advice_to_friend=[line for record in records for line in record.advice_lines(limit=2)][:3],
            suggested_response_moves=[line for record in records for line in record.move_lines(limit=1)][:2]
            + [f"Gợi ý resource `{pick.resource_id}` nếu người dùng muốn một bước nhỏ ngay."],
            forbidden_moves=["long_lecture"],
            should_use=True,
        )
