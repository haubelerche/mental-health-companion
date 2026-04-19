from fastapi import APIRouter

from app.core.responses import ok
from app.schemas.payloads import GuestChoiceRequest, GuestHeartbeatRequest
from app.services.guest_service import heartbeat, record_choice, start_session

router = APIRouter(prefix="/guest", tags=["guest"])


@router.post("/session/start")
def guest_start():
    sid, ttl = start_session()
    return ok({"guest_session_id": sid, "max_duration_sec": ttl})


@router.post("/session/heartbeat")
def guest_heartbeat(payload: GuestHeartbeatRequest):
    ok_h = heartbeat(payload.guest_session_id)
    return ok({"alive": ok_h})


@router.post("/choice")
def guest_choice(payload: GuestChoiceRequest):
    if not record_choice(payload.guest_session_id, payload.choice):
        from app.core.errors import AppError

        raise AppError("INVALID_PARAMETER", "Phiên guest không hợp lệ hoặc đã hết hạn", 400)
    return ok({"recorded": True, "choice": payload.choice})


@router.post("/convert")
def guest_convert():
    from app.core.errors import AppError

    raise AppError("INVALID_PARAMETER", "Hoàn tất đăng ký rồi gọi lại với JWT", 400)
