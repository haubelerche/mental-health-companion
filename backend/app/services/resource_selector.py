from __future__ import annotations

from typing import Any

from app.services.schemas.resources import ResourceSelectionInput, ResourceSuggestion

_CATALOG: dict[str, tuple[str, str, str]] = {
    "grounding": ("breathing_3m", "Thở 3 phút", "Một nhịp thở ngắn giúp hạ căng ngay lúc này."),
    "journaling": ("journal_5m", "Viết nhanh 5 phút", "Viết ngắn để làm rõ điều đang nặng."),
    "sleep": ("sleep_winddown_10m", "Giãn nhịp trước ngủ", "Nếp đi ngủ ngắn giúp đầu óc chậm lại."),
    "task_breakdown": ("micro_step_10m", "Bước nhỏ 10 phút", "Chia nhỏ việc để bớt quá tải."),
    "reflection": ("single_question_reflect", "Một câu phản tư", "Giữ cuộc trò chuyện tập trung vào điểm chính."),
}


class ResourceSelector:
    @staticmethod
    def _score_candidate(candidate: dict[str, Any], payload: ResourceSelectionInput) -> int:
        score = 0
        tags = [str(t).lower() for t in (candidate.get("tags") or []) if isinstance(t, str)]
        title = str(candidate.get("title") or "").lower()
        text = " ".join(tags + [title])
        if payload.conversation_need in text:
            score += 4
        if payload.user_preference == "short":
            duration = int(candidate.get("duration_sec") or 0)
            if 0 < duration <= 300:
                score += 2
        if payload.time_available_minutes <= 3:
            duration = int(candidate.get("duration_sec") or 0)
            if 0 < duration <= 180:
                score += 3
        if payload.emotion and payload.emotion.lower() in text:
            score += 1
        return score

    def select(self, payload: ResourceSelectionInput) -> ResourceSuggestion:
        resource_id, title, why = _CATALOG[payload.conversation_need]
        mode = "inline_short" if payload.time_available_minutes <= 3 else "card"
        if payload.user_preference == "short":
            mode = "inline_short"
        return ResourceSuggestion(
            resource_id=resource_id,
            title=title,
            why_this=why,
            delivery_mode=mode,
        )

    def select_from_candidates(
        self,
        *,
        payload: ResourceSelectionInput,
        candidates: list[dict[str, Any]],
    ) -> ResourceSuggestion:
        ranked = sorted(candidates, key=lambda c: self._score_candidate(c, payload), reverse=True)
        top = ranked[0] if ranked and self._score_candidate(ranked[0], payload) > 0 else None
        if not top:
            return self.select(payload)
        mode = "inline_short" if payload.user_preference == "short" or payload.time_available_minutes <= 3 else "card"
        return ResourceSuggestion(
            resource_id=str(top.get("resource_id") or top.get("id") or "fallback_resource"),
            title=str(top.get("title") or "Gợi ý phù hợp"),
            why_this=str(top.get("description") or "Phù hợp với ngữ cảnh hiện tại.")[:280],
            delivery_mode=mode,
        )
