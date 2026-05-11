# Phase 2 — Data Sufficiency and Insight Pipeline

> **For agentic workers:** Use `superpowers:subagent-driven-development`. Steps use `- [ ]` syntax.

---

## 1. Files to Create

| Action | Path |
|---|---|
| Create | `backend/app/dashboard/__init__.py` (empty) |
| Create | `backend/app/dashboard/sufficiency.py` |
| Create | `backend/app/dashboard/service.py` |

---

## 2. Readiness Levels — `backend/app/dashboard/sufficiency.py`

Thresholds (backend-owned; frontend reads level string only):

| Level | Condition |
|---|---|
| `no_data` | 0 sessions AND 0 mood check-ins |
| `first_signals` | ≥1 session OR 1–2 check-ins |
| `early_insight` | ≥3 deep sessions OR (≥5 check-ins across ≥3 distinct days) |
| `weekly_trend` | calendar_days ≥7 AND active_days ≥4 AND total_sessions ≥2 |
| `stable_pattern` | calendar_days ≥14 AND active_days ≥6 AND total_sessions ≥5 |

Priority evaluation order (highest first): `stable_pattern → weekly_trend → early_insight → first_signals → no_data`.

**Deep session** — any condition met:
- `message_count >= 16`
- `anonymous_summary is not None` (session was summarized)
- `(last_message_at - started_at).total_seconds() / 60 >= 10`

**active_days** = distinct VN-local dates from `mood_checkins.logged_date` UNION
`conversations.started_at` converted to VN-local date.

- [ ] Implement `compute_data_sufficiency(db, *, user_id) -> DashboardDataSufficiency`

```python
def compute_data_sufficiency(db: Session, *, user_id: str) -> DashboardDataSufficiency:
    checkins = db.scalars(select(MoodCheckin)
        .where(MoodCheckin.user_id == user_id)).all()
    convs = db.scalars(select(Conversation)
        .where(Conversation.user_id == user_id,
               Conversation.deleted_at.is_(None))).all()

    checkin_dates = {r.logged_date for r in checkins}
    conv_dates = {_vn_date(c.started_at) for c in convs if c.started_at}
    all_dates = checkin_dates | conv_dates
    active_days = len(all_dates)

    deep = sum(1 for c in convs if _is_deep(c))
    checkin_distinct_days = len(checkin_dates)
    n_checkins = len(checkins)
    n_sessions = len(convs)
    calendar_days = (max(all_dates) - min(all_dates)).days + 1 if all_dates else 0

    level = _level(n_sessions, deep, n_checkins, checkin_distinct_days,
                   active_days, calendar_days)
    return DashboardDataSufficiency(
        readiness_level=level,
        active_days=active_days,
        mood_checkin_count=n_checkins,
        total_session_count=n_sessions,
        deep_session_count=deep,
        evidence_window_start=min(all_dates) if all_dates else None,
        evidence_window_end=max(all_dates) if all_dates else None,
        message=_message(level),
        next_data_needed=_hints(level, deep, n_checkins, checkin_distinct_days,
                                active_days, calendar_days, n_sessions),
    )
```

- [ ] Implement `_level(...)` with priority order above.
- [ ] Implement `_message(level)` — Vietnamese, non-clinical, warm copy:

```python
_MESSAGES = {
    "no_data":        "Serene chưa có dữ liệu. Hãy check-in hoặc trò chuyện để bắt đầu.",
    "first_signals":  "Serene đã có tín hiệu đầu tiên — đây là trạng thái hiện tại, chưa phải xu hướng.",
    "early_insight":  "Đã có đủ dữ liệu ban đầu. Serene chia sẻ một vài tín hiệu nhẹ.",
    "weekly_trend":   "Serene có thể nhận ra xu hướng trong 7 ngày qua.",
    "stable_pattern": "Dữ liệu khá ổn định. Serene nhận thấy một số xu hướng rõ hơn từ 14+ ngày qua.",
}
```

- [ ] Implement `_hints(...)` — returns 1-3 bullet strings describing what data is still needed.

---

## 3. Insight Cards — `backend/app/dashboard/service.py`

Source data (safe, derived from `UserProfile.profile` JSONB):

| Profile key | Safe insight type |
|---|---|
| `trigger_tags` | Repeated stress pattern |
| `session_summaries[-5:]` → `dominant_emotion` | Emotion pattern |
| `coping_history` | Recovery preference |

