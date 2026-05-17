"""Analyst signal and insight hypothesis writers.

Implements the analyst_signals → insight_hypotheses pipeline described in
DATABASE_DESIGN_AUDIT_REPORT.md §7 Phase 4.

Called from session_summary.close_session_summary() after profile rollup.
SOS sessions are skipped — crisis sessions do not feed the insight pipeline.
"""

from __future__ import annotations

import logging
from datetime import timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import AnalystSignal, InsightHypothesis
from app.services.memory_enrichment import StructuredExtract
from app.services.utils import utc_now

_LANGGRAPH_ANALYST_MODEL_VERSION = "langgraph-inline-v1"

_ANALYST_MODEL_VERSION = "rule-based-v1"

logger = logging.getLogger(__name__)

_EMOTION_TO_HYPOTHESIS: dict[str, str] = {
    "lo_au": "anxiety_like_worry_loop",
    "buon_ba": "low_mood_trend",
    "cang_thang": "stress_pattern",
}

_TRIGGER_TO_HYPOTHESIS: dict[str, str] = {
    "co_don": "social_withdrawal",
    "suc_khoe": "sleep_disruption",
}

_COPING_HYPOTHESIS = "coping_success"


def _distress_score(extract: StructuredExtract) -> float:
    if extract.dominant_emotion in ("lo_au", "cang_thang"):
        return 0.6
    if extract.dominant_emotion == "buon_ba":
        return 0.5
    if extract.key_triggers:
        return 0.4
    return 0.2


def _hypothesis_type(extract: StructuredExtract) -> str:
    if extract.dominant_emotion and extract.dominant_emotion in _EMOTION_TO_HYPOTHESIS:
        return _EMOTION_TO_HYPOTHESIS[extract.dominant_emotion]
    for trigger in extract.key_triggers:
        if trigger in _TRIGGER_TO_HYPOTHESIS:
            return _TRIGGER_TO_HYPOTHESIS[trigger]
    if extract.coping_attempts:
        return _COPING_HYPOTHESIS
    return "other"


def _insight_title(hyp_type: str) -> str:
    _TITLES = {
        "stress_pattern": "Tín hiệu căng thẳng lặp lại",
        "sleep_disruption": "Giấc ngủ hoặc sức khỏe thể chất",
        "social_withdrawal": "Tín hiệu cô đơn hoặc thu mình",
        "low_mood_trend": "Xu hướng cảm xúc nặng nề",
        "anxiety_like_worry_loop": "Vòng lo âu lặp lại",
        "coping_success": "Điều có vẻ giúp bạn dễ chịu hơn",
        "engagement_pattern": "Mẫu tương tác trong app",
        "other": "Tín hiệu gần đây",
    }
    return _TITLES.get(hyp_type, "Tín hiệu gần đây")


def _insight_summary(hyp_type: str, extract: StructuredExtract) -> str:
    if hyp_type == "coping_success" and extract.coping_attempts:
        actions = ", ".join(extract.coping_attempts[:2])
        return (
            f"Serene nhận thấy bạn đã thử một số cách chăm sóc bản thân ({actions}). "
            "Đây chỉ là quan sát nhẹ để bạn nhìn lại — không phải kết luận."
        )
    if hyp_type == "anxiety_like_worry_loop":
        return (
            "Dữ liệu gần đây cho thấy bạn có thể đang trải qua những lo lắng lặp đi lặp lại. "
            "Serene chỉ ghi nhận tín hiệu ban đầu — bạn biết rõ mình nhất."
        )
    if hyp_type == "low_mood_trend":
        return (
            "Trong vài phiên gần đây, Serene nhận thấy không khí cảm xúc hơi nặng nề. "
            "Đây là quan sát nhẹ, không phải đánh giá."
        )
    if hyp_type == "stress_pattern":
        return (
            "Các phiên gần đây cho thấy dấu hiệu căng thẳng lặp lại. "
            "Serene chỉ ghi nhận tín hiệu — không đưa ra kết luận."
        )
    if hyp_type == "social_withdrawal":
        return (
            "Bạn có thể đang cảm thấy cô đơn hoặc muốn thu mình lại. "
            "Đây chỉ là quan sát nhẹ từ các phiên trò chuyện gần đây."
        )
    if hyp_type == "sleep_disruption":
        return (
            "Dữ liệu gần đây gợi ý có thể có ảnh hưởng đến giấc ngủ hoặc sức khỏe thể chất. "
            "Serene chỉ coi đây là tín hiệu ban đầu."
        )
    return (
        "Serene ghi nhận một tín hiệu nhẹ từ các phiên trò chuyện gần đây. "
        "Đây chỉ là quan sát, không phải kết luận."
    )


