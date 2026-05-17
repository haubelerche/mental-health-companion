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
    screening = dict(features.get("screening") or {})
    data_quality = dict(features.get("data_quality") or {})
    stressors = list(mood.get("top_triggers") or [])[:3] or list(memory.get("stable_stressors") or [])[:3]
    total_events = int(data_quality.get("total_events") or 0)
    checkin_count = int(mood.get("checkin_count") or 0)
    confidence = 0.65 if total_events >= 5 else 0.25
    candidates = []

    # Pattern 1: intraday mood swing
    if mood.get("morning_evening_delta") is not None and abs(float(mood["morning_evening_delta"])) >= 1.0:
        candidates.append(
            {
                "hypothesis_type": "mood_trend",
                "title": "Mood có vẻ đổi nhịp trong ngày",
                "user_safe_summary": "Dữ liệu gần đây gợi ý mood giữa các buổi trong ngày có sự dao động. Đây chỉ là quan sát từ check-in.",
                "evidence_count": checkin_count,
            }
        )

    # Pattern 2: consistently low average mood (score ≤ 4 on 1–10 scale, ≥ 3 check-ins)
    avg_score = mood.get("avg_score")
    if avg_score is not None and float(avg_score) <= 4.0 and checkin_count >= 3:
        candidates.append(
            {
                "hypothesis_type": "low_mood_trend",
                "title": "Tâm trạng gần đây có vẻ thấp hơn bình thường",
                "user_safe_summary": (
                    f"Trong {checkin_count} lần check-in gần đây, điểm tâm trạng trung bình của bạn "
                    f"khá thấp (khoảng {float(avg_score):.1f}/10). Serene ghi nhận đây là tín hiệu cần chú ý — "
                    "đây chỉ là quan sát từ dữ liệu, Serene không đưa ra kết luận y tế."
                ),
                "evidence_count": checkin_count,
                "severity_band": "low",
            }
        )

    # Pattern 3: recurring trigger
    if stressors:
        candidates.append(
            {
                "hypothesis_type": "trigger_pattern",
                "title": "Một trigger xuất hiện lặp lại",
                "user_safe_summary": f'Trong vài lần ghi nhận gần đây, "{stressors[0]}" xuất hiện nhiều hơn các yếu tố khác.',
                "evidence_count": checkin_count,
            }
        )

    # Pattern 4: nutrition–mood correlation
    if int((nutrition.get("low_mood_after_skipped_breakfast_count") or 0)) >= 2:
        candidates.append(
            {
                "hypothesis_type": "nutrition_mood_link",
                "title": "Bữa sáng và năng lượng có thể liên quan",
                "user_safe_summary": "Một vài ngày bỏ bữa sáng xuất hiện cùng mood thấp hơn. Đây chỉ là tương quan sơ bộ, không phải kết luận nguyên nhân.",
                "evidence_count": int(nutrition.get("meal_log_count") or 0),
            }
        )

    # Pattern 5: screening signal notice (PHQ-9 mild+ or GAD-7 mild+)
    phq_band = str(screening.get("phq9_score_band_internal") or "")
    gad_band = str(screening.get("gad7_score_band_internal") or "")
    _mild_plus = {"mild_signal", "moderate_signal", "moderately_severe_signal", "severe_signal"}
    if screening.get("available") and (phq_band in _mild_plus or gad_band in _mild_plus):
        candidates.append(
            {
                "hypothesis_type": "screening_context_notice",
                "title": "Kết quả sàng lọc gần đây có tín hiệu cần chú ý",
                "user_safe_summary": (
                    "Bài sàng lọc gần đây của bạn có một số tín hiệu mà Serene muốn theo dõi cùng bạn theo thời gian. "
                    "Đây không phải chẩn đoán — chỉ là điểm tham chiếu để Serene hiểu bạn hơn."
                ),
                "evidence_count": int(screening.get("available") or 0),
                "severity_band": "low",
            }
        )

    # Pattern 6: mood volatility — high standard deviation signals unstable period
    volatility = mood.get("volatility")
    if volatility is not None and float(volatility) >= 2.5 and checkin_count >= 4:
        candidates.append(
            {
                "hypothesis_type": "stress_pattern",
                "title": "Tâm trạng dao động nhiều trong thời gian gần đây",
                "user_safe_summary": (
                    f"Dựa trên {checkin_count} lần check-in, tâm trạng của bạn thay đổi khá nhiều từ ngày này sang ngày khác. "
                    "Sự dao động này có thể liên quan đến áp lực hoặc thay đổi môi trường — Serene chỉ ghi nhận để cùng bạn theo dõi."
                ),
                "evidence_count": checkin_count,
                "severity_band": "low",
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

