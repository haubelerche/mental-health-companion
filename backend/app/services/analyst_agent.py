from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import MoodCheckin, NutritionMealCheckin
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
        today = date.today()
        start = today - timedelta(days=14)
        mood_rows = db.scalars(
            select(MoodCheckin)
            .where(MoodCheckin.user_id == user_id, MoodCheckin.logged_date >= start)
            .order_by(MoodCheckin.logged_date.asc())
        ).all()
        meal_rows = db.scalars(
            select(NutritionMealCheckin)
            .where(NutritionMealCheckin.user_id == user_id, NutritionMealCheckin.meal_date >= start)
            .order_by(NutritionMealCheckin.meal_date.asc())
        ).all()

        events: list[dict[str, Any]] = []
        for idx, row in enumerate(mood_rows):
            events.append(
                {
                    "event_id": f"mood:{idx}:{row.checkin_id}",
                    "emotion": row.mood,
                    "triggers": list(row.triggers or []),
                }
            )
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
        out.evidence_refs = list(dict.fromkeys(list(out.evidence_refs or []) + mem0_evidence))
        if mem0_rows and "insufficient_signal" in out.missing_info:
            out.missing_info = [item for item in out.missing_info if item != "insufficient_signal"]
        return out
