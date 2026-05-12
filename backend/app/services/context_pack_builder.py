from __future__ import annotations

import time
from typing import Any, Callable

from app.services.schemas.contracts import ContextPack

Provider = Callable[[], Any]


def _safe_call(provider: Provider, *, timeout_ms: int) -> Any:
    started = time.perf_counter()
    try:
        value = provider()
    except Exception:
        return None
    elapsed = int((time.perf_counter() - started) * 1000)
    if elapsed > timeout_ms:
        return None
    return value


class ContextPackBuilder:
    def __init__(self, *, timeout_ms: int = 300) -> None:
        self.timeout_ms = timeout_ms
        self.last_fallback_reasons: list[str] = []

    def _call_with_reason(self, provider: Provider, *, key: str) -> Any:
        if hasattr(self, "_build_started_at"):
            elapsed_ms = int((time.perf_counter() - self._build_started_at) * 1000)
            if elapsed_ms >= self.timeout_ms:
                self.last_fallback_reasons.append(f"{key}_budget_exceeded")
                return None
        value = _safe_call(provider, timeout_ms=self.timeout_ms)
        if value is None:
            self.last_fallback_reasons.append(key)
        return value

    @staticmethod
    def _compact_screening_summary(payload: Any) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        keep = {
            "phq9_score": payload.get("phq9_score"),
            "gad7_score": payload.get("gad7_score"),
            "phq9_band": payload.get("phq9_band"),
            "gad7_band": payload.get("gad7_band"),
            "updated_at": payload.get("updated_at"),
        }
        compact = {k: v for k, v in keep.items() if v is not None}
        return compact or None

    @staticmethod
    def _compact_resources(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            return []
        out: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            out.append(
                {
                    "resource_id": str(item.get("resource_id") or item.get("id") or "")[:100],
                    "title": str(item.get("title") or "")[:200],
                    "why_this": str(item.get("why_this") or item.get("description") or "")[:280],
                    "delivery_mode": str(item.get("delivery_mode") or "card"),
                }
            )
            if len(out) >= 5:
                break
        return [r for r in out if r["resource_id"]]

    def build(
        self,
        *,
        safety_policy,
        recent_messages: list[dict[str, Any]],
        active_memory_provider: Provider,
        onboarding_provider: Provider,
        mood_provider: Provider,
        nutrition_provider: Provider,
        screening_provider: Provider,
        resource_candidates_provider: Provider,
        persona_provider: Provider,
    ) -> ContextPack:
        self.last_fallback_reasons = []
        self._build_started_at = time.perf_counter()

        def _sanitize_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            cleaned: list[dict[str, Any]] = []
            for item in rows[-8:]:
                content = str(item.get("content") or "")
                if "crisis_log" in content.lower() or "clinical_note_internal" in content.lower():
                    continue
                cleaned.append({"role": item.get("role"), "content": content[:500]})
            return cleaned

        screening = self._compact_screening_summary(self._call_with_reason(screening_provider, key="screening"))
        resources = self._compact_resources(self._call_with_reason(resource_candidates_provider, key="resources"))

        try:
            return ContextPack(
                recent_messages=_sanitize_messages(recent_messages),
                active_memory=self._call_with_reason(active_memory_provider, key="active_memory"),
                onboarding_summary=self._call_with_reason(onboarding_provider, key="onboarding"),
                mood_context=self._call_with_reason(mood_provider, key="mood"),
                nutrition_context=self._call_with_reason(nutrition_provider, key="nutrition"),
                screening_summary=screening,
                resource_candidates=resources,
                persona_context=self._call_with_reason(persona_provider, key="persona"),
                safety_policy=safety_policy,
            )
        finally:
            if hasattr(self, "_build_started_at"):
                delattr(self, "_build_started_at")
