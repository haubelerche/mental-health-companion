from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.analyst_agent import AnalystAgent
from app.services.schemas.contracts import AnalystBundle


class AnalystPipeline:
    def __init__(self) -> None:
        self._agent = AnalystAgent()

    def run(self, *, user_id: str, normalized_events: list[dict]) -> dict:
        bundle = self._agent.generate_bundle(user_id=user_id, events=normalized_events)
        return bundle.model_dump(mode="json")

    def run_from_db(self, *, db: Session, user_id: str) -> AnalystBundle:
        return self._agent.generate_bundle_from_db(db=db, user_id=user_id)

