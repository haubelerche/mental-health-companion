from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.services.exercise_catalog import build_resource_attachment


def _mask_text(text: str) -> str:
    try:
        from app.services.pii_mask import mask_pii

        return mask_pii(text or "")
    except Exception:
        return text or ""


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", normalized.lower()).strip()


def _clip_dict(value: dict[str, Any], *, allowed_keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: value.get(key) for key in allowed_keys if value.get(key) is not None}


def memory_lookup(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 3)
    facts: list[str] = []
    for key in ("active_memory_text",):
        raw = str(context.get(key) or "").strip()
        if raw:
            facts.extend(line.strip("- ").strip() for line in raw.splitlines() if line.strip())
    for key in ("mem0_facts", "long_term_memories", "active_goals", "effective_coping"):
        for item in list(context.get(key) or []):
            text = _mask_text(str(item or "").strip())
            if text and text not in facts:
                facts.append(text)
            if len(facts) >= limit:
                break
    return {
        "facts": facts[:limit],
        "count": min(len(facts), limit),
        "provenance": "sanitized_chat_state",
    }


def resource_search(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 2)
    query = _fold(str(args.get("query") or context.get("user_message") or ""))
    resource_ids = ["calm_library", "sleep_meditation"]
    if any(token in query for token in ("ngu", "mat ngu", "sleep", "kho ngu")):
        resource_ids = ["sleep_meditation", "calm_library"]
    elif any(token in query for token in ("deadline", "hoc", "tap trung", "work")):
        resource_ids = ["calm_library", "sleep_meditation"]
    items = [build_resource_attachment(resource_id) for resource_id in resource_ids[:limit]]
    return {
        "resources": [
            _clip_dict(
                item,
                allowed_keys=("type", "id", "title", "description", "duration_sec", "action", "route", "thumbnail"),
            )
            for item in items
        ],
        "provenance": "curated_internal_resource_catalog",
    }


def advisor_consult(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    from app.services.chat_orchestrator import ChatOrchestrator

    user_message = str(context.get("user_message") or "")
    advisor_ids = [str(item) for item in list(args.get("advisor_ids") or []) if str(item).strip()]
    if not advisor_ids:
        _route, advisor_ids = ChatOrchestrator.resolve_route_and_advisors(
            raw_text=user_message,
            previous_user_messages=[
                str(m.get("content") or "")
                for m in list(context.get("recent_messages") or [])
                if isinstance(m, dict) and m.get("role") == "user"
            ],
        )
    advice = ChatOrchestrator.consult_advisors(
        advisor_ids=advisor_ids[:2],
        user_message=user_message,
        context_summary=str(args.get("context_summary") or user_message)[:500],
        timeout_ms=1200,
    )
    return {
        "advisor_count": len(advice),
        "advisors": [
            {
                "advisor_id": item.advisor_id,
                "confidence": item.confidence,
                "suggested_response_moves": list(item.suggested_response_moves or [])[:3],
                "forbidden_moves": list(item.forbidden_moves or [])[:3],
                "should_use": bool(item.should_use),
            }
            for item in advice[:2]
        ],
        "provenance": "internal_advisor_pool",
    }


def context_pack_read(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    max_chars = int(args.get("max_chars") or 900)
    recent = []
    for item in list(context.get("recent_messages") or [])[-6:]:
        if not isinstance(item, dict):
            continue
        recent.append(
            {
                "role": str(item.get("role") or "")[:20],
                "content": _mask_text(str(item.get("content") or ""))[:220],
            }
        )
    payload = {
        "recent_messages": recent,
        "mood_today": context.get("mood_today") or None,
        "top_triggers": list(context.get("top_triggers") or [])[:3],
        "active_goals": list(context.get("active_goals") or [])[:3],
        "clinical_trajectory": _mask_text(str(context.get("clinical_trajectory") or ""))[:240],
    }
    text_size = len(str(payload))
    if text_size > max_chars:
        payload["recent_messages"] = recent[-3:]
    return {"context": payload, "provenance": "bounded_chat_state"}


def nutrition_context_read(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    limit = int(args.get("limit") or 4)
    meals = []
    for item in list(context.get("nutrition_meals") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        meals.append(
            {
                "slot": str(item.get("slot") or "?")[:40],
                "items": _mask_text(str(item.get("items") or ""))[:160],
                "mood_before": item.get("mood_before"),
                "mood_after": item.get("mood_after"),
            }
        )
    return {"meals": meals, "count": len(meals), "provenance": "nutrition_checkins"}


def safety_policy_check(args: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    distress = float(context.get("distress_score") or 0.0)
    include_reason_codes = bool(args.get("include_reason_codes"))
    constraints = [
        "no_diagnosis",
        "no_disorder_probability",
        "no_internal_scores_in_user_text",
        "max_one_question",
    ]
    if distress >= 0.55:
        constraints.extend(["calming_tone", "no_playful_or_romantic_tone"])
    output: dict[str, Any] = {
        "distress_band": "elevated" if distress >= 0.55 else "normal",
        "constraints": constraints,
        "provenance": "deterministic_safety_policy_summary",
    }
    if include_reason_codes:
        output["reason_codes"] = ["redacted_policy_summary"]
    return output