Rules:
- Maximum 2 insight cards returned to frontend.
- `confidence = "low"` when checkin_count < 5 or session_count < 3.
- `confidence = "medium"` when 5 ≤ checkin_count < 14 or 3 ≤ session_count < 8.
- `confidence = "high"` only at `stable_pattern`.
- `severity_band` is always `"neutral"` or `"watch"` — never implies diagnosis.
- `user_safe_summary` must use tentative language: "Serene nhận thấy...", "Dữ liệu gần đây cho thấy...", "Có thể bạn đang..."
- `suggested_action` is one small concrete step, never clinical advice.

- [ ] Implement `_build_insight_cards(profile_data, *, checkin_count, session_count, today) -> list[DashboardInsightCard]`

---

## 4. Wellness Dimension Cards

Source mapping (no PHQ9/GAD7):

| Dimension | Source | Status logic |
|---|---|---|
| `emotion` | Last 7 `mood_checkins`, avg score | avg ≥4 → steady; ≥3 → steady; <3 → needs_attention |
| `sleep` | `note` JSON blob `extra.sleep_hours` last 7 checkins | avg ≥7h → steady; ≥6h → needs_attention; else needs_attention |
| `mindfulness` | `stats.breathing_sessions` or `coping_history` breathing entries | 0 → limited_data; >0 → improving/steady |
| `connection` | `total_session_count` | 0 → limited_data; 1–4 → improving; ≥5 → steady |
| `body` | Effective coping count in `coping_history` | 0 → limited_data; else → improving/steady |
| `growth` | `stats.streak_days` + session count | 0 streak → limited_data; 1–6 → improving; ≥7 → steady |

- [ ] Implement `_build_wellness_dimensions(profile_data, *, checkin_rows, session_count) -> list[WellnessDimensionCard]`
- [ ] All 6 dimension cards always returned (status = "limited_data" when evidence_count == 0).
- [ ] Score is `int | None` — only set when evidence_count > 0.
- [ ] Never use `phq9_score`, `gad7_score`, `crisis_level` in dimension card computation.

---

## 5. Mood Series

- [ ] Implement `_build_mood_series(checkin_rows, days=14) -> list[dict]`
- [ ] If multiple check-ins on one day: average mood scores for that day.
- [ ] Output per day point: `{date, mood_score (1-5 avg), mood_score_pct (0-100), label, checkin_count}`.
- [ ] Only include days that have at least one check-in (skip empty days — frontend handles gaps).

---

## 6. Check-in History Builder

- [ ] Implement `build_checkin_history(checkin_rows, days=30) -> list[CheckinHistoryDay]`
- [ ] Group rows by `logged_date`, sorted newest-first.
- [ ] Parse `note` JSON blob to extract `note.note` text (strip internal extra fields).
- [ ] `completed = len(day_checkins) > 0`.
- [ ] `time_bucket` from row attribute (defaults "other" for pre-migration rows).

---

## 7. `build_reflect_summary` Orchestrator

- [ ] Implement `build_reflect_summary(db, *, user_id) -> DashboardReflectSummary`

```python
def build_reflect_summary(db, *, user_id):
    sufficiency = compute_data_sufficiency(db, user_id=user_id)
    checkins = fetch_all_checkins(db, user_id)
    profile_data = fetch_profile_data(db, user_id)

    insights = [] if sufficiency.readiness_level == "no_data" else \
        _build_insight_cards(profile_data, ...)
    dimensions = _build_wellness_dimensions(profile_data, checkin_rows=checkins, ...)
    mood_series = _build_mood_series(checkins, days=14)
    history_preview = build_checkin_history(checkins, days=7)
    radar_available = (
        sufficiency.readiness_level in ("weekly_trend", "stable_pattern")
        and sum(1 for d in dimensions if d.score is not None) >= 4
    )
    return DashboardReflectSummary(sufficiency=sufficiency, top_insights=insights,
        wellness_dimensions=dimensions, mood_series=mood_series,
        checkin_history_preview=history_preview, radar_available=radar_available)
```

---

## 8. Safety Checklist for This Phase

- [ ] `phq9_score`, `gad7_score`, `crisis_level` never referenced in `service.py` or `sufficiency.py`.
- [ ] No `AnalystNode` output passed directly to frontend — only aggregated safe fields.
- [ ] `user_safe_summary` strings do not contain: "bệnh", "rối loạn", "chẩn đoán", "triệu chứng bệnh", "nguy cơ mắc", "điểm tâm thần".
- [ ] `severity_band` never `"critical"` or any value implying clinical severity.
