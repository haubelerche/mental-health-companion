"""Synchronous writers for safety audit tables.

RiskInferenceLog and SessionRiskSnapshot must be written synchronously
before the turn response is returned so the safety audit trail is never
missing when an SOS or elevated-risk state is detected.

These tables are backend-only. Frontend must never read them directly.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.db.models import RiskInferenceLog, SessionRiskSnapshot

_RISK_MODEL_VERSION = "rule-based-v1"

logger = logging.getLogger(__name__)


def record_risk_inference(
    db: Session,
    *,
    user_id: str,
    session_id: str | None,
    inferred_signal: str,
    score: float | None = None,
    detail: dict[str, Any] | None = None,
) -> int | None:
    """Persist one risk inference event. Returns log_id or None on failure.

    Must be called inside an open transaction; caller is responsible for
    committing (or letting the caller's flush handle it).
    """
    try:
        row = RiskInferenceLog(
            user_id=user_id,
            session_id=session_id,
            inferred_signal=inferred_signal,
            model_version=_RISK_MODEL_VERSION,
            score=score,
            detail=detail or {},
        )
        db.add(row)
        db.flush()
        return row.log_id
    except Exception as exc:
        logger.error(
            "risk_inference write failed user=%s session=%s signal=%s: %s",
            user_id,
            session_id,
            inferred_signal,
            exc,
        )
        return None


def record_session_risk_snapshot(
    db: Session,
    *,
    session_id: str,
    user_id: str,
    risk_score: float,
    intent_severity: float = 0.0,
    intent_immediacy: float = 0.0,
    crisis_mode: bool = False,
    escalation_flag: bool = False,
    components: dict[str, Any] | None = None,
    source: str = "safety_agent",
) -> int | None:
    """Persist a session-level risk snapshot. Returns snapshot_id or None on failure.

    source must be one of: supervisor, sos_override, batch_recalc, system, safety_agent.
    """
    _VALID_SOURCES = {"supervisor", "sos_override", "batch_recalc", "system", "safety_agent"}
    if source not in _VALID_SOURCES:
        source = "safety_agent"
    try:
        row = SessionRiskSnapshot(
            session_id=session_id,
            user_id=user_id,
            risk_score=max(0.0, min(1.0, risk_score)),
            intent_severity=max(0.0, min(1.0, intent_severity)),
            intent_immediacy=max(0.0, min(1.0, intent_immediacy)),
            crisis_mode=crisis_mode,
            escalation_flag=escalation_flag,
            components=components or {},
            source=source,
        )
        db.add(row)
        db.flush()
        return row.snapshot_id
    except Exception as exc:
        logger.error(
            "session_risk_snapshot write failed session=%s user=%s: %s",
            session_id,
            user_id,
            exc,
        )
        return None
