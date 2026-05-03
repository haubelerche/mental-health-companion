from fastapi import APIRouter, Response

from app.core.responses import ok
from app.services.schemas.payloads import ClinicsRequest
from app.services.vn_hotlines import connect_hotlines_list
from app.services.clinics import clinics_for_default_list, clinics_near

router = APIRouter(prefix="/connect", tags=["connect"])


@router.get("/hotlines")
def hotlines():
    return ok({"hotlines": connect_hotlines_list()})


@router.post("/clinics")
def clinics(payload: ClinicsRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if payload.lat is not None and payload.lng is not None:
        clinics_data = clinics_near(payload.lat, payload.lng, payload.radius_km)
    else:
        clinics_data = clinics_for_default_list()
    return ok({"clinics": clinics_data})