def record_analyst_signal(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    extract: StructuredExtract,
) -> str | None:
    """Write one AnalystSignal row derived from a StructuredExtract.

    Returns signal_id or None on failure.
    SOS sessions are skipped because crisis events belong to safety tables only.
    """
    if extract.sos_triggered:
        return None
    try:
        signal = AnalystSignal(
            user_id=user_id,
            session_id=session_id,
            emotional_theme=extract.dominant_emotion,
            suggested_focus=", ".join(extract.key_triggers[:3]) if extract.key_triggers else None,
            risk_indicators=list(extract.key_triggers),
            distress_score=_distress_score(extract),
            model_version=_ANALYST_MODEL_VERSION,
            source="analyst_node",
            display_allowed=False,
        )
        db.add(signal)
        db.flush()
        return str(signal.signal_id)
    except Exception as exc:
        logger.error("analyst_signal write failed user=%s session=%s: %s", user_id, session_id, exc)
        return None


def upsert_insight_hypothesis(
    db: Session,
    *,
    user_id: str,
    extract: StructuredExtract,
    signal_id: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """Create or update an InsightHypothesis from a StructuredExtract.

    Finds any existing active hypothesis of the same type for the user and
    increments evidence_count + updates window. Creates a new row if none.
    Returns insight_id or None on failure.
    SOS sessions are skipped.
    """
    if extract.sos_triggered:
        return None
    hyp_type = _hypothesis_type(extract)
    now = utc_now()
    evidence_window_end = now
    evidence_window_start = now - timedelta(days=30)

    internal: dict[str, Any] = {
        "signal_id": signal_id,
        "session_id": session_id,
        "triggers": extract.key_triggers,
        "coping": extract.coping_attempts,
        "emotion": extract.dominant_emotion,
        "model_version": _ANALYST_MODEL_VERSION,
    }

    try:
        existing = db.scalar(
            select(InsightHypothesis)
            .where(
                InsightHypothesis.user_id == user_id,
                InsightHypothesis.hypothesis_type == hyp_type,
                InsightHypothesis.status == "active",
            )
            .order_by(InsightHypothesis.updated_at.desc())
            .limit(1)
        )
        if existing is not None:
            existing.evidence_count = existing.evidence_count + 1
            existing.evidence_window_end = evidence_window_end
            existing.confidence = min(0.80, (existing.confidence or 0.30) + 0.05)
            existing.internal_rationale = {**(existing.internal_rationale or {}), **internal}
            existing.updated_at = now
            db.flush()
            return str(existing.insight_id)

        row = InsightHypothesis(
            user_id=user_id,
            hypothesis_type=hyp_type,
            title=_insight_title(hyp_type),
            user_safe_summary=_insight_summary(hyp_type, extract),
            internal_rationale=internal,
            evidence_window_start=evidence_window_start,
            evidence_window_end=evidence_window_end,
            evidence_count=1,
            confidence=0.30,
            severity_band="low",
            status="active",
            display_allowed=True,
            source="analyst_pipeline",
        )
        db.add(row)
        db.flush()
        return str(row.insight_id)
    except Exception as exc:
        logger.error(
            "insight_hypothesis upsert failed user=%s type=%s: %s", user_id, hyp_type, exc
        )
        return None


def record_analyst_bundle_signal(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    analyst_bundle: Any,
    distress_score: float = 0.0,
    sos_triggered: bool = False,
    evidence_refs: list[str] | None = None,
) -> str | None:
    """Persist an inline LangGraph AnalystBundle to analyst_signals.

    Called from the chat router immediately after a non-SOS turn.
    SOS turns are skipped — crisis data belongs in safety tables only.
    analyst_bundle must have .emotional_theme and .risk_indicators attributes.
    Returns signal_id or None on failure.
    """
    if sos_triggered or analyst_bundle is None:
        return None
    emotional_theme = getattr(analyst_bundle, "emotional_theme", None) or "unknown"
    if emotional_theme in ("cold_start_screen", "unknown", "unclear"):
        return None
    risk_indicators = list(getattr(analyst_bundle, "risk_indicators", []) or [])
    suggested_focus = getattr(analyst_bundle, "suggested_focus", None)
    try:
        signal = AnalystSignal(
            user_id=user_id,
            session_id=session_id,
            emotional_theme=emotional_theme,
            suggested_focus=suggested_focus,
            risk_indicators=risk_indicators,
            evidence_refs=list(evidence_refs or [])[:100],
            distress_score=max(0.0, min(1.0, float(distress_score))),
            model_version=_LANGGRAPH_ANALYST_MODEL_VERSION,
            source="friend_turn",
            display_allowed=False,
        )
        db.add(signal)
        db.flush()
        return str(signal.signal_id)
    except Exception as exc:
        logger.error(
            "analyst_bundle signal write failed user=%s session=%s: %s",
            user_id,
            session_id,
            exc,
        )
        return None
