from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyst.jobs import build_refresh_job
from app.analyst.service import default_window_for_run, run_analyst_pipeline
from app.analyst.types import AnalystRunRequest
from app.api.deps import ensure_policy_acknowledged
from app.core.responses import ok
from app.services.async_outbox import enqueue_worker_job
from app.services.db.models import AnalystRun, InsightEvidence, InsightHypothesis, User
from app.services.db.session import get_db
from app.services.observability import record_event
from app.services.utils import get_now

router = APIRouter(prefix="/analyst", tags=["analyst"])


class RefreshRequest(BaseModel):
    run_type: Literal["turn", "daily", "rolling_3d", "weekly", "on_demand_dashboard", "post_screening"] = "on_demand_dashboard"
    run_now: bool = False
    force: bool = False


@router.get("/dashboard/insights")
def analyst_dashboard_insights(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(InsightHypothesis)
        .where(
            InsightHypothesis.user_id == current_user.user_id,
            InsightHypothesis.status == "active",
            InsightHypothesis.display_allowed.is_(True),
        )
        .order_by(InsightHypothesis.updated_at.desc())
        .limit(20)
    ).all()
    return ok(
        {
            "insights": [
                {
                    "insight_id": row.insight_id,
                    "hypothesis_type": row.hypothesis_type,
                    "title": row.title,
                    "user_safe_summary": row.user_safe_summary,
                    "confidence": row.confidence,
                    "severity_band": row.severity_band,
                    "evidence_count": row.evidence_count,
                    "evidence_window_start": row.evidence_window_start.isoformat() if row.evidence_window_start else None,
                    "evidence_window_end": row.evidence_window_end.isoformat() if row.evidence_window_end else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]
        }
    )


@router.get("/dashboard/insights/{insight_id}/evidence")
def analyst_dashboard_insight_evidence(
    insight_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    insight = db.scalar(
        select(InsightHypothesis).where(
            InsightHypothesis.insight_id == insight_id,
            InsightHypothesis.user_id == current_user.user_id,
            InsightHypothesis.display_allowed.is_(True),
        )
    )
    if insight is None:
        raise HTTPException(status_code=404, detail="Insight not found")
    rows = db.scalars(
        select(InsightEvidence)
        .where(
            InsightEvidence.insight_id == insight_id,
            InsightEvidence.user_id == current_user.user_id,
            InsightEvidence.display_allowed.is_(True),
        )
        .order_by(InsightEvidence.occurred_at.desc())
        .limit(20)
    ).all()
    return ok(
        {
            "insight_id": insight_id,
            "evidence": [
                {
                    "evidence_id": row.evidence_id,
                    "source_table": row.source_table,
                    "source_id": row.source_id,
                    "evidence_type": row.evidence_type,
                    "occurred_at": row.occurred_at.isoformat(),
                    "user_safe_excerpt": row.user_safe_excerpt,
                    "numeric_value": row.numeric_value,
                    "weight": row.weight,
                }
                for row in rows
            ],
        }
    )


@router.post("/runs/refresh")
def refresh_analyst_run(
    payload: RefreshRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    if payload.run_now and os.getenv("SERENE_BACKEND_TESTING") == "1":
        start, end = default_window_for_run(payload.run_type, now=get_now())
        result = run_analyst_pipeline(
            db,
            AnalystRunRequest(
                user_id=current_user.user_id,
                run_type=payload.run_type,
                window_start=start,
                window_end=end,
                data_cutoff_at=end,
                force=payload.force,
            ),
        )
        db.commit()
        return ok(result.model_dump(mode="json"))

    job = build_refresh_job(user_id=current_user.user_id, run_type=payload.run_type)
    outbox_id = enqueue_worker_job(db, job)
    db.commit()
    record_event("analyst.run.queued", metadata={"run_type": payload.run_type, "outbox_id": outbox_id})
    return ok({"status": "queued", "outbox_id": outbox_id, "run_type": payload.run_type})


@router.get("/runs/{run_id}")
def get_analyst_run(
    run_id: str,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(AnalystRun).where(AnalystRun.run_id == run_id, AnalystRun.user_id == current_user.user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return ok(
        {
            "run_id": row.run_id,
            "run_type": row.run_type,
            "status": row.status,
            "window_start": row.window_start.isoformat(),
            "window_end": row.window_end.isoformat(),
            "data_cutoff_at": row.data_cutoff_at.isoformat(),
            "source_counts": row.source_counts,
            "missing_sources": row.missing_sources,
            "model_version": row.model_version,
            "feature_version": row.feature_version,
            "error_code": row.error_code,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
    )
