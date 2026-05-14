from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyst.context_pack_builder import build_context_pack
from app.analyst.feature_builder import FEATURE_VERSION, build_features
from app.analyst.insight_aggregator import aggregate_insights, write_signal
from app.analyst.llm_analyzer import LLM_MODEL_VERSION, analyze_context
from app.analyst.repositories import collect_source_events
from app.analyst.types import AnalystRunRequest, AnalystRunResult
from app.services.db.models import AnalystFeatureSnapshot, AnalystRun
from app.services.observability import record_event, record_metric
from app.services.utils import get_now


def default_window_for_run(run_type: str, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    end = now or get_now()
    if run_type == "daily":
        return end - timedelta(days=1), end
    if run_type == "rolling_3d":
        return end - timedelta(days=3), end
    if run_type == "weekly":
        return end - timedelta(days=7), end
    return end - timedelta(days=14), end


def idempotency_key_for(request: AnalystRunRequest) -> str:
    return (
        f"analyst_run:{request.user_id}:{request.run_type}:"
        f"{request.window_start.isoformat()}:{request.window_end.isoformat()}:{request.data_cutoff_at.isoformat()}"
    )


def run_analyst_pipeline(db: Session, request: AnalystRunRequest) -> AnalystRunResult:
    key = idempotency_key_for(request)
    existing = db.scalar(select(AnalystRun).where(AnalystRun.idempotency_key == key))
    if existing and not request.force:
        return AnalystRunResult(
            run_id=existing.run_id,
            status=existing.status,  # type: ignore[arg-type]
            source_counts={str(k): int(v) for k, v in dict(existing.source_counts or {}).items()},
            missing_sources=[str(x) for x in list(existing.missing_sources or [])],
            skipped_reason="idempotent_existing_run",
        )

    run = existing or AnalystRun(
        run_id=str(uuid4()),
        user_id=request.user_id,
        run_type=request.run_type,
        status="running",
        window_start=request.window_start,
        window_end=request.window_end,
        data_cutoff_at=request.data_cutoff_at,
        idempotency_key=key,
        feature_version=FEATURE_VERSION,
    )
    if existing is None:
        db.add(run)
    else:
        run.status = "running"
        run.error_code = None
    db.flush()

    record_event("analyst.run.started", metadata={"run_id": run.run_id, "run_type": request.run_type})
    try:
        events, source_counts, missing_sources = collect_source_events(
            db,
            user_id=request.user_id,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        run.source_counts = source_counts
        run.missing_sources = missing_sources
        run.input_summary = {"event_count": len(events), "source_tables": sorted(source_counts.keys())}
        if _insufficient(request.run_type, events, source_counts):
            features = build_features(events, missing_sources=missing_sources).model_dump(mode="json")
            snapshot = _write_snapshot(db, run=run, request=request, features=features, source_counts=source_counts)
            run.status = "skipped_insufficient_data"
            run.completed_at = get_now()
            db.flush()
            record_event("analyst.run.skipped_insufficient_data", metadata={"run_id": run.run_id, "run_type": request.run_type})
            return AnalystRunResult(
                run_id=run.run_id,
                status="skipped_insufficient_data",
                snapshot_id=snapshot.snapshot_id,
                source_counts=source_counts,
                missing_sources=missing_sources,
                skipped_reason="insufficient_data",
            )

        features = build_features(events, missing_sources=missing_sources).model_dump(mode="json")
        features["feature_version"] = FEATURE_VERSION
        features["source_counts"] = source_counts
        snapshot = _write_snapshot(db, run=run, request=request, features=features, source_counts=source_counts)
        context = build_context_pack(db, request=request, features=features, events=events)
        llm_output = analyze_context(context)
        write_signal(db, run_id=run.run_id, request=request, llm_output=llm_output, model_version=LLM_MODEL_VERSION)
        insight_ids = aggregate_insights(
            db,
            run_id=run.run_id,
            request=request,
            llm_output=llm_output,
            events=events,
            features=features,
        )
        run.status = "completed"
        run.model_version = LLM_MODEL_VERSION
        run.completed_at = get_now()
        db.flush()
        record_event("analyst.run.completed", metadata={"run_id": run.run_id, "run_type": request.run_type, "insight_count": len(insight_ids)})
        record_metric("analyst_run_completed_total", 1, labels={"status": "completed", "worker_type": "analyst_run"})
        return AnalystRunResult(
            run_id=run.run_id,
            status="completed",
            snapshot_id=snapshot.snapshot_id,
            source_counts=source_counts,
            missing_sources=missing_sources,
            created_insight_ids=insight_ids,
        )
    except Exception as exc:
        run.status = "failed"
        run.error_code = type(exc).__name__
        run.completed_at = get_now()
        db.flush()
        record_event("analyst.run.failed", metadata={"run_id": run.run_id, "run_type": request.run_type, "error_code": type(exc).__name__})
        raise


def _write_snapshot(
    db: Session,
    *,
    run: AnalystRun,
    request: AnalystRunRequest,
    features: dict,
    source_counts: dict[str, int],
) -> AnalystFeatureSnapshot:
    snapshot = AnalystFeatureSnapshot(
        snapshot_id=str(uuid4()),
        run_id=run.run_id,
        user_id=request.user_id,
        window_start=request.window_start,
        window_end=request.window_end,
        data_cutoff_at=request.data_cutoff_at,
        window_type=request.run_type,
        feature_version=FEATURE_VERSION,
        features=features,
        source_counts=source_counts,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _insufficient(run_type: str, events: list, source_counts: dict[str, int]) -> bool:
    total = len(events)
    mood_count = int(source_counts.get("mood_checkins") or 0)
    meal_count = int(source_counts.get("nutrition_meal_checkins") or 0)
    if run_type == "daily":
        return mood_count < 1 and total < 2
    if run_type == "rolling_3d":
        return total < 5
    if run_type == "weekly":
        return total < 5 or mood_count < 3
    if run_type == "post_screening":
        return int(source_counts.get("clinical_profiles") or 0) < 1
    if run_type == "on_demand_dashboard":
        return total < 2 and meal_count < 1
    return total < 2
