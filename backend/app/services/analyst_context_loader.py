"""Load typed, privacy-preserving analyst context bundles from the database."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import ClinicalProfile, MoodCheckin, SessionSummaryArchive

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MoodContextBundle:
    source_table: str = "mood_checkins"
    record_ids: list[str] = field(default_factory=list)
    evidence_count: int = 0
    emotion_counts: dict[str, int] = field(default_factory=dict)
    top_emotions: list[str] = field(default_factory=list)
    top_triggers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScreeningContextBundle:
    source_table: str = "clinical_profiles"
    evidence_count: int = 0
    phq9_score: int | None = None
    gad7_score: int | None = None
    dass21_depression_score: int | None = None
    dass21_anxiety_score: int | None = None
    dass21_stress_score: int | None = None
    mdq_score: int | None = None
    pcl5_score: int | None = None
    has_screening_data: bool = False
    instruments_available: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SessionSummaryBundle:
    source_table: str = "session_summaries_archive"
    record_ids: list[str] = field(default_factory=list)
    evidence_count: int = 0
    top_themes: list[str] = field(default_factory=list)


@dataclass
class AnalystContext:
    user_id: str
    window_days: int
    mood: MoodContextBundle
    screening: ScreeningContextBundle
    session_summaries: SessionSummaryBundle
    source_counts: dict[str, int] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)

    def total_evidence(self) -> int:
        return sum(self.source_counts.values())


class AnalystContextLoader:
    def __init__(self, db: Session) -> None:
        self._db = db

    def load_mood_context(self, *, user_id: str, window_days: int = 14) -> MoodContextBundle:
        start = date.today() - timedelta(days=window_days)
        try:
            rows = self._db.scalars(
                select(MoodCheckin)
                .where(MoodCheckin.user_id == user_id, MoodCheckin.logged_date >= start)
                .order_by(MoodCheckin.logged_date.asc())
                .limit(100)
            ).all()
        except Exception as exc:
            logger.warning("mood_checkins load failed user=%s: %s", user_id, exc)
            return MoodContextBundle()

        record_ids = [f"mood:{row.checkin_id}" for row in rows]
        emotion_counts: dict[str, int] = {}
        trigger_counts: dict[str, int] = {}
        for row in rows:
            mood = str(row.mood or "").strip()
            if mood:
                emotion_counts[mood] = emotion_counts.get(mood, 0) + 1
            for trigger in list(row.triggers or []):
                trigger_s = str(trigger).strip()
                if trigger_s:
                    trigger_counts[trigger_s] = trigger_counts.get(trigger_s, 0) + 1

        top_emotions = sorted(emotion_counts, key=lambda key: (-emotion_counts[key], key))[:3]
        top_triggers = sorted(trigger_counts, key=lambda key: (-trigger_counts[key], key))[:3]
        return MoodContextBundle(
            record_ids=record_ids,
            evidence_count=len(rows),
            emotion_counts=emotion_counts,
            top_emotions=top_emotions,
            top_triggers=top_triggers,
        )

    def load_screening_context(self, *, user_id: str) -> ScreeningContextBundle:
        try:
            profile = self._db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
        except Exception as exc:
            logger.warning("clinical_profiles load failed user=%s: %s", user_id, exc)
            return ScreeningContextBundle(limitations=["db_error"])

        if profile is None:
            return ScreeningContextBundle(limitations=["no_clinical_profile"])

        instruments: list[str] = []
        if profile.phq9_score is not None:
            instruments.append("phq9")
        if profile.gad7_score is not None:
            instruments.append("gad7")
        if profile.dass21_depression_score is not None:
            instruments.append("dass21")
        if profile.mdq_score is not None:
            instruments.append("mdq")
        if profile.pcl5_score is not None:
            instruments.append("pcl5")

        return ScreeningContextBundle(
            evidence_count=len(instruments),
            phq9_score=profile.phq9_score,
            gad7_score=profile.gad7_score,
            dass21_depression_score=profile.dass21_depression_score,
            dass21_anxiety_score=profile.dass21_anxiety_score,
            dass21_stress_score=profile.dass21_stress_score,
            mdq_score=profile.mdq_score,
            pcl5_score=profile.pcl5_score,
            has_screening_data=bool(instruments),
            instruments_available=instruments,
        )

    def load_session_summaries(self, *, user_id: str, limit: int = 5) -> SessionSummaryBundle:
        try:
            rows = self._db.scalars(
                select(SessionSummaryArchive)
                .where(
                    SessionSummaryArchive.user_id == user_id,
                    SessionSummaryArchive.sos_triggered.is_(False),
                )
                .order_by(SessionSummaryArchive.archived_at.desc())
                .limit(limit)
            ).all()
        except Exception as exc:
            logger.warning("session_summaries load failed user=%s: %s", user_id, exc)
            return SessionSummaryBundle()

        record_ids = []
        themes = []
        for row in rows:
            archive_id = getattr(row, "archive_id", None)
            if archive_id is None:
                continue
            record_ids.append(f"session:{archive_id}")
            dominant_emotion = str(getattr(row, "dominant_emotion", "") or "").strip()
            if dominant_emotion:
                themes.append(dominant_emotion)
        return SessionSummaryBundle(
            record_ids=record_ids,
            evidence_count=len(record_ids),
            top_themes=list(dict.fromkeys(themes))[:5],
        )

    def load_all(self, *, user_id: str, window_days: int = 14) -> AnalystContext:
        mood = self.load_mood_context(user_id=user_id, window_days=window_days)
        screening = self.load_screening_context(user_id=user_id)
        sessions = self.load_session_summaries(user_id=user_id)
        source_counts = {
            "mood_checkins": mood.evidence_count,
            "clinical_profiles": screening.evidence_count,
            "session_summaries_archive": sessions.evidence_count,
        }
        evidence_refs = mood.record_ids[:50] + sessions.record_ids[:10]
        if screening.evidence_count:
            user_hash = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]
            evidence_refs.append(f"screening:{user_hash}")
        return AnalystContext(
            user_id=user_id,
            window_days=window_days,
            mood=mood,
            screening=screening,
            session_summaries=sessions,
            source_counts=source_counts,
            evidence_refs=evidence_refs,
        )
