import logging
import asyncio
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.db.models import AdminAuditLog, Conversation, CrisisLog, Message, User
from app.db.session import get_db
from app.schemas.payloads import ChatEndRequest, ChatMessageRequest
from app.services.chat_context import load_chat_context_sync
from app.services.langgraph_chat import build_normal_envelope, run_non_sos_turn
from app.services.pii_mask import mask_pii
from app.services.rate_limit import get_rate_limiter
from app.services.session_summary import close_session_summary
from app.services.sos_handler import (
    assistant_text_for_stored_message_sos,
    build_sos_chat_response_data,
    decide_sos,
    heuristic_distress,
    snapshot_for_sos,
)
from app.services.clinical_profile import get_or_create_clinical_profile
from app.services.safety_scoring import compute_escalation_signal
from app.services.voice_consent import get_voice_consent
from app.services.proactive_voice import (
    build_voice_script,
    cooldown_active,
    enqueue_voice_job,
    get_voice_audio_path,
    get_voice_job,
    mark_cooldown,
)
from app.services.utils import make_id, utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_AUDIT_ADMIN = "sys_auto"


def _record_sos_side_effects(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    context_summary: str,
    request_host: str | None,
) -> None:
    db.add(
        CrisisLog(
            log_id=make_id("cl"),
            session_id=session_id,
            user_id=user_id,
            muc_do="cao",
            context_summary=context_summary[:2000],
            reviewed=False,
        )
    )
    db.add(
        AdminAuditLog(
            admin_id=SYSTEM_AUDIT_ADMIN,
            action="SOS_TRIGGERED",
            resource_accessed=f"/v1/chat/session/{session_id}",
            ip_address=request_host or "0.0.0.0",
            metadata_json={"user_id": user_id, "kind": "crisis_keyword"},
        )
    )
    clin = get_or_create_clinical_profile(db, user_id)
    clin.crisis_level = max(int(clin.crisis_level or 0), 5)
    clin.last_scored_at = utc_now().replace(tzinfo=None)


def _recent_distress_history(recent_messages: list[dict], *, max_turns: int) -> list[float]:
    user_msgs = [m for m in recent_messages if m.get("role") == "user"]
    history: list[float] = []
    for row in user_msgs[-max_turns:]:
        content = str(row.get("content") or "")
        history.append(heuristic_distress(content))
    return history


def _build_voice_intervention(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    raw_text: str,
    recent_messages: list[dict],
    snapshot,
    trigger_reason: str,
    rolling_window_turns: int,
    delta_score: float,
) -> dict:
    script = build_voice_script(
        user_message=raw_text,
        recent_messages=recent_messages,
        distress_score=snapshot.distress_score,
        risk_level=snapshot.risk_level,
        safety_tier=snapshot.safety_tier,
        conversation_mode=snapshot.conversation_mode,
    )
    voice = enqueue_voice_job(
        db,
        user_id=user_id,
        session_id=session_id,
        voice_script=script,
        trigger_reason=trigger_reason,
        trigger_snapshot={
            "distress_score": snapshot.distress_score,
            "risk_level": snapshot.risk_level,
            "safety_tier": snapshot.safety_tier,
            "rolling_window_turns": rolling_window_turns,
            "delta_score": delta_score,
        },
    )
    mark_cooldown(user_id=user_id, session_id=session_id)
    return {
        "type": "proactive_voice",
        "trigger_reason": trigger_reason,
        "trigger_snapshot": {
            "distress_score": snapshot.distress_score,
            "risk_level": snapshot.risk_level,
            "safety_tier": snapshot.safety_tier,
            "rolling_window_turns": rolling_window_turns,
            "delta_score": delta_score,
        },
        "cooldown": {"active": False, "seconds_remaining": 0},
        "voice": voice,
        "voice_script": script,
        "copy_ngan": "Mình gửi cậu một lời nhắn thoại ngắn để đồng hành ngay lúc này.",
        "crisis_footer": {
            "show_once": True,
            "text": "Nếu cậu đang có ý định tự hại ngay lúc này, hãy bấm để kết nối hỗ trợ khẩn cấp.",
            "hotline_cta": {"label": "Gọi hỗ trợ khẩn cấp", "action": "open_hotline_sheet"},
        },
        "next_actions": [
            {"id": "continue_voice", "label": "Nói chuyện tiếp", "action": "open_voice_session_placeholder"},
            {"id": "grounding_54321", "label": "Bài tập 5-4-3-2-1", "action": "start_grounding"},
        ],
    }


