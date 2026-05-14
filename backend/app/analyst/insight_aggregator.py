from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyst.evidence_builder import create_evidence_rows
from app.analyst.privacy_filter import filter_user_safe_insight
from app.analyst.types import AnalystLLMOutput, AnalystRunRequest, AnalystSourceEvent
from app.services.db.models import AnalystSignal, InsightHypothesis
from app.services.observability import record_event
from app.services.utils import get_now


def write_signal(
    db: Session,
    *,
    run_id: str,
    request: AnalystRunRequest,
    llm_output: AnalystLLMOutput,
    model_version: str,
) -> str:
    signal = AnalystSignal(
        run_id=run_id,
        user_id=request.user_id,
        emotional_theme=", ".join(llm_output.emotional_themes[:3]) or None,
        suggested_focus=", ".join(llm_output.recurring_stressors[:3]) or None,
        clinical_note_internal=None,
        risk_indicators=[],
        distress_score=None,
        confidence=llm_output.confidence,
        model_version=model_version,
        graph_context_used=False,
        source="batch_rollup",
        display_allowed=False,
        raw_structured_output=llm_output.model_dump(mode="json"),
    )
    db.add(signal)
    db.flush()
    return str(signal.signal_id)


def aggregate_insights(
    db: Session,
    *,
    run_id: str,
    request: AnalystRunRequest,
    llm_output: AnalystLLMOutput,
    events: list[AnalystSourceEvent],
    features: dict[str, Any],
) -> list[str]:
    _expire_old_insights(db, user_id=request.user_id)
    created_or_updated: list[str] = []
    candidates = list(llm_output.user_safe_insight_candidates or [])
    if not candidates and features.get("data_quality", {}).get("is_provisional"):
        candidates.append(
            {
                "hypothesis_type": "data_quality_notice",
                "title": "Dữ liệu còn đang được ghép lại",
                "user_safe_summary": "Dữ liệu hiện tại còn ít, nên Serene chỉ xem đây là quan sát tạm thời.",
                "evidence_count": max(2, int(features.get("data_quality", {}).get("total_events") or 0)),
                "severity_band": "informational",
            }
        )

    for candidate in candidates:
        hyp_type = str(candidate.get("hypothesis_type") or "data_quality_notice")
        title = str(candidate.get("title") or "Tín hiệu gần đây")[:240]
        summary = str(candidate.get("user_safe_summary") or "").strip()
        evidence_count = int(candidate.get("evidence_count") or 0)
        severity = str(candidate.get("severity_band") or _severity_for_type(hyp_type))
        decision = filter_user_safe_insight(
            summary=summary,
            confidence=llm_output.confidence,
            evidence_count=evidence_count,
            sensitivity="medium",
        )
        if not decision.allowed:
            record_event("analyst.privacy.blocked", metadata={"hypothesis_type": hyp_type, "reason_code": decision.reason})
            _write_blocked_candidate(
                db,
                run_id=run_id,
                request=request,
                hyp_type=hyp_type,
                title=title,
                summary=summary or "Insight bị chặn bởi bộ lọc an toàn.",
                evidence_count=max(0, evidence_count),
                reason=decision.reason,
            )
            continue

        existing = db.scalar(
            select(InsightHypothesis)
            .where(
                InsightHypothesis.user_id == request.user_id,
                InsightHypothesis.hypothesis_type == hyp_type,
                InsightHypothesis.status == "active",
            )
            .order_by(InsightHypothesis.updated_at.desc())
            .limit(1)
        )
        if existing is not None and _overlaps(existing, request):
            existing.status = "superseded"
            existing.updated_at = get_now()
            record_event("analyst.insight.superseded", metadata={"hypothesis_type": hyp_type})

        row = InsightHypothesis(
            insight_id=str(uuid4()),
            run_id=run_id,
            user_id=request.user_id,
            hypothesis_type=hyp_type,
            title=title,
            user_safe_summary=decision.rewritten_summary or summary,
            internal_rationale={
                "run_id": run_id,
                "candidate": {k: v for k, v in candidate.items() if k != "user_safe_summary"},
                "feature_version": features.get("feature_version"),
            },
            evidence_window_start=request.window_start,
            evidence_window_end=request.window_end,
            evidence_count=evidence_count,
            confidence=min(0.85, max(0.0, llm_output.confidence)),
            severity_band=severity if severity in {"informational", "low", "medium", "high"} else "low",
            status="active",
            display_allowed=True,
            source="analyst_pipeline",
        )
        db.add(row)
        db.flush()
        matched_events = _events_for_hypothesis(hyp_type, events)
        create_evidence_rows(
            db,
            insight_id=row.insight_id,
            user_id=request.user_id,
            evidence_events=matched_events,
            evidence_type=hyp_type,
            numeric_value={"source_counts": features.get("source_counts", {})},
        )
        created_or_updated.append(str(row.insight_id))
        record_event("analyst.insight.created", metadata={"hypothesis_type": hyp_type})
    return created_or_updated


def _write_blocked_candidate(
    db: Session,
    *,
    run_id: str,
    request: AnalystRunRequest,
    hyp_type: str,
    title: str,
    summary: str,
    evidence_count: int,
    reason: str | None,
) -> None:
    db.add(
        InsightHypothesis(
            insight_id=str(uuid4()),
            run_id=run_id,
            user_id=request.user_id,
            hypothesis_type=hyp_type if hyp_type else "data_quality_notice",
            title=title,
            user_safe_summary=summary[:1000],
            internal_rationale={"blocked_reason": reason, "run_id": run_id},
            evidence_window_start=request.window_start,
            evidence_window_end=request.window_end,
            evidence_count=evidence_count,
            confidence=0.0,
            severity_band="informational",
            status="blocked_by_safety",
            display_allowed=False,
            source="analyst_pipeline",
        )
    )


def _severity_for_type(hyp_type: str) -> str:
    if hyp_type in {"data_quality_notice", "engagement_pattern"}:
        return "informational"
    if hyp_type in {"nutrition_mood_link", "sleep_energy_link"}:
        return "medium"
    return "low"


def _overlaps(row: InsightHypothesis, request: AnalystRunRequest) -> bool:
    start = row.evidence_window_start
    end = row.evidence_window_end
    if not start or not end:
        return True
    return start <= request.window_end and end >= request.window_start


def _expire_old_insights(db: Session, *, user_id: str, ttl_days: int = 45) -> None:
    cutoff = get_now() - timedelta(days=ttl_days)
    rows = db.scalars(
        select(InsightHypothesis).where(
            InsightHypothesis.user_id == user_id,
            InsightHypothesis.status == "active",
            InsightHypothesis.updated_at < cutoff,
        )
    ).all()
    for row in rows:
        row.status = "expired"
        row.updated_at = get_now()


def _events_for_hypothesis(hyp_type: str, events: list[AnalystSourceEvent]) -> list[AnalystSourceEvent]:
    if hyp_type in {"mood_trend", "trigger_pattern"}:
        return [e for e in events if e.event_type == "mood_checkin"]
    if hyp_type == "nutrition_mood_link":
        return [e for e in events if e.event_type in {"meal_checkin", "mood_checkin"}]
    if hyp_type in {"coping_preference", "support_style_preference"}:
        return [e for e in events if e.event_type in {"memory", "chat_message"}]
    if hyp_type == "screening_context_notice":
        return [e for e in events if e.event_type == "screening_result"]
    return [e for e in events if e.sensitivity in {"low", "medium"}]
