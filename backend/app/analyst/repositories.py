from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.analyst.source_events import make_event, parse_checkin_note, redact_excerpt
from app.analyst.types import AnalystSourceEvent
from app.services.db.models import (
    ClinicalProfile,
    Conversation,
    HeartRewardEvent,
    MemoryCard,
    Message,
    MoodCheckin,
    NutritionMealCheckin,
    PersonaUnlockState,
    Resource,
    SessionRiskSnapshot,
    SessionSummaryArchive,
)
from app.services.mem0_repository import list_all_user_memories
from app.services.utils import get_now


class Mem0MemoryRepository:
    source_name = "mem0_memories"

    def list_events(self, db: Session, *, user_id: str) -> tuple[list[AnalystSourceEvent], list[str]]:
        try:
            rows = list_all_user_memories(db, user_id=user_id, batch_size=200, max_rows=500)
        except Exception:
            return [], [self.source_name]
        events: list[AnalystSourceEvent] = []
        for row in rows:
            occurred_at = _parse_dt(row.created_at) or get_now()
            events.append(
                make_event(
                    user_id=user_id,
                    source_table=self.source_name,
                    source_id=row.id,
                    event_type="memory",
                    occurred_at=occurred_at,
                    payload={"source": row.source, "metadata_keys": sorted((row.metadata or {}).keys())[:12]},
                    sensitivity="medium",
                    text_for_llm=row.content,
                )
            )
        return events, []


