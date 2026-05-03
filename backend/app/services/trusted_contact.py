from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.db.models import SyncOutbox, UserProfile

TRUSTED_CONTACTS_KEY = "trusted_contacts"
OUTBOUND_OPT_IN_KEY = "trusted_contact_outbound_opt_in"


def list_trusted_contacts(db: Session, user_id: str) -> list[dict]:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not row:
        return []
    profile = dict(row.profile or {})
    return list(profile.get(TRUSTED_CONTACTS_KEY) or [])


def add_trusted_contact(db: Session, user_id: str, contact: dict) -> list[dict]:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not row:
        row = UserProfile(user_id=user_id, profile={})
        db.add(row)
        db.flush()
    profile = dict(row.profile or {})
    contacts = list(profile.get(TRUSTED_CONTACTS_KEY) or [])
    contacts.append(contact)
    profile[TRUSTED_CONTACTS_KEY] = contacts[:5]
    row.profile = profile
    db.commit()
    return list(profile.get(TRUSTED_CONTACTS_KEY) or [])


def set_outbound_opt_in(db: Session, user_id: str, enabled: bool) -> bool:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not row:
        row = UserProfile(user_id=user_id, profile={})
        db.add(row)
        db.flush()
    profile = dict(row.profile or {})
    profile[OUTBOUND_OPT_IN_KEY] = bool(enabled)
    row.profile = profile
    db.commit()
    return bool(profile.get(OUTBOUND_OPT_IN_KEY))


def get_outbound_opt_in(db: Session, user_id: str) -> bool:
    row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if not row:
        return False
    profile = dict(row.profile or {})
    return bool(profile.get(OUTBOUND_OPT_IN_KEY, False))


def enqueue_trusted_contact_notification(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    risk_level: int,
    reason: str,
) -> int:
    event = SyncOutbox(
        event_type="trusted_contact.notify_request",
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "risk_level": risk_level,
            "reason": reason,
        },
        status="pending",
    )
    db.add(event)
    db.flush()
    outbox_id = int(event.outbox_id)
    db.commit()
    return outbox_id
