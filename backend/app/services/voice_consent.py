from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserProfile

VOICE_CONSENT_KEY = "voice_consent"


def get_voice_consent(db: Session, user_id: str) -> bool:
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not profile_row:
        return False
    profile = dict(profile_row.profile or {})
    return bool(profile.get(VOICE_CONSENT_KEY, False))


def set_voice_consent(db: Session, user_id: str, consent: bool) -> bool:
    profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not profile_row:
        profile_row = UserProfile(user_id=user_id, profile={})
        db.add(profile_row)
        db.flush()
    profile = dict(profile_row.profile or {})
    profile[VOICE_CONSENT_KEY] = bool(consent)
    profile_row.profile = profile
    db.commit()
    return bool(profile.get(VOICE_CONSENT_KEY, False))
