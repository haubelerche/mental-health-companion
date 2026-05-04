from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.core.product_constants import CURRENT_POLICY_VERSION
from app.core.responses import ok
from app.services.db.models import User, UserProfile
from app.services.db.session import get_db
from app.services.schemas.payloads import OnboardingCompleteRequest
from app.services.utils import utc_now

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _read_profile(db: Session, user_id: str) -> tuple[UserProfile, dict]:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if row is None:
        row = UserProfile(user_id=user_id, profile={})
        db.add(row)
        db.flush()
    profile_data = dict(row.profile or {})
    return row, profile_data


@router.get("/state")
def onboarding_state(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.user_id))
    profile_data = dict(row.profile or {}) if row else {}
    onboarding = dict(profile_data.get("onboarding") or {})
    return ok(
        {
            "completed": bool(onboarding.get("completed_at")),
            "skipped": bool(onboarding.get("skipped", False)),
            "profile": onboarding if onboarding else None,
        }
    )


@router.post("/complete")
def onboarding_complete(
    payload: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.disclaimer_accepted:
        raise AppError("DISCLAIMER_NOT_ACCEPTED", "Bạn cần xác nhận điều khoản trước khi tiếp tục", 400)

    row, profile_data = _read_profile(db, current_user.user_id)
    now = utc_now().replace(tzinfo=None)
    onboarding_payload = {
        "v": 1,
        "disclaimer_accepted": True,
        "nickname": payload.nickname.strip(),
        "age_group": payload.age_group,
        "emotional_state": payload.emotional_state,
        "primary_concern": payload.primary_concern,
        "support_level": payload.support_level,
        "stress_level": payload.stress_level,
        "wake_time": payload.wake_time,
        "bed_time": payload.bed_time,
        "practice_ids": list(dict.fromkeys(payload.practice_ids))[:8],
        "completed_at": now.isoformat() + "Z",
        "skipped": False,
    }

    profile_data["onboarding"] = onboarding_payload
    # Keep compatibility with existing consumers that read goals directly.
    profile_data["goals"] = onboarding_payload["practice_ids"][:5]
    row.profile = profile_data
    row.updated_at = now
    current_user.policy_acknowledged_at = now
    current_user.policy_version_ack = CURRENT_POLICY_VERSION
    db.commit()

    return ok({"completed": True, "profile": onboarding_payload})


@router.post("/skip")
def onboarding_skip(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row, profile_data = _read_profile(db, current_user.user_id)
    now = utc_now().replace(tzinfo=None)
    existing = dict(profile_data.get("onboarding") or {})
    onboarding_payload = {
        "v": int(existing.get("v") or 1),
        "disclaimer_accepted": bool(existing.get("disclaimer_accepted") or False),
        "nickname": str(existing.get("nickname") or current_user.display_name or "bạn"),
        "age_group": str(existing.get("age_group") or "prefer_not"),
        "emotional_state": str(existing.get("emotional_state") or "doing_okay"),
        "primary_concern": existing.get("primary_concern"),
        "support_level": existing.get("support_level"),
        "stress_level": int(existing.get("stress_level") or 2),
        "wake_time": str(existing.get("wake_time") or "07:30"),
        "bed_time": str(existing.get("bed_time") or "22:30"),
        "practice_ids": list(existing.get("practice_ids") or []),
        "completed_at": now.isoformat() + "Z",
        "skipped": True,
    }
    profile_data["onboarding"] = onboarding_payload
    row.profile = profile_data
    row.updated_at = now
    db.commit()

    return ok({"completed": True, "skipped": True, "profile": onboarding_payload})
