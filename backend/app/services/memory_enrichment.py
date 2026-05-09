"""Structured memory enrichment for user profile JSONB."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from app.services.utils import get_now

logger = logging.getLogger(__name__)

_TRIGGER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cong_viec": ("công việc", "deadline", "sếp", "đồng nghiệp", "overload"),
    "gia_dinh": ("gia đình", "ba mẹ", "bố mẹ", "con cái", "hôn nhân"),
    "tai_chinh": ("tiền", "nợ", "lương", "chi phí", "tài chính"),
    "suc_khoe": ("mất ngủ", "đau đầu", "kiệt sức", "sức khỏe", "bệnh"),
    "co_don": ("một mình", "cô đơn", "không ai hiểu", "không ai bên"),
}
_COPING_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tho_478": ("thở", "hít thở", "4-7-8"),
    "di_bo": ("đi bộ", "ra ngoài", "vận động"),
    "viet_nhat_ky": ("viết nhật ký", "journal", "ghi lại"),
    "tam_su": ("tâm sự", "chia sẻ", "nói chuyện"),
}


@dataclass
class StructuredExtract:
    key_triggers: list[str]
    coping_attempts: list[str]
    dominant_emotion: str | None
    sos_triggered: bool


def _fallback_extract(transcript: str, *, sos_triggered: bool) -> StructuredExtract:
    lowered = transcript.lower()
    triggers = [tag for tag, kws in _TRIGGER_KEYWORDS.items() if any(k in lowered for k in kws)][:5]
    coping = [tag for tag, kws in _COPING_KEYWORDS.items() if any(k in lowered for k in kws)][:5]

    dominant_emotion = None
    if any(x in lowered for x in ("lo âu", "lo au", "stress", "căng thẳng")):
        dominant_emotion = "lo_au"
    elif any(x in lowered for x in ("buồn", "that vong", "thất vọng", "mệt")):
        dominant_emotion = "buon_ba"
    elif any(x in lowered for x in ("tức", "bực", "giận")):
        dominant_emotion = "cang_thang"

    return StructuredExtract(
        key_triggers=triggers,
        coping_attempts=coping,
        dominant_emotion=dominant_emotion,
        sos_triggered=sos_triggered,
    )


def extract_structured(transcript: str, settings: Any, *, sos_triggered: bool) -> StructuredExtract:
    cleaned = str(transcript or "").strip()
    if not cleaned:
        return StructuredExtract([], [], None, sos_triggered)

    if not settings.openai_api_key:
        return _fallback_extract(cleaned, sos_triggered=sos_triggered)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 5.0))
        resp = client.chat.completions.create(
            model=settings.openai_model_analyst or "gpt-4o-mini",
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract structured JSON from this therapy chat. "
                        "Return exactly one JSON object with keys: "
                        "key_triggers (array max 5), coping_attempts (array max 5), dominant_emotion (string|null). "
                        "Use snake_case short labels. No markdown."
                    ),
                },
                {"role": "user", "content": cleaned[:3500]},
            ],
        )
        raw = str(resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return StructuredExtract(
            key_triggers=[str(x).strip() for x in list(data.get("key_triggers") or []) if str(x).strip()][:5],
            coping_attempts=[str(x).strip() for x in list(data.get("coping_attempts") or []) if str(x).strip()][:5],
            dominant_emotion=(str(data.get("dominant_emotion")).strip() or None) if data.get("dominant_emotion") is not None else None,
            sos_triggered=sos_triggered,
        )
    except Exception as exc:
        logger.warning("structured extraction failed, using fallback: %s", exc)
        return _fallback_extract(cleaned, sos_triggered=sos_triggered)


def _ensure_profile_shape(profile: dict[str, Any]) -> None:
    profile.setdefault("schema_version", "v1")
    profile.setdefault("traits", {})
    profile.setdefault("clinical_snapshot", {})
    profile.setdefault("session_summaries", [])
    profile.setdefault("trigger_tags", {})
    profile.setdefault("coping_history", [])
    profile.setdefault("goals", [])
    profile.setdefault("safety_flags", {"ever_sos_triggered": False, "last_sos_at": None, "admin_reviewed": False, "do_not_suggest_topics": []})
    profile.setdefault("stats", {"total_sessions": 0, "total_messages_user": 0, "avg_session_length_turns": None, "days_active_last_30": 0, "streak_days": 0})
    profile.setdefault("meta", {"pii_masked": True, "last_rollup_at": None, "next_rollup_at": None})


def apply_to_profile(
    profile: dict[str, Any],
    *,
    extract: StructuredExtract,
    session_meta: dict[str, Any],
    summary_text: str,
    max_items: int = 50,
) -> dict[str, Any]:
    now_iso = get_now().isoformat()
    out = dict(profile or {})
    _ensure_profile_shape(out)

    summary_entry = {
        "session_id": str(session_meta.get("session_id") or ""),
        "started_at": str(session_meta.get("started_at") or now_iso),
        "ended_at": str(session_meta.get("ended_at") or now_iso),
        "turn_count": int(session_meta.get("turn_count") or 1),
        "summary": str(summary_text or "")[:500],
        "summary_embedding_ref": None,
        "dominant_emotion": extract.dominant_emotion,
        "key_triggers": extract.key_triggers[:5],
        "resources_suggested": [],
        "resources_engaged": [],
        "sos_triggered": bool(extract.sos_triggered),
        "crisis_level_peak": int(session_meta.get("crisis_level_peak") or 0),
    }

    summaries = list(out.get("session_summaries") or [])
    summaries.append(summary_entry)
    out["session_summaries"] = summaries[-max_items:]

    trigger_tags = dict(out.get("trigger_tags") or {})
    for tag in extract.key_triggers:
        entry = dict(trigger_tags.get(tag) or {})
        entry["count"] = int(entry.get("count") or 0) + 1
        entry["last_seen"] = now_iso
        if "avg_intensity" not in entry:
            entry["avg_intensity"] = None
        trigger_tags[tag] = entry
    out["trigger_tags"] = trigger_tags

    coping_history = list(out.get("coping_history") or [])
    for action in extract.coping_attempts:
        existing = next((item for item in coping_history if str(item.get("action")) == action), None)
        if existing is None:
            coping_history.append(
                {
                    "action": action,
                    "resource_id": None,
                    "tried_count": 1,
                    "self_reported_effective": 0,
                    "last_tried": now_iso[:10],
                }
            )
        else:
            existing["tried_count"] = int(existing.get("tried_count") or 0) + 1
            existing["last_tried"] = now_iso[:10]
    out["coping_history"] = coping_history

    safety = dict(out.get("safety_flags") or {})
    safety.setdefault("ever_sos_triggered", False)
    if extract.sos_triggered:
        safety["ever_sos_triggered"] = True
        safety["last_sos_at"] = now_iso
    out["safety_flags"] = safety

    stats = dict(out.get("stats") or {})
    stats["total_sessions"] = int(stats.get("total_sessions") or 0) + 1
    out["stats"] = stats

    return out
