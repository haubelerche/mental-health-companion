from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.services.clinical_profile import (
    SCREENING_ANSWER_OPTIONS_VERSION,
    SCREENING_ANSWER_LABELS,
    SCREENING_QUESTION_TEXT_VERSION,
    apply_screening_to_clinical_profile,
    build_screening_answer_payload,
    compute_screening_severity,
    get_or_create_clinical_profile,
)
from app.services.db.models import ScreeningAnswer, User
from app.services.db.session import get_db
from app.services.schemas.payloads import ScreeningSubmitRequest
from app.services.utils import get_now

router = APIRouter(prefix="/screenings", tags=["screenings"])

_EXPECTED_ITEMS = {"phq9": 9, "gad7": 7}


@router.get("/catalog")
def catalog(current_user: User = Depends(ensure_policy_acknowledged), db: Session = Depends(get_db)):
    _ = (current_user, db)
    return ok(
        {
            "instruments": [
                {"id": "phq9", "title": "PHQ-9 (rút gọn demo)", "item_count": 9},
                {"id": "gad7", "title": "GAD-7 (rút gọn demo)", "item_count": 7},
            ]
        }
    )


@router.post("/submit")
def submit(
    payload: ScreeningSubmitRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    expected = _EXPECTED_ITEMS.get(payload.instrument_id)
    if expected is None:
        raise AppError("INVALID_INSTRUMENT", "instrument_id không hợp lệ", 400)
    if len(payload.answers) != expected:
        raise AppError("INVALID_ANSWERS", f"Cần đúng {expected} câu trả lời cho {payload.instrument_id}", 400)

    total = sum(int(v) for v in payload.answers.values())
    label = compute_screening_severity(instrument_id=payload.instrument_id, raw_score=total)

    now = get_now().replace(tzinfo=None)
    clin = get_or_create_clinical_profile(db, current_user.user_id)
    answer_payload = build_screening_answer_payload(
        user_id=current_user.user_id,
        instrument_id=payload.instrument_id,
        answers=payload.answers,
        submitted_at=now,
        session_id=payload.session_id,
        locale=payload.locale,
    )
    apply_screening_to_clinical_profile(
        profile=clin,
        instrument_id=payload.instrument_id,
        raw_score=total,
        scored_at=now,
    )

    db.add(
        ScreeningAnswer(
            user_id=current_user.user_id,
            instrument_id=payload.instrument_id,
            screening_type=payload.instrument_id,
            question_id="bulk",
            question_key="bulk",
            answer_value=total,
            answer_label=f"severity:{label}",
            question_text_version=SCREENING_QUESTION_TEXT_VERSION[payload.instrument_id],
            answer_options_version=SCREENING_ANSWER_OPTIONS_VERSION,
            session_id=payload.session_id,
            locale=payload.locale or "vi-VN",
            raw_score=total,
            answers=answer_payload,
        )
    )
    db.commit()

    return ok(
        {
            "instrument_id": payload.instrument_id,
            "raw_score": total,
            "severity_label": label,
            "saved": True,
            "assessment_updated_at": now.isoformat() + "Z",
        }
    )