@router.post("/message")
def send_message(
    payload: ChatMessageRequest,
    request: Request,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    limiter = get_rate_limiter()
    limiter.enforce_per_minute(
        key=f"chat:{current_user.user_id}",
        limit=settings.chat_rate_limit_per_minute,
        code="RATE_LIMIT_EXCEEDED",
        message="Cậu ơi, cậu dùng hết gói chat trial rùi nè, hãy đăng ký tài khoản để mình nói chuyện được lâu hơn nhé!",
    )

    now = utc_now().replace(tzinfo=None)
    session = None
    if payload.session_id:
        session = db.scalar(
            select(Conversation).where(
                Conversation.session_id == payload.session_id,
                Conversation.user_id == current_user.user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if not session:
            raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)
    else:
        session = Conversation(
            session_id=make_id("sess"),
            user_id=current_user.user_id,
            message_count=0,
            started_at=now,
            last_message_at=now,
        )
        db.add(session)
        db.flush()

    raw_text = payload.message
    sos, distress0 = decide_sos(raw_text)
    stored_user_content = mask_pii(raw_text)

    user_msg = Message(
        message_id=make_id("msg"),
        session_id=session.session_id,
        user_id=current_user.user_id,
        role="user",
        content=stored_user_content,
        created_at=now,
    )
    db.add(user_msg)
    db.flush()

    ctx = load_chat_context_sync(
        db,
        session_id=session.session_id,
        user_id=current_user.user_id,
        message_limit=8,
    )
    voice_consent = get_voice_consent(db, current_user.user_id)
    cooldown_is_active, cooldown_seconds = cooldown_active(
        user_id=current_user.user_id,
        session_id=session.session_id,
    )

    host = request.client.host if request.client else None

    if sos:
        snap = snapshot_for_sos(distress0)
        assistant_content = assistant_text_for_stored_message_sos()
        assistant_msg = Message(
            message_id=make_id("msg"),
            session_id=session.session_id,
            user_id=current_user.user_id,
            role="assistant",
            content=assistant_content,
            tone_cam_xuc=None,
            sos_triggered=True,
            created_at=now,
        )
        db.add(assistant_msg)
        session.message_count += 2
        session.last_message_at = now
        _record_sos_side_effects(
            db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            context_summary=mask_pii(raw_text)[:500],
            request_host=host,
        )
        db.commit()
        data = build_sos_chat_response_data(session.session_id, snap)
        data["intervention"] = None
        if voice_consent and not cooldown_is_active:
            data["intervention"] = _build_voice_intervention(
                db=db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                raw_text=raw_text,
                recent_messages=ctx.recent_messages,
                snapshot=snap,
                trigger_reason="sos_gate",
                rolling_window_turns=1,
                delta_score=0.0,
            )
        return ok(data)

    distress = distress0
    if ctx.mood_today and ctx.mood_today.get("mood") in ("stressed", "restless", "melancholic"):
        distress = min(1.0, distress + 0.08)

    try:
        turn = run_non_sos_turn(
            user_message=raw_text,
            recent_messages=ctx.recent_messages,
            mood_today=ctx.mood_today,
            distress_score=distress,
        )
    except Exception as exc:
        logger.exception("langgraph chat failed")
        raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504) from exc

    snap = turn["session_fields"]
    assistant_content = turn["reply"]
    tone = turn["tone_cam_xuc"]
    goi_y = turn["goi_y_nhanh"]
    the_dinh = turn["the_dinh_kem"]

    assistant_msg = Message(
        message_id=make_id("msg"),
        session_id=session.session_id,
        user_id=current_user.user_id,
        role="assistant",
        content=mask_pii(assistant_content),
        tone_cam_xuc=tone if tone in ("ho_tro", "xac_nhan", "vui_tuoi", "lam_diu") else "xac_nhan",
        sos_triggered=False,
        created_at=now,
    )
    db.add(assistant_msg)
    session.message_count += 2
    session.last_message_at = now
    db.commit()

    vhint = None
    if snap.safety_tier == "voice_recommended":
        vhint = (
            "Bạn có thể bấm gọi để nói chuyện trực tiếp với Mây / tổng đài — mình vẫn ở đây trong lúc bạn cân nhắc."
        )

    data = build_normal_envelope(
        session.session_id,
        snap=snap,
        reply=assistant_content,
        tone_cam_xuc=tone,
        goi_y_nhanh=goi_y,
        the_dinh_kem=the_dinh,
        voice_hint=vhint,
    )
    data["intervention"] = None
    history = _recent_distress_history(
        ctx.recent_messages,
        max_turns=settings.proactive_voice_window_turns,
    )
    signal = compute_escalation_signal(
        current_distress=distress,
        previous_distress=history,
        threshold=settings.proactive_voice_threshold,
        delta_threshold=settings.proactive_voice_delta_threshold,
        window_turns=settings.proactive_voice_window_turns,
    )
    if signal.escalate and voice_consent and not cooldown_is_active:
        data["intervention"] = _build_voice_intervention(
            db=db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            raw_text=raw_text,
            recent_messages=ctx.recent_messages,
            snapshot=snap,
            trigger_reason=signal.trigger_reason,
            rolling_window_turns=signal.rolling_window_turns,
            delta_score=signal.delta_score,
        )
    elif signal.escalate and voice_consent and cooldown_is_active:
        data["intervention"] = {
            "type": "proactive_voice",
            "trigger_reason": "cooldown_active",
            "cooldown": {"active": True, "seconds_remaining": cooldown_seconds},
            "voice": {"status": "cooldown", "tts_job_id": None, "audio_url": None},
        }
    return ok(data)


@router.get("/voice-jobs/{tts_job_id}")
def get_voice_job_status(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    job = get_voice_job(db, tts_job_id)
    if not job:
        raise AppError("VOICE_JOB_NOT_FOUND", "Voice job không tồn tại", 404)
    return ok(job)


@router.get("/voice-jobs/{tts_job_id}/events")
async def stream_voice_job_events(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user

    async def event_stream():
        previous_status = None
        for _ in range(30):
            job = get_voice_job(db, tts_job_id)
            if not job:
                yield "event: error\ndata: {\"code\":\"VOICE_JOB_NOT_FOUND\"}\n\n"
                return
            status = job.get("status")
            if status != previous_status:
                payload = json.dumps(job, ensure_ascii=False)
                yield f"event: status\ndata: {payload}\n\n"
                previous_status = status
            if status in {"ready", "failed", "synced"}:
                return
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/voice-jobs/{tts_job_id}/audio")
def get_voice_job_audio(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    audio_path = get_voice_audio_path(db, tts_job_id)
    if not audio_path:
        raise AppError("VOICE_AUDIO_NOT_READY", "Audio chưa sẵn sàng", 404)
    return FileResponse(path=audio_path, media_type="audio/mpeg", filename=audio_path.name)


@router.post("/end")
def end_chat_session(
    payload: ChatEndRequest,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(Conversation).where(
            Conversation.session_id == payload.session_id,
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not session:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)
    summary = close_session_summary(db, session=session, user_id=current_user.user_id)
    return ok({"session_id": session.session_id, "summarized": True, "summary": summary})


@router.get("/sessions")
def get_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == current_user.user_id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.last_message_at.desc())
    ).all()

    sessions = []
    for row in rows:
        preview = db.scalar(
            select(Message.content)
            .where(Message.session_id == row.session_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        sessions.append(
            {
                "session_id": row.session_id,
                "last_message_at": row.last_message_at.isoformat() + "Z",
                "preview": preview,
            }
        )

    return ok({"sessions": sessions})


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not session:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)

    total = db.scalar(select(func.count(Message.message_id)).where(Message.session_id == session_id)) or 0
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    messages = [
        {
            "message_id": m.message_id,
            "role": m.role,
            "content": m.content,
            "tone_cam_xuc": m.tone_cam_xuc,
            "the_dinh_kem": [],
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in rows
    ]

    return ok(
        {
            "session_id": session_id,
            "messages": messages,
            "total": total,
            "has_more": offset + len(messages) < total,
        }
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    hard: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.scalar(
        select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if not session:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)

    now = utc_now().replace(tzinfo=None)
    session.deleted_at = now
    if hard:
        session.hard_deleted_at = now
        session.anonymous_summary = None
    else:
        session.hard_deleted_at = now + timedelta(days=90)
        session.anonymous_summary = {
            "turn_count": session.message_count,
            "dominant_tone": "xac_nhan",
            "had_sos": False,
        }

    db.commit()
    return ok(
        {
            "deleted_at": session.deleted_at.isoformat() + "Z",
            "hard_delete_at": session.hard_deleted_at.isoformat() + "Z",
        }
    )
