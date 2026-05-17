# Phase 1 — Backend Contracts and Database

> **For agentic workers:** Use `superpowers:subagent-driven-development`. Steps use `- [ ]` syntax.

---

## 1. Files to Create / Modify

| Action | Path |
|---|---|
| Create | `backend/app/dashboard/__init__.py` |
| Create | `backend/app/dashboard/types.py` |
| Create | `backend/app/dashboard/sufficiency.py` |
| Create | `backend/app/dashboard/service.py` |
| Modify | `backend/app/api/v1/routers/dashboard.py` (add 3 endpoints) |
| Create | `backend/alembic/versions/0011_mood_checkin_time_bucket.py` |
| Modify | `backend/app/services/db/models.py` (MoodCheckin) |
| Modify | `backend/app/api/v1/routers/checkin.py` (time_bucket logic) |

---

## 2. DB Migration — `0011_mood_checkin_time_bucket.py`

- [ ] Create `backend/alembic/versions/0011_mood_checkin_time_bucket.py`

```python
"""Add time_bucket to mood_checkins for intraday multi-checkin support.

Revision ID: 0011_mood_checkin_time_bucket
Revises: 0010_oauth_identities
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_mood_checkin_time_bucket"
down_revision = "0010_oauth_identities"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("mood_checkins")]
    if "time_bucket" not in cols:
        op.add_column("mood_checkins",
            sa.Column("time_bucket", sa.String(20), nullable=False,
                      server_default="other"))
    # Drop old unique constraint, add bucket-scoped one
    try:
        op.drop_constraint("uq_mood_per_day", "mood_checkins", type_="unique")
    except Exception:
        pass
    existing = [u["name"] for u in inspector.get_unique_constraints("mood_checkins")]
    if "uq_mood_checkin_bucket" not in existing:
        op.create_unique_constraint(
            "uq_mood_checkin_bucket",
            "mood_checkins",
            ["user_id", "logged_date", "time_bucket"],
        )

def downgrade() -> None:
    op.drop_constraint("uq_mood_checkin_bucket", "mood_checkins", type_="unique")
    op.drop_column("mood_checkins", "time_bucket")
    op.create_unique_constraint("uq_mood_per_day", "mood_checkins",
                                ["user_id", "logged_date"])
```

- [ ] Run migration locally: `cd backend && alembic upgrade head`

---

## 3. Update `MoodCheckin` SQLAlchemy Model

- [ ] In `backend/app/services/db/models.py`, replace `MoodCheckin.__table_args__`:

```python
class MoodCheckin(Base):
    __tablename__ = "mood_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "logged_date", "time_bucket",
                         name="uq_mood_checkin_bucket"),
    )
    checkin_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(10))
    emotions: Mapped[list[Any] | None] = mapped_column(JSON)
    triggers: Mapped[list[Any] | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    time_bucket: Mapped[str] = mapped_column(String(20), nullable=False,
                                              default="other", server_default="other")
```

---

## 4. Update `checkin.py` — Multi-bucket Check-in Logic

- [ ] Add `_compute_time_bucket()` helper:

```python
from zoneinfo import ZoneInfo
_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def _compute_time_bucket() -> str:
    hour = utc_now().astimezone(_VN_TZ).hour
    if 6 <= hour < 12:   return "morning"
    if 12 <= hour < 18:  return "afternoon"
    if 18 <= hour < 23:  return "evening"
    return "other"
```

- [ ] In `checkin_quick`, compute `time_bucket = _compute_time_bucket()` before query.
- [ ] Change `existing` query to filter on `MoodCheckin.time_bucket == time_bucket`.
- [ ] Reward idempotency key stays per-day: `f"mood_checkin:{user_id}:{logged_date.isoformat()}"` — unchanged.
- [ ] `update_mood_streak` call unchanged — streak already idempotent per date.

---

## 5. Pydantic Types — `backend/app/dashboard/types.py`

