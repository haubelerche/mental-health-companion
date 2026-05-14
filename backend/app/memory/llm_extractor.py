"""LLM-based atomic memory candidate extraction.

Calls the configured LLM with a structured prompt that extracts user-facing
atomic memory candidates from a masked conversation transcript.

Falls back to an empty ExtractionResult on any LLM error so the caller can
chain the deterministic extractor as a fallback.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings
from app.memory.extractor import AtomicMemoryCandidate, ExtractionResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Bạn trích xuất ký ức ngắn gọn dành cho người dùng từ một đoạn hội thoại với ứng dụng sức khỏe tâm thần Serene.

Trả về JSON hợp lệ theo đúng cấu trúc sau, không thêm text ngoài JSON:
{
  "candidate_cards": [
    {
      "memory_type": "event_memory|support_insight|background|relationship_context|current_stressor|emotional_pattern|coping_history|goal_or_hope|preference|support_style|persona_preference|nutrition_pattern|temporary_context",
      "display_category": "Chuyện đã kể|Insight|Bối cảnh|Gia đình & quan hệ|Áp lực gần đây|Mẫu cảm xúc|Điều từng giúp|Mục tiêu|Sở thích|Cách hỗ trợ|Kiểu trò chuyện|Bữa ăn|Tạm thời",
      "subject": "chủ thể ngắn gọn (không dấu, snake_case)",
      "predicate": "vị từ ngắn gọn (không dấu, snake_case)",
      "display_text": "Một câu tiếng Việt tối đa 160 ký tự",
      "confidence": 0.0,
      "is_temporary": false,
      "ttl_days": null,
      "evidence_message_ids": [],
      "sensitivity_level": "low|medium|high"
    }
  ]
}

Hướng dẫn chọn memory_type:
- event_memory: chuyện người dùng kể đã xảy ra ("Bạn đã kể rằng bố mẹ không lắng nghe bạn.")
- support_insight: insight giúp Serene hỗ trợ tốt hơn ("Khi bị hỏi dồn, bạn có vẻ dễ áp lực hơn.")
- background: thông tin nền về cuộc sống/công việc ("Bạn làm việc ở nhà.")
- relationship_context: quan hệ gia đình, bạn bè ("Bạn mong được kết nối với bố mẹ nhiều hơn.")
- current_stressor: áp lực đang xảy ra, có ttl_days 7–30 ("Deadline đang khiến bạn căng thẳng.")
- emotional_pattern: xu hướng cảm xúc lặp lại ("Bạn thường cảm thấy đơn độc vào buổi tối.")
- coping_history: điều từng giúp ("Bạn từng thấy đi bộ giúp dịu lại.")
- goal_or_hope: mục tiêu hoặc kỳ vọng ("Bạn muốn kết nối tốt hơn với gia đình.")
- preference: sở thích tương tác ("Bạn thích Serene trả lời ngắn khi bạn mệt.")
- support_style: cách Serene nên hỗ trợ ("Bạn hợp với cách hỗ trợ nhẹ nhàng, không hỏi nhiều.")
- temporary_context: ngữ cảnh tạm thời, có ttl_days 7–14.

Quy tắc viết display_text:
- Bắt đầu bằng: "Bạn đã kể rằng..." / "Bạn từng nói..." / "Bạn có vẻ..." / "Khi ..., bạn thường..." / "Bạn từng thấy..." / "Bạn mong..." / "Bạn thích..."
- Không bắt đầu bằng "User..." hay dùng tiếng Anh.
- Không dùng nhãn: Tín hiệu cảm xúc, Tác nhân chính, Bước đối phó, session_summary.
- Không có "user:" hay "assistant:".
- Không chẩn đoán. Không nêu chi tiết nguy hiểm, tự làm hại, khủng hoảng.
- Nếu không có ký ức rõ, trả về candidate_cards rỗng [].
- current_stressor và temporary_context phải có ttl_days từ 7–30.
"""

_VALID_MEMORY_TYPES = {
    "background", "support_style", "current_stressor", "coping_history",
    "preference", "persona_preference", "nutrition_pattern", "temporary_context",
    "event_memory", "support_insight", "relationship_context", "goal_or_hope",
    "emotional_pattern",
}


def _parse_candidates(raw: Any, *, session_id: str | None) -> list[AtomicMemoryCandidate]:
    if not isinstance(raw, dict):
        return []
    items = raw.get("candidate_cards") or []
    if not isinstance(items, list):
        return []

    result: list[AtomicMemoryCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        memory_type = str(item.get("memory_type") or "").strip()
        if memory_type not in _VALID_MEMORY_TYPES:
            continue
        display_text = str(item.get("display_text") or "").strip()
        if not display_text:
            continue
        subject = str(item.get("subject") or display_text[:60]).strip()
        predicate = str(item.get("predicate") or display_text[:80]).strip()
        key = (memory_type, subject.lower(), predicate.lower())
        if key in seen:
            continue
        seen.add(key)

        is_temporary = bool(item.get("is_temporary")) or memory_type in {"current_stressor", "temporary_context"}
        ttl_raw = item.get("ttl_days")
        ttl_days: int | None = None
        if is_temporary and ttl_raw is not None:
            try:
                ttl_days = max(7, min(30, int(ttl_raw)))
            except (TypeError, ValueError):
                ttl_days = 14

        sensitivity = str(item.get("sensitivity_level") or "low")
        if sensitivity not in {"low", "medium", "high"}:
            sensitivity = "low"

        result.append(
            AtomicMemoryCandidate(
                memory_type=memory_type,  # type: ignore[arg-type]
                display_category=str(item.get("display_category") or "Ký ức").strip()[:60],
                subject=subject,
                predicate=predicate,
                display_text=display_text[:160],
                confidence=min(1.0, max(0.0, float(item.get("confidence") or 0.7))),
                is_temporary=is_temporary,
                ttl_days=ttl_days,
                evidence_message_ids=[str(e) for e in (item.get("evidence_message_ids") or []) if str(e or "").strip()],
                source_session_id=session_id,
                sensitivity_level=sensitivity,  # type: ignore[arg-type]
                metadata={"extractor": "llm_atomic_v1"},
            )
        )
    return result


def extract_memory_candidates_llm(
    transcript: str,
    *,
    session_id: str | None = None,
) -> ExtractionResult:
    """Call LLM to extract atomic memory candidates from a masked transcript.

    Returns an empty ExtractionResult on any error — callers should chain the
    deterministic extractor as a fallback.
    """
    cleaned = " ".join(str(transcript or "").split()).strip()
    if not cleaned:
        return ExtractionResult()

    settings = get_settings()
    if not settings.openai_api_key:
        return ExtractionResult()

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=min(getattr(settings, "llm_timeout_seconds", 10.0), 10.0),
        )
        resp = client.chat.completions.create(
            model=getattr(settings, "openai_model_analyst", "gpt-4o-mini"),
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": cleaned[:3000]},
            ],
        )
        raw_text = str(resp.choices[0].message.content or "").strip()
        if not raw_text:
            return ExtractionResult()
        parsed = json.loads(raw_text)
        candidates = _parse_candidates(parsed, session_id=session_id)
        return ExtractionResult(candidate_cards=candidates)
    except Exception as exc:
        logger.warning("llm memory extraction failed (session=%s): %s", session_id, exc)
        return ExtractionResult()
