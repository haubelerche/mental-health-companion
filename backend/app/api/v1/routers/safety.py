from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged
from app.core.config import get_settings
from app.core.responses import ok
from app.db.models import User
from app.db.session import get_db
from app.schemas.payloads import SafetyEscalateRequest, TrustedContactRequest, VoiceConsentRequest
from app.services.trusted_contact import (
    add_trusted_contact,
    enqueue_trusted_contact_notification,
    get_outbound_opt_in,
    list_trusted_contacts,
    set_outbound_opt_in,
)
from app.services.vn_hotlines import hotline_cards_sos

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/hotlines")
def safety_hotlines():
    return ok({"hotlines": hotline_cards_sos()})


@router.get("/referrals/options")
def referrals_options():
    return ok({"options": [{"type": "counselor"}, {"type": "trusted_contact"}, {"type": "clinic"}]})


@router.get("/trusted-contacts")
def trusted_contacts_get(
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    contacts = list_trusted_contacts(db, current_user.user_id)
    outbound_opt_in = get_outbound_opt_in(db, current_user.user_id)
    return ok({"contacts": contacts, "outbound_opt_in": outbound_opt_in})


@router.post("/trusted-contacts")
def trusted_contacts_add(
    payload: TrustedContactRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    contacts = add_trusted_contact(
        db,
        current_user.user_id,
        {"name": payload.name, "phone": payload.phone, "relation": payload.relation},
    )
    return ok({"contacts": contacts})


@router.post("/trusted-contacts/opt-in")
def trusted_contacts_opt_in(
    payload: VoiceConsentRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    enabled = set_outbound_opt_in(db, current_user.user_id, payload.consent)
    return ok({"outbound_opt_in": enabled})


@router.post("/escalate")
def safety_escalate(
    payload: SafetyEscalateRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    contacts = list_trusted_contacts(db, current_user.user_id)
    outbound_opt_in = get_outbound_opt_in(db, current_user.user_id)
    queued = False
    outbox_id = None
    if settings.trusted_contact_outbound_enabled and outbound_opt_in and contacts:
        outbox_id = enqueue_trusted_contact_notification(
            db,
            user_id=current_user.user_id,
            session_id=payload.session_id,
            risk_level=payload.risk_level,
            reason=payload.reason,
        )
        queued = True
    return ok(
        {
            "queued": queued,
            "outbox_id": outbox_id,
            "legal_gate_enabled": settings.trusted_contact_outbound_enabled,
            "outbound_opt_in": outbound_opt_in,
            "contact_count": len(contacts),
        }
    )