- [ ] Create file with these models (no internal clinical fields):

```python
from __future__ import annotations
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel

DashboardReadinessLevel = Literal[
    "no_data", "first_signals", "early_insight", "weekly_trend", "stable_pattern"]

class DashboardDataSufficiency(BaseModel):
    readiness_level: DashboardReadinessLevel
    active_days: int
    mood_checkin_count: int
    total_session_count: int
    deep_session_count: int
    evidence_window_start: date | None
    evidence_window_end: date | None
    message: str
    next_data_needed: list[str]

class DashboardInsightCard(BaseModel):
    insight_id: str
    title: str
    user_safe_summary: str
    evidence_count: int
    evidence_sources: list[str]
    confidence: Literal["low", "medium", "high"]
    severity_band: Literal["neutral", "watch", "supportive_attention"]
    suggested_action: str | None
    evidence_window_start: date | None
    evidence_window_end: date | None
    updated_at: datetime

class WellnessDimensionCard(BaseModel):
    dimension: Literal["emotion","sleep","mindfulness","connection","body","growth"]
    label: str
    status: Literal["unknown","limited_data","steady","needs_attention","improving"]
    score: int | None
    explanation: str
    evidence_count: int
    suggested_action: str | None

class CheckinHistoryItem(BaseModel):
    checkin_id: str
    logged_at: datetime
    date: date
    time_bucket: Literal["morning","afternoon","evening","other"]
    mood_label: str | None
    mood_score: int | None
    emotions: list[str]
    triggers: list[str]
    note: str | None

class CheckinHistoryDay(BaseModel):
    date: date
    completed: bool
    checkins: list[CheckinHistoryItem]

class DashboardReflectSummary(BaseModel):
    sufficiency: DashboardDataSufficiency
    top_insights: list[DashboardInsightCard]
    wellness_dimensions: list[WellnessDimensionCard]
    mood_series: list[dict]
    checkin_history_preview: list[CheckinHistoryDay]
    radar_available: bool
```

---

## 6. New Endpoints in `backend/app/api/v1/routers/dashboard.py`

- [ ] Import `build_reflect_summary`, `build_checkin_history` from `app.dashboard.service`
- [ ] Add to existing router (already mounted at `/dashboard`):

```python
@router.get("/reflect-summary")
def reflect_summary(current_user=Depends(...), db=Depends(get_db)):
    summary = build_reflect_summary(db, user_id=current_user.user_id)
    return ok(summary.model_dump(mode="json"))

@router.get("/checkin-history")
def checkin_history(
    range_: str = Query(default="30d", alias="range"),
    current_user=Depends(...), db=Depends(get_db),
):
    days = {"all": 365, "90d": 90}.get(range_, 30)
    rows = db.scalars(select(MoodCheckin)
        .where(MoodCheckin.user_id == current_user.user_id)
        .order_by(MoodCheckin.logged_date.asc(), MoodCheckin.logged_at.asc())).all()
    history = build_checkin_history(list(rows), days=days)
    return ok({"days": days, "range": range_,
               "history": [d.model_dump(mode="json") for d in history]})

@router.get("/safe-insights")
def safe_insights(current_user=Depends(...), db=Depends(get_db)):
    from app.dashboard.service import build_safe_insights
    return ok(build_safe_insights(db, user_id=current_user.user_id))
```

---

## 7. Safety Boundary

These fields must **never** appear in any response from the three new endpoints:

```
clinical_note_internal · risk_indicators · phq9_score · gad7_score
crisis_level · crisis_logs · admin_audit_log · internal_rationale
distress_score · sos_triggered (raw) · analyst raw bundle
```

The existing `/reflect/mental-health-summary` endpoint that exposes `clinical_snapshot`
(PHQ9/GAD7) should be marked `@deprecated` in its docstring. Do not delete it yet
(backward compatibility). The new frontend code must **not** consume it.
