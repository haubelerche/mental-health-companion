from fastapi import APIRouter

from app.core.responses import ok
from app.schemas.payloads import SafetyCheckRequest
from app.services.intake_keyword_risk import intake_combined_text, score_intake_keywords
from app.services.safety_scoring import distress_to_risk_level

router = APIRouter(prefix="/intake", tags=["intake"])
# Đánh giá mức độ rủi ro từ 3 ô intake; điểm 0.0–1.0 từ quét từ khóa (có chuẩn hóa tiếng Việt).


@router.post("/safety-check")
def safety_check(payload: SafetyCheckRequest):
    """Gộp overwhelmed / unsafe / need_help_now, quét cụm từ tiếng Việt → risk_score 0.0–1.0."""
    combined = intake_combined_text(
        payload.overwhelmed,
        payload.unsafe,
        payload.need_help_now,
    )
    risk_score, _matched = score_intake_keywords(combined)
    risk_level = distress_to_risk_level(risk_score)
    # Đồng bộ với map distress→risk_level: mức 4–5 ≈ cần hướng xử lý khủng hoảng / hạ nhiệt mạnh
    should_route_crisis = risk_level >= 4
    recommended_next_step = (
        "chat_de_escalation" if should_route_crisis else "checkin_or_chat"
    )
    return ok(
        {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "should_route_crisis": should_route_crisis,
            "recommended_next_step": recommended_next_step,
        }
    )
