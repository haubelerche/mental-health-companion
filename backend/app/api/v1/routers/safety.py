from fastapi import APIRouter

from app.core.responses import ok
from app.services.vn_hotlines import hotline_cards_sos

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/hotlines")
def safety_hotlines():
    return ok({"hotlines": hotline_cards_sos()})


@router.get("/referrals/options")
def referrals_options():
    return ok({"options": [{"type": "counselor"}, {"type": "trusted_contact"}, {"type": "clinic"}]})