class ConversationMemoryRepository:
    source_name = "conversation_memories"

    def list_events(self, db: Session, *, user_id: str) -> tuple[list[AnalystSourceEvent], list[str]]:
        try:
            rows = db.execute(
                text(
                    """
                    SELECT id::text AS id, content, created_at
                    FROM app.conversation_memories
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                ),
                {"user_id": user_id},
            ).all()
        except Exception:
            return [], [self.source_name]
        events = [
            make_event(
                user_id=user_id,
                source_table=self.source_name,
                source_id=str(row.id),
                event_type="memory",
                occurred_at=_parse_dt(getattr(row, "created_at", None)) or get_now(),
                sensitivity="medium",
                text_for_llm=str(getattr(row, "content", "") or ""),
            )
            for row in rows
        ]
        return events, []


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _in_window(column: Any, start: datetime, end: datetime) -> Any:
    return column >= start, column <= end


def collect_source_events(
    db: Session,
    *,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
) -> tuple[list[AnalystSourceEvent], dict[str, int], list[str]]:
    events: list[AnalystSourceEvent] = []
    missing: list[str] = []

    mood_rows = db.scalars(
        select(MoodCheckin)
        .where(MoodCheckin.user_id == user_id, MoodCheckin.logged_at >= window_start, MoodCheckin.logged_at <= window_end)
        .order_by(MoodCheckin.logged_at.asc())
    ).all()
    for row in mood_rows:
        note, extra = parse_checkin_note(row.note)
        events.append(
            make_event(
                user_id=user_id,
                source_table="mood_checkins",
                source_id=row.checkin_id,
                event_type="mood_checkin",
                occurred_at=row.logged_at,
                local_date=row.logged_date,
                local_period=row.time_bucket if row.time_bucket in ("morning", "afternoon", "evening") else None,
                payload={"mood": row.mood, "emotions": row.emotions or [], "triggers": row.triggers or []},
                sensitivity="medium",
                text_for_llm=note,
                numeric_features={
                    "sleep_hours": extra.get("sleep_hours"),
                    "stress_level": extra.get("stress_level"),
                    "study_hours": extra.get("study_hours"),
                },
            )
        )

    meal_rows = db.scalars(
        select(NutritionMealCheckin)
        .where(
            NutritionMealCheckin.user_id == user_id,
            NutritionMealCheckin.created_at >= window_start,
            NutritionMealCheckin.created_at <= window_end,
        )
        .order_by(NutritionMealCheckin.created_at.asc())
    ).all()
    for row in meal_rows:
        events.append(
            make_event(
                user_id=user_id,
                source_table="nutrition_meal_checkins",
                source_id=row.checkin_id,
                event_type="meal_checkin",
                occurred_at=row.created_at,
                local_date=row.meal_date,
                payload={"meal_slot": row.meal_slot, "mood_before": row.mood_before, "mood_after": row.mood_after},
                sensitivity="medium",
                text_for_llm=row.items_text,
            )
        )

    profile = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    if profile and profile.last_scored_at:
        events.append(
            make_event(
                user_id=user_id,
                source_table="clinical_profiles",
                source_id=profile.profile_id,
                event_type="screening_result",
                occurred_at=profile.last_scored_at,
                payload={"has_phq9": profile.phq9_score is not None, "has_gad7": profile.gad7_score is not None},
                sensitivity="restricted",
                numeric_features={
                    "phq9_score": profile.phq9_score,
                    "gad7_score": profile.gad7_score,
                    "crisis_level": profile.crisis_level,
                },
            )
        )

    summary_rows = db.scalars(
        select(SessionSummaryArchive)
        .where(
            SessionSummaryArchive.user_id == user_id,
            SessionSummaryArchive.archived_at >= window_start,
            SessionSummaryArchive.archived_at <= window_end,
            SessionSummaryArchive.sos_triggered.is_(False),
        )
        .order_by(SessionSummaryArchive.archived_at.asc())
    ).all()
    for row in summary_rows:
        summary = row.summary if isinstance(row.summary, dict) else {}
        events.append(
            make_event(
                user_id=user_id,
                source_table="session_summaries_archive",
                source_id=str(row.archive_id),
                event_type="chat_message",
                occurred_at=row.archived_at,
                payload={"dominant_emotion": row.dominant_emotion, "summary_keys": sorted(summary.keys())[:12]},
                sensitivity="medium",
                text_for_llm=redact_excerpt(str(summary.get("summary") or summary.get("text") or "")),
            )
        )

    message_rows = db.scalars(
        select(Message)
        .where(Message.user_id == user_id, Message.created_at >= window_start, Message.created_at <= window_end)
        .order_by(Message.created_at.desc())
        .limit(20)
    ).all()
    for row in message_rows:
        if row.sos_triggered:
            continue
        events.append(
            make_event(
                user_id=user_id,
                source_table="messages",
                source_id=row.message_id,
                event_type="chat_message",
                occurred_at=row.created_at,
                payload={"role": row.role, "assistant_tone": row.assistant_tone},
                sensitivity="high",
                text_for_llm=row.content if row.role == "user" else None,
            )
        )

    card_rows = db.scalars(
        select(MemoryCard)
        .where(
            MemoryCard.user_id == user_id,
            MemoryCard.status.in_(("active", "edited_by_user")),
            MemoryCard.safety_review_status.in_(("approved", "pending")),
            MemoryCard.personalization_disabled.is_(False),
        )
        .order_by(MemoryCard.updated_at.desc())
        .limit(100)
    ).all()
    for row in card_rows:
        events.append(
            make_event(
                user_id=user_id,
                source_table="memory_cards",
                source_id=row.card_id,
                event_type="memory",
                occurred_at=row.updated_at,
                payload={"memory_type": row.memory_type, "confidence": row.confidence},
                sensitivity="medium",
                text_for_llm=f"{row.title}. {row.content}",
            )
        )

    for repo in (Mem0MemoryRepository(), ConversationMemoryRepository()):
        repo_events, repo_missing = repo.list_events(db, user_id=user_id)
        events.extend([event for event in repo_events if window_start <= event.occurred_at <= window_end])
        missing.extend(repo_missing)

    events.extend(_optional_engagement_events(db, user_id=user_id, window_start=window_start, window_end=window_end, missing=missing))
    events.extend(_safety_events(db, user_id=user_id, window_start=window_start, window_end=window_end))

    counts: dict[str, int] = {}
    for event in events:
        counts[event.source_table] = counts.get(event.source_table, 0) + 1
    return events, counts, sorted(set(missing))


def _optional_engagement_events(
    db: Session,
    *,
    user_id: str,
    window_start: datetime,
    window_end: datetime,
    missing: list[str],
) -> list[AnalystSourceEvent]:
    events: list[AnalystSourceEvent] = []
    reward_rows = db.scalars(
        select(HeartRewardEvent)
        .where(HeartRewardEvent.user_id == user_id, HeartRewardEvent.created_at >= window_start, HeartRewardEvent.created_at <= window_end)
        .order_by(HeartRewardEvent.created_at.asc())
    ).all()
    for row in reward_rows:
        events.append(
            make_event(
                user_id=user_id,
                source_table="heart_reward_events",
                source_id=row.event_id,
                event_type="resource_play",
                occurred_at=row.created_at,
                payload={"event_type": row.event_type, "source_tab": row.source_tab},
                sensitivity="low",
            )
        )

    persona_rows = db.scalars(select(PersonaUnlockState).where(PersonaUnlockState.user_id == user_id)).all()
    for row in persona_rows:
        if row.updated_at and window_start <= row.updated_at <= window_end:
            events.append(
                make_event(
                    user_id=user_id,
                    source_table="persona_unlock_states",
                    source_id=row.persona_id,
                    event_type="persona_selection",
                    occurred_at=row.updated_at,
                    payload={"persona_id": row.persona_id, "unlocked": row.unlocked},
                    sensitivity="low",
                )
            )

    for table_name, event_type in (("bookmarks", "bookmark"), ("play_events", "resource_play")):
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT * FROM app.{table_name}
                    WHERE user_id = :user_id
                    LIMIT 50
                    """
                ),
                {"user_id": user_id},
            ).all()
        except Exception:
            missing.append(table_name)
            rows = []
        for idx, row in enumerate(rows):
            occurred = _parse_dt(getattr(row, "created_at", None)) or get_now()
            if window_start <= occurred <= window_end:
                events.append(
                    make_event(
                        user_id=user_id,
                        source_table=table_name,
                        source_id=str(getattr(row, "id", idx)),
                        event_type=event_type,
                        occurred_at=occurred,
                        sensitivity="low",
                    )
                )

    _ = Resource
    return events


def _safety_events(db: Session, *, user_id: str, window_start: datetime, window_end: datetime) -> list[AnalystSourceEvent]:
    rows = db.scalars(
        select(SessionRiskSnapshot)
        .where(SessionRiskSnapshot.user_id == user_id, SessionRiskSnapshot.created_at >= window_start, SessionRiskSnapshot.created_at <= window_end)
        .order_by(SessionRiskSnapshot.created_at.asc())
    ).all()
    return [
        make_event(
            user_id=user_id,
            source_table="session_risk_snapshots",
            source_id=str(row.snapshot_id),
            event_type="safety_snapshot",
            occurred_at=row.created_at,
            payload={"crisis_mode": row.crisis_mode, "escalation_flag": row.escalation_flag, "source": row.source},
            sensitivity="restricted",
            numeric_features={"risk_score": row.risk_score, "intent_severity": row.intent_severity},
        )
        for row in rows
    ]
