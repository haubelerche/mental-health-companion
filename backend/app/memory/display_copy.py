"""User-facing memory-card copy normalization.

Memory cards are product copy, not analyst notes. This module turns canonical
memory candidates into short, friendly Vietnamese text and rejects internal
summary/transcript artifacts before they can be shown to users.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.memory.extractor import MemoryCandidate
from app.services.db.models import MemoryCard

MAX_TITLE_CHARS = 60
MAX_BODY_CHARS = 500
DISPLAY_COPY_VERSION = "memory_display_copy_v1"
DEFAULT_CURRENT_STRESSOR_TTL_DAYS = 30

FORBIDDEN_UI_TERMS = (
    "TÓM TẮT PHIÊN TRÒ CHUYỆN",
    "Tóm tắt phiên trò chuyện",
    "Tín hiệu cảm xúc",
    "Tác nhân chính",
    "Bước đối phó",
    "Cơ chế đối phó",
    "Gợi ý hành động",
    "clinical",
    "risk",
    "distress",
    "diagnosis",
    "user:",
    "assistant:",
    "model confidence",
    "safety tier",
    "crisis",
    "self-harm",
)

BADGE_LABELS = {
    "support_style": "Cách hỗ trợ",
    "preference": "Sở thích",
    "current_stressor": "Áp lực gần đây",
    "coping_history": "Điều từng giúp",
    "emotional_pattern": "Mẫu cảm xúc",
    "persona_preference": "Kiểu trò chuyện",
    "nutrition_pattern": "Bữa ăn",
    "kindness_pattern": "Điều tử tế",
    "event_memory": "Chuyện đã kể",
    "support_insight": "Insight",
    "relationship_context": "Gia đình & quan hệ",
    "goal_or_hope": "Mục tiêu",
    "background": "Bối cảnh",
    "temporary_context": "Tạm thời",
}

REVIEW_PROMPT = "Serene có thể nhớ điều này để hỗ trợ bạn tốt hơn không?"


@dataclass(slots=True)
class UserFacingMemoryCopy:
    badge_label: str
    title: str
    body: str
    helper_text: str | None = None
    review_prompt: str = REVIEW_PROMPT
    ttl_days: int | None = None


def confidence_prefix(confidence: float, evidence_count: int) -> str:
    if evidence_count >= 2 and confidence >= 0.75:
        return "Bạn thường"
    if confidence >= 0.60:
        return "Bạn có vẻ"
    return "Serene có thể nhớ rằng"


def _candidate_value(candidate: MemoryCandidate | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(candidate, MemoryCandidate):
        return getattr(candidate, key, default)
    return candidate.get(key, default)


def _clean_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(user|assistant)\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def _sentence(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    text = text[:MAX_BODY_CHARS].rstrip(" ,;:")
    if text[-1:] not in ".!?":
        text += "."
    return text


def _has_forbidden_terms(text: str) -> bool:
    lowered = text.lower()
    for term in FORBIDDEN_UI_TERMS:
        if term.lower() in lowered:
            return True
    return False


def _looks_like_raw_transcript(text: str) -> bool:
    return bool(re.search(r"(^|\n|\s)(user|assistant)\s*:", text, flags=re.IGNORECASE))


def _title_for(memory_type: str, fallback: str) -> str:
    titles = {
        "support_style": "Cách Serene nên hỗ trợ bạn",
        "preference": "Một điều bạn thích",
        "current_stressor": "Một áp lực gần đây",
        "coping_history": "Điều từng giúp bạn nhẹ hơn",
        "emotional_pattern": "Điều có thể lặp lại với bạn",
        "persona_preference": "Kiểu trò chuyện bạn hay chọn",
        "nutrition_pattern": "Điều liên quan tới bữa ăn của bạn",
        "kindness_pattern": "Một điều tử tế Serene nên nhớ",
    }
    return (titles.get(memory_type) or fallback or "Một điều Serene nên nhớ")[:MAX_TITLE_CHARS]


def _body_for(memory_type: str, content: str, confidence: float, evidence_count: int) -> str:
    lowered = content.lower()
    prefix = confidence_prefix(confidence, evidence_count)

    if memory_type == "support_style":
        if "ngắn" in lowered or "ngan" in lowered or "ít chữ" in lowered:
            return "Bạn có vẻ hợp với những câu trả lời ngắn gọn và trực tiếp."
        return _sentence(f"{prefix} hợp với một cách hỗ trợ nhẹ và rõ ràng")

    if memory_type == "preference":
        if content.startswith(("Bạn ", "Serene ")):
            return _sentence(content)
        return _sentence(f"{prefix} thích {content[0].lower() + content[1:] if content else 'một cách trò chuyện rõ ràng'}")

    if memory_type == "current_stressor":
        if "deadline" in lowered:
            return "Bạn đã chia sẻ rằng deadline đang khiến bạn dễ quá tải."
        if "gia đình" in lowered or "gia dinh" in lowered:
            return "Gần đây, áp lực gia đình có vẻ làm bạn mệt hơn."
        if "công việc" in lowered or "cong viec" in lowered:
            return "Gần đây, công việc có vẻ là một nguồn áp lực với bạn."
        return _sentence(f"Gần đây, {content[0].lower() + content[1:] if content else 'có một áp lực đang làm bạn căng hơn'}")

    if memory_type == "coping_history":
        if "đi bộ" in lowered or "di bo" in lowered:
            return "Bạn từng thấy đi bộ một chút giúp đầu óc dịu lại."
        if "hít thở" in lowered or "hit tho" in lowered or "thở sâu" in lowered:
            return "Bạn từng thấy hít thở chậm giúp mình dịu lại hơn."
        return _sentence(f"Bạn từng thấy {content[0].lower() + content[1:] if content else 'một cách nhỏ giúp mình nhẹ hơn'}")

    if memory_type == "emotional_pattern":
        if evidence_count >= 2 and confidence >= 0.75:
            return _sentence(f"Bạn thường {content[0].lower() + content[1:] if content else 'dễ bị ảnh hưởng bởi một mẫu cảm xúc lặp lại'}")
        if content.startswith(("Bạn có vẻ", "Khi ", "Gần đây,")):
            return _sentence(content)
        return _sentence(f"Bạn có vẻ {content[0].lower() + content[1:] if content else 'có một mẫu cảm xúc Serene nên để ý nhẹ nhàng'}")

    if memory_type == "persona_preference":
        return _sentence(f"{prefix} hợp với kiểu trò chuyện này trong một số lúc")

    if memory_type == "nutrition_pattern":
        if "bữa" in lowered or "ăn" in lowered:
            return _sentence(f"Bạn từng {content[0].lower() + content[1:]}")
        return "Khi bận, bạn có vẻ dễ ăn muộn hơn bình thường."

    return _sentence(f"Serene có thể nhớ rằng {content[0].lower() + content[1:] if content else 'có một điều nhỏ giúp hỗ trợ bạn tốt hơn'}")


def build_user_facing_memory_copy(candidate: MemoryCandidate | dict[str, Any]) -> UserFacingMemoryCopy:
    memory_type = str(_candidate_value(candidate, "memory_type", "") or "")
    title = _clean_text(_candidate_value(candidate, "title", "") or "")
    content = _clean_text(_candidate_value(candidate, "content", "") or "")
    confidence = float(_candidate_value(candidate, "confidence", 0.7) or 0.0)
    metadata = dict(_candidate_value(candidate, "metadata", {}) or {})
    evidence_count = int(metadata.get("evidence_count") or 1)
    ttl_days = int(metadata.get("ttl_days") or DEFAULT_CURRENT_STRESSOR_TTL_DAYS) if memory_type == "current_stressor" else None

    copy = UserFacingMemoryCopy(
        badge_label=BADGE_LABELS.get(memory_type, "Ký ức"),
        title=_title_for(memory_type, title),
        body=_body_for(memory_type, content, confidence, evidence_count),
        helper_text=None,
        ttl_days=ttl_days,
    )
    result = validate_user_facing_memory_copy(copy)
    if not result["approved"]:
        raise ValueError(result["rejection_reason"] or "invalid_display_copy")
    return copy


def validate_user_facing_memory_copy(copy: UserFacingMemoryCopy | dict[str, Any]) -> dict[str, str | bool | None]:
    title = _clean_text(copy.title if isinstance(copy, UserFacingMemoryCopy) else copy.get("title", ""))
    body = _clean_text(copy.body if isinstance(copy, UserFacingMemoryCopy) else copy.get("body", ""))
    text = f"{title} {body}"

    if not title:
        return {"approved": False, "rejection_reason": "empty_display_title"}
    if not body:
        return {"approved": False, "rejection_reason": "empty_display_body"}
    if len(title) > MAX_TITLE_CHARS:
        return {"approved": False, "rejection_reason": "display_title_too_long"}
    if len(body) > MAX_BODY_CHARS:
        return {"approved": False, "rejection_reason": "display_body_too_long"}
    if _has_forbidden_terms(text):
        return {"approved": False, "rejection_reason": "forbidden_internal_wording"}
    if _looks_like_raw_transcript(text):
        return {"approved": False, "rejection_reason": "raw_transcript_marker"}
    return {"approved": True, "rejection_reason": None}


def display_copy_from_card(card: MemoryCard) -> UserFacingMemoryCopy | None:
    # Prefer the short display_category label (atomic extraction).
    # Legacy cards stored the full sentence in title — truncate so validation
    # does not permanently mark them rejected_by_guardrail.
    raw_title = str(getattr(card, "display_category", None) or card.title or "").strip()
    title = _clean_text(raw_title)[:MAX_TITLE_CHARS]
    # Enforce body length for cards created before the 160-char cap.
    body = _clean_text(card.content)[:MAX_BODY_CHARS]
    copy = UserFacingMemoryCopy(
        badge_label=BADGE_LABELS.get(card.memory_type, "Ký ức"),
        title=title,
        body=body,
        helper_text=None,
        review_prompt=REVIEW_PROMPT,
        ttl_days=None,
    )
    result = validate_user_facing_memory_copy(copy)
    if not result["approved"]:
        return None
    return copy


def compute_expires_at(created_at: Any, ttl_days: int | None) -> Any:
    if ttl_days is None or created_at is None:
        return None
    return created_at + timedelta(days=ttl_days)
