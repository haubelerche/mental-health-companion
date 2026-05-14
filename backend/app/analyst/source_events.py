from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from app.analyst.types import AnalystSourceEvent, LocalPeriod, Sensitivity
from app.services.utils import VN_TZ


_PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:\+?\d[\s.-]?){8,}\b"),
]


def local_period_from_datetime(value: datetime | None, fallback: str | None = None) -> LocalPeriod:
    if fallback in ("morning", "afternoon", "evening"):
        return fallback  # type: ignore[return-value]
    if value is None:
        return "unknown"
    dt = value if value.tzinfo else value.replace(tzinfo=VN_TZ)
    hour = dt.astimezone(VN_TZ).hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 23:
        return "evening"
    return "unknown"


def local_date_from_datetime(value: datetime | None, fallback: date | None = None) -> date | None:
    if fallback is not None:
        return fallback
    if value is None:
        return None
    dt = value if value.tzinfo else value.replace(tzinfo=VN_TZ)
    return dt.astimezone(VN_TZ).date()


def redact_excerpt(value: str | None, *, limit: int = 180) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return None
    for pattern in _PII_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text[:limit]


def parse_checkin_note(note: str | None) -> tuple[str | None, dict[str, Any]]:
    if not note:
        return None, {}
    try:
        blob = json.loads(note)
        if isinstance(blob, dict):
            extra = blob.get("extra") if isinstance(blob.get("extra"), dict) else {}
            return redact_excerpt(blob.get("note")), extra
    except Exception:
        pass
    return redact_excerpt(note), {}


def make_event(
    *,
    user_id: str,
    source_table: str,
    source_id: str,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, Any] | None = None,
    sensitivity: Sensitivity = "medium",
    text_for_llm: str | None = None,
    numeric_features: dict[str, Any] | None = None,
    local_date: date | None = None,
    local_period: LocalPeriod | None = None,
) -> AnalystSourceEvent:
    return AnalystSourceEvent(
        event_id=f"{source_table}:{source_id}",
        user_id=user_id,
        source_table=source_table,
        source_id=source_id,
        event_type=event_type,
        occurred_at=occurred_at,
        local_date=local_date_from_datetime(occurred_at, local_date),
        local_period=local_period or local_period_from_datetime(occurred_at),
        payload=payload or {},
        sensitivity=sensitivity,
        text_for_llm=redact_excerpt(text_for_llm),
        numeric_features=numeric_features or {},
    )
