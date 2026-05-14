from __future__ import annotations

import json
import logging
from collections.abc import Callable

from pydantic import ValidationError

from app.analyst.types import AnalystLLMInput, AnalystLLMOutput
from app.services.observability import record_event

logger = logging.getLogger(__name__)

LLM_MODEL_VERSION = "structured-analyst-v1"


def analyze_context(
    llm_input: AnalystLLMInput,
    *,
    json_callable: Callable[[AnalystLLMInput], str] | None = None,
) -> AnalystLLMOutput:
    """Return structured analysis, failing closed on unavailable LLMs.

    The default implementation is deterministic and network-free. Production can
    inject a callable that returns strict JSON; this module performs validation
    and never writes to the database.
    """
    if json_callable is None:
        return _deterministic_output(llm_input)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            raw = json_callable(llm_input)
            payload = json.loads(raw)
            return AnalystLLMOutput.model_validate(payload)
        except TimeoutError:
            record_event("analyst.llm.timeout", metadata={"run_type": llm_input.run_type})
            return AnalystLLMOutput(status="insufficient_signal", confidence=0.0)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            last_error = exc
            record_event("analyst.llm.invalid_json", metadata={"run_type": llm_input.run_type, "attempt": attempt + 1})
    logger.warning("analyst structured LLM fallback: %s", type(last_error).__name__ if last_error else "unknown")
    return AnalystLLMOutput(status="insufficient_signal", confidence=0.0)


def _deterministic_output(llm_input: AnalystLLMInput) -> AnalystLLMOutput:
    features = llm_input.compact_features
    mood = dict(features.get("mood") or {})
    memory = dict(features.get("memory") or {})
    nutrition = dict(features.get("nutrition") or {})
    stressors = list(mood.get("top_triggers") or [])[:3] or list(memory.get("stable_stressors") or [])[:3]
    confidence = 0.65 if int((features.get("data_quality") or {}).get("total_events") or 0) >= 5 else 0.25
    candidates = []
    if mood.get("morning_evening_delta") is not None and abs(float(mood["morning_evening_delta"])) >= 1.0:
        candidates.append(
            {
                "hypothesis_type": "mood_trend",
                "title": "Mood có vẻ đổi nhịp trong ngày",
                "user_safe_summary": "Dữ liệu gần đây gợi ý mood giữa các buổi trong ngày có sự dao động. Đây chỉ là quan sát từ check-in.",
                "evidence_count": int(mood.get("checkin_count") or 0),
            }
        )
    if stressors:
        candidates.append(
            {
                "hypothesis_type": "trigger_pattern",
                "title": "Một trigger xuất hiện lặp lại",
                "user_safe_summary": f"Trong vài lần ghi nhận gần đây, {stressors[0]} xuất hiện nhiều hơn các yếu tố khác.",
                "evidence_count": int(mood.get("checkin_count") or 0),
            }
        )
    if int((nutrition.get("low_mood_after_skipped_breakfast_count") or 0)) >= 2:
        candidates.append(
            {
                "hypothesis_type": "nutrition_mood_link",
                "title": "Bữa sáng và năng lượng có thể liên quan",
                "user_safe_summary": "Một vài ngày bỏ bữa sáng xuất hiện cùng mood thấp hơn. Đây chỉ là tương quan sơ bộ, không phải kết luận nguyên nhân.",
                "evidence_count": int(nutrition.get("meal_log_count") or 0),
            }
        )
    return AnalystLLMOutput(
        status="success" if candidates else "insufficient_signal",
        emotional_themes=list(mood.get("dominant_emotions") or [])[:4],
        recurring_stressors=stressors,
        coping_preferences=list(memory.get("coping_preferences") or [])[:4],
        nutrition_links=[],
        mood_pattern_candidates=[],
        user_safe_insight_candidates=candidates,
        evidence_refs=[],
        confidence=confidence,
    )

