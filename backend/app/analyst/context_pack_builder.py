from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyst.types import AnalystLLMInput, AnalystRunRequest, AnalystSourceEvent
from app.services.db.models import InsightHypothesis


def build_context_pack(
    db: Session,
    *,
    request: AnalystRunRequest,
    features: dict,
    events: list[AnalystSourceEvent],
) -> AnalystLLMInput:
    text_evidence = [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source_table": event.source_table,
            "occurred_at": event.occurred_at.isoformat(),
            "excerpt": event.text_for_llm,
        }
        for event in events
        if event.text_for_llm and event.sensitivity in {"low", "medium"}
    ][:12]
    existing = db.scalars(
        select(InsightHypothesis)
        .where(InsightHypothesis.user_id == request.user_id, InsightHypothesis.status == "active")
        .order_by(InsightHypothesis.updated_at.desc())
        .limit(8)
    ).all()
    return AnalystLLMInput(
        user_id=request.user_id,
        run_type=request.run_type,
        window_start=request.window_start,
        window_end=request.window_end,
        data_cutoff_at=request.data_cutoff_at,
        compact_features=features,
        redacted_text_evidence=text_evidence,
        existing_insights_summary=[
            {"insight_id": row.insight_id, "hypothesis_type": row.hypothesis_type, "title": row.title}
            for row in existing
        ],
    )
