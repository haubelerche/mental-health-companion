"""Synchronous writers for safety audit tables.

CrisisLog and SessionRiskSnapshot must be written synchronously before the
turn response is returned so safety audit trail is never missing.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.db.models import CrisisLog, SessionRiskSnapshot
from app.services.utils import make_id, get_now

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
) -> str | None:
    """Persist one risk inference audit row into crisis_logs. Returns log_id or None on failure.

    Must be called inside an open transaction; caller is responsible for
    committing (or letting the caller's flush handle it).
    """
    try:
        score_value = float(score) if score is not None else 0.0
        if score_value >= 0.85:
            severity = "imminent"
        elif score_value >= 0.65:
            severity = "high"
        elif score_value >= 0.35:
            severity = "moderate"
        else:
            severity = "low"
        details = detail or {}
        row = CrisisLog(
            log_id=make_id("cl"),
            user_id=user_id,
            session_id=session_id,
            severity_level=severity,
            context_summary=f"[risk:{inferred_signal}] score={score_value:.3f} model={_RISK_MODEL_VERSION} detail={details}",
            reviewed=False,
            triggered_at=get_now().replace(tzinfo=None),
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
