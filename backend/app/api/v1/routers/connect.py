from fastapi import APIRouter, Response

from app.core.responses import ok
from app.schemas.payloads import ClinicsRequest

router = APIRouter(prefix="/connect", tags=["connect"])


@router.get("/hotlines")
def hotlines():
    return ok(
        {
            "hotlines": [
                {
                    "name": "Đường dây hỗ trợ sức khỏe tâm thần quốc gia",
                    "number": "1800-599-920",
                    "available": "24/7",
                    "note": "Miễn phí",
                },
                {
                    "name": "Tổng đài hỗ trợ trẻ em",
                    "number": "111",
                    "available": "24/7",
                    "note": "Miễn phí",
                },
            ]
        }
    )


@router.post("/clinics")
def clinics(payload: ClinicsRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    clinics_data = [
        {
            "id": "c_01",
            "name": "Trung tâm Tư vấn Tâm lý ABC",
            "address": "12 Nguyễn Trãi, Hà Nội",
            "lat": 21.028,
            "lng": 105.851,
            "phone": "024-1234-5678",
            "hours": "8:00-17:00, Thứ 2-Thứ 6",
            "distance_km": 1.2,
        }
    ]

    if payload.lat is not None and payload.lng is not None:
        clinics_data[0]["distance_km"] = 0.5

    return ok({"clinics": clinics_data})
