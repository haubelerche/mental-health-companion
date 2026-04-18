"""Shared helpers for ClinicalProfile rows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ClinicalProfile
from app.services.utils import make_id


def get_or_create_clinical_profile(db: Session, user_id: str) -> ClinicalProfile:
    row = db.scalar(select(ClinicalProfile).where(ClinicalProfile.user_id == user_id))
    if row:
        return row
    row = ClinicalProfile(profile_id=make_id("clin"), user_id=user_id)
    db.add(row)
    db.flush()
    return row
