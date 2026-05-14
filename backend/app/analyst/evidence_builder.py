from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.analyst.types import AnalystSourceEvent
from app.services.db.models import InsightEvidence
from app.services.observability import record_event


def create_evidence_rows(
    db: Session,
    *,
    insight_id: str,
    user_id: str,
    evidence_events: list[AnalystSourceEvent],
    evidence_type: str,
    numeric_value: dict[str, Any] | None = None,
    limit: int = 6,
) -> list[str]:
    ids: list[str] = []
    for event in evidence_events[:limit]:
        row = InsightEvidence(
            evidence_id=str(uuid4()),
            insight_id=insight_id,
            user_id=user_id,
            source_table=event.source_table,
            source_id=event.source_id,
            evidence_type=evidence_type,
            occurred_at=event.occurred_at if isinstance(event.occurred_at, datetime) else datetime.utcnow(),
            user_safe_excerpt=event.text_for_llm if event.sensitivity in {"low", "medium"} else None,
            numeric_value=numeric_value,
            weight=1.0,
            sensitivity=event.sensitivity,
            display_allowed=event.sensitivity in {"low", "medium"},
        )
        db.add(row)
        ids.append(row.evidence_id)
    if ids:
        record_event("analyst.evidence.created", metadata={"evidence_count": len(ids), "evidence_type": evidence_type})
    return ids
