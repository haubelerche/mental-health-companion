from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.product_constants import CURRENT_POLICY_VERSION
from app.core.responses import ok
from app.services.db.models import User
from app.services.db.session import get_db
from app.services.schemas.payloads import PolicyAckRequest, VoiceConsentRequest
from app.services.voice_consent import get_voice_consent, set_voice_consent
from app.services.utils import get_now

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/current")
def policies_current(current_user: User = Depends(get_current_user)):
    _ = current_user
    return ok(
        {
            "version": CURRENT_POLICY_VERSION,
            "title": "Điều khoản & quyền riêng tư",
            "summary": "AI không thay thế chuyên gia; dữ liệu được xử lý theo chính sách bảo mật.",
        }
    )


@router.post("/acknowledge")
def policies_ack(
    payload: PolicyAckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, current_user.user_id)
    if not user:
        raise AppError("AUTH_INVALID_TOKEN", "Token không hợp lệ", 401)
    user.policy_version_ack = payload.policy_version
    user.policy_acknowledged_at = get_now().replace(tzinfo=None)
    db.commit()
    return ok({"policy_version": payload.policy_version, "acknowledged_at": user.policy_acknowledged_at.isoformat() + "Z"})


@router.get("/voice-consent")
def voice_consent_get(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consent = get_voice_consent(db, current_user.user_id)
    return ok({"voice_consent": consent})


@router.post("/voice-consent")
def voice_consent_set(
    payload: VoiceConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consent = set_voice_consent(db, current_user.user_id, payload.consent)
    return ok({"voice_consent": consent})
