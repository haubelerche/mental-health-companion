from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.analyst_context_loader import AnalystContextLoader
from app.services.db.models import NutritionMealCheckin
from app.services.langfuse_tracing import get_active_tracer
from app.services.mem0_repository import list_all_user_memories
from app.services.schemas.contracts import AnalystBundle


class AnalystAgent:
    def generate_bundle(self, *, user_id: str, events: list[dict]) -> AnalystBundle:
        evidence_refs = [str((e or {}).get("event_id") or f"evt_{idx}") for idx, e in enumerate(events[:8])]
        trigger_counter: Counter[str] = Counter()
        emotions: Counter[str] = Counter()
        for event in events:
            if not isinstance(event, dict):
                continue
            for trigger in event.get("triggers", []) or []:
                if isinstance(trigger, str) and trigger.strip():
                    trigger_counter[trigger.strip().lower()] += 1
            emotion = event.get("emotion")
            if isinstance(emotion, str) and emotion.strip():
                emotions[emotion.strip().lower()] += 1

        recurring_triggers = [name for name, cnt in trigger_counter.most_common(3) if cnt >= 2]
        dominant_emotions = [name for name, _ in emotions.most_common(3)]
        confidence = "high" if len(evidence_refs) >= 5 else ("medium" if len(evidence_refs) >= 2 else "low")
        missing = []
        if len(evidence_refs) < 2:
            missing.append("insufficient_signal")

        return AnalystBundle(
            user_id=user_id,
            time_window={"scope": "rolling_14d"},
            dominant_emotions=dominant_emotions,
            recurring_triggers=recurring_triggers,
            cognitive_patterns=[],
            nutrition_patterns=[],
            coping_preferences=[],
            evidence_refs=evidence_refs,
            confidence=confidence,  # type: ignore[arg-type]
            missing_info=missing,
            safe_dashboard_candidates=[],
        )

    def generate_bundle_from_db(self, *, db: Session, user_id: str) -> AnalystBundle:
        loader = AnalystContextLoader(db=db)
        ctx = loader.load_all(user_id=user_id, window_days=14)
        _tracer = get_active_tracer()
        if _tracer is not None:
            for src, count in ctx.source_counts.items():
                _tracer.event(
                    f"analyst.source.{src}",
                    output_data={"record_count": count, "source_table": src},
                    metadata={"agent": "analyst_batch", "status": "ok" if count > 0 else "empty"},
                )
            _tracer.event(
                "analyst.context_load",
                output_data={
                    "total_evidence": ctx.total_evidence(),
                    "source_counts": ctx.source_counts,
                    "evidence_refs_count": len(ctx.evidence_refs),
                },
                metadata={"agent": "analyst_batch"},
            )

        events: list[dict[str, Any]] = []
        for ref in ctx.evidence_refs[:60]:
            parts = str(ref).split(":", 2)
            source = parts[0] if parts else "unknown"
            events.append({"event_id": ref, "emotion": None, "triggers": [f"{source}_signal"]})

        for emotion in ctx.mood.top_emotions:
            events.append({"event_id": f"top_emotion:{emotion}", "emotion": emotion, "triggers": []})
        for trigger in ctx.mood.top_triggers:
            events.append({"event_id": f"top_trigger:{trigger}", "emotion": None, "triggers": [trigger]})

        meal_rows = db.scalars(
            select(NutritionMealCheckin)
            .where(NutritionMealCheckin.user_id == user_id)
            .order_by(NutritionMealCheckin.meal_date.asc())
            .limit(100)
        ).all()

        for idx, row in enumerate(meal_rows):
            events.append(
                {
                    "event_id": f"meal:{idx}:{row.checkin_id}",
                    "emotion": row.mood_after or row.mood_before,
                    "triggers": [f"meal_{row.meal_slot}"],
                }
            )

        mem0_rows = list_all_user_memories(db, user_id=user_id, batch_size=200, max_rows=2000)
        for idx, row in enumerate(mem0_rows):
            events.append(
                {
                    "event_id": f"mem0:{idx}:{row.id}",
                    "emotion": None,
                    "triggers": [f"mem0_source_{str(row.source or 'unknown').strip().lower()}"],
                }
            )
        out = self.generate_bundle(user_id=user_id, events=events)
        mem0_evidence = [f"mem0:{row.id}" for row in mem0_rows[:300]]
        out.evidence_refs = list(dict.fromkeys(list(ctx.evidence_refs or []) + list(out.evidence_refs or []) + mem0_evidence))

        if ctx.screening.has_screening_data:
            screening_note_parts: list[str] = []
            s = ctx.screening
            if s.phq9_score is not None:
                screening_note_parts.append(f"phq9_band:{_phq9_band(s.phq9_score)}")
            if s.gad7_score is not None:
                screening_note_parts.append(f"gad7_band:{_gad7_band(s.gad7_score)}")
            if s.dass21_depression_score is not None:
                screening_note_parts.append(f"dass21_dep_band:{_dass21_depression_band(s.dass21_depression_score)}")
            if s.dass21_anxiety_score is not None:
                screening_note_parts.append(f"dass21_anx_band:{_dass21_anxiety_band(s.dass21_anxiety_score)}")
            if s.dass21_stress_score is not None:
                screening_note_parts.append(f"dass21_str_band:{_dass21_stress_band(s.dass21_stress_score)}")
            if s.mdq_score is not None:
                screening_note_parts.append(f"mdq_band:{_mdq_band(s.mdq_score)}")
            if s.pcl5_score is not None:
                screening_note_parts.append(f"pcl5_band:{_pcl5_band(s.pcl5_score)}")
            if screening_note_parts:
                out.safe_dashboard_candidates.append(
                    {
                        "type": "screening_context_notice",
                        "instruments": list(ctx.screening.instruments_available),
                        "signal": " ".join(screening_note_parts),
                    }
                )

        missing = list(out.missing_info)
        if ctx.screening.evidence_count == 0:
            missing.append("no_screening_data")
        if ctx.session_summaries.evidence_count == 0:
            missing.append("no_session_summaries")
        out.missing_info = list(dict.fromkeys(missing))
        if mem0_rows and "insufficient_signal" in out.missing_info:
            out.missing_info = [item for item in out.missing_info if item != "insufficient_signal"]
        return out


def _phq9_band(score: int) -> str:
    if score <= 4:
        return "minimal"
    if score <= 9:
        return "mild"
    if score <= 14:
        return "moderate"
    return "moderately_severe_or_above"


def _gad7_band(score: int) -> str:
    if score <= 4:
        return "minimal"
    if score <= 9:
        return "mild"
    if score <= 14:
        return "moderate"
    return "severe"


def _dass21_depression_band(score: int) -> str:
    if score <= 9:
        return "normal"
    if score <= 13:
        return "mild"
    if score <= 20:
        return "moderate"
    return "severe_or_above"


def _dass21_anxiety_band(score: int) -> str:
    if score <= 7:
        return "normal"
    if score <= 9:
        return "mild"
    if score <= 14:
        return "moderate"
    return "severe_or_above"


def _dass21_stress_band(score: int) -> str:
    if score <= 14:
        return "normal"
    if score <= 18:
        return "mild"
    if score <= 25:
        return "moderate"
    return "severe_or_above"


def _mdq_band(score: int) -> str:
    return "possible_signal" if score >= 7 else "no_signal"


def _pcl5_band(score: int) -> str:
    if score <= 10:
        return "minimal"
    if score <= 32:
        return "low_to_moderate"
    if score <= 50:
        return "moderate"
    return "moderately_high"
