from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import User
from app.db.session import get_db
from app.schemas.payloads import ScreeningSubmitRequest
from app.services.clinical_profile import get_or_create_clinical_profile
from app.services.utils import utc_now

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
    if total <= 10:
        label = "mild"
    elif total <= 20:
        label = "moderate"
    else:
        label = "high-like"

    now = utc_now().replace(tzinfo=None)
    clin = get_or_create_clinical_profile(db, current_user.user_id)
    if payload.instrument_id == "phq9":
        clin.phq9_score = min(27, total)
        clin.phq9_coverage = {"answers": payload.answers}
    else:
        clin.gad7_score = min(21, total)
        clin.gad7_coverage = {"answers": payload.answers}
    clin.last_scored_at = now
    clin.updated_at = now
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
