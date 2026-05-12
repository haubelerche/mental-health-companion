from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.schemas.contracts import AdvisorAdvice


class BaseAdvisor(ABC):
    advisor_id: str

    @abstractmethod
    def run(self, *, user_message: str, context_summary: str = "") -> AdvisorAdvice:
        raise NotImplementedError

