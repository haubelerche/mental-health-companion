import logging
import asyncio
import json
import mimetypes
import threading
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ensure_policy_acknowledged, get_current_user, require_csrf
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import AdminAuditLog, Conversation, CrisisLog, Message, User, UserProfile
from app.services.db.session import get_db
from app.services.schemas.payloads import ChatEndRequest, ChatMessageRequest, GuestChatMessageRequest
from app.services.chat_context import load_chat_context_sync
from app.services.chat_response_cache import get_cached_turn, hash_message, set_cached_turn
from app.services.confidence_router import route_for_human_review
from app.services.guest_service import heartbeat as guest_heartbeat
from app.services.guest_service import start_session as guest_start_session
from app.services.langgraph_chat import build_normal_envelope, run_non_sos_turn, stream_non_sos_turn_events
from app.services.longterm_memory import (
    UserMemoryContext,
    build_user_memory_context,
    get_user_longterm_memories,
    persist_turn_memory,
)
from app.services.mem0_service import MemoryManager
from app.services.pii_mask import mask_pii
from app.services.rate_limit import get_rate_limiter
from app.services.session_summary import close_session_summary
from app.services.sos_handler import (
    assistant_text_for_sos,
    build_sos_chat_response_data,
    decide_sos,
    heuristic_distress,
    snapshot_for_sos,
)
from app.services.clinical_profile import get_or_create_clinical_profile
from app.services.safety_scoring import SafetySnapshot, compute_escalation_signal
from app.services.proactive_voice import (
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
DEFAULT_PERSONA_ID = "ban_than"


def _build_heartbeat_event(*, started_at: float, last_heartbeat_at: float, stage: str, interval_seconds: float = 0.4):
    now = time.perf_counter()
    if now - last_heartbeat_at < interval_seconds:
        return last_heartbeat_at, None
    payload = {
        "stage": stage,
        "elapsed_ms": int((now - started_at) * 1000),
    }
    return now, "event: heartbeat\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def _enqueue_turn_mem0(user_id: str, raw_text: str, assistant_text: str) -> None:
    """Persist recent turn to Mem0 without blocking the API response path."""
    try:
        MemoryManager.instance().add_session(
            user_id=user_id,
            messages=[
                {"role": "user", "content": raw_text},
                {"role": "assistant", "content": assistant_text},
            ],
        )
    except Exception as exc:  # pragma: no cover - fail-safe
        logger.warning("mem0 turn add failed for %s: %s", user_id, exc)


def _active_persona_id(db: Session, user_id: str) -> str:
    if not hasattr(db, "scalar"):
        return DEFAULT_PERSONA_ID
    try:
        profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    except Exception:
        return DEFAULT_PERSONA_ID
    profile_data = dict(profile_row.profile or {}) if profile_row else {}
    persona_data = dict(profile_data.get("persona") or {})
    selected = str(persona_data.get("selected") or "").strip()
    return selected or DEFAULT_PERSONA_ID


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


def _queue_human_review(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    distress_score: float,
    message: str,
    host: str | None,
) -> None:
    row = CrisisLog(
        log_id=make_id("cl"),
        session_id=session_id,
        user_id=user_id,
        muc_do="cao",
        context_summary=f"[pending_review distress={distress_score:.2f}] {mask_pii(message)[:1800]}",
        reviewed=False,
    )
    db.add(row)
    db.add(
        AdminAuditLog(
            admin_id=SYSTEM_AUDIT_ADMIN,
            action="HIGH_RISK_REVIEW_QUEUED",
            resource_accessed=f"/v1/chat/session/{session_id}",
            ip_address=host or "0.0.0.0",
            metadata_json={"user_id": user_id, "distress_score": round(float(distress_score), 3)},
        )
    )


def _recent_distress_history(recent_messages: list[dict], *, max_turns: int) -> list[float]:
    user_msgs = [m for m in recent_messages if m.get("role") == "user"]
    history: list[float] = []
    for row in user_msgs[-max_turns:]:
        content = str(row.get("content") or "")
        history.append(heuristic_distress(content))
    return history


def _should_load_memory_context(raw_text: str, recent_messages: list[dict]) -> bool:
    """Load memory context even on short/low-distress turns when user asks recall-style questions."""
    text = str(raw_text or "").lower()
    recall_keywords = (
        "nhớ",
        "nho",
        "lần trước",
        "lan truoc",
        "hôm qua",
        "hom qua",
        "hội thoại trước",
        "hoi thoai truoc",
        "trước đó",
        "truoc do",
        "tôi là ai",
        "toi la ai",
        "mình là ai",
        "minh la ai",
        "bạn còn nhớ",
        "ban con nho",
        "nhắc lại",
        "nhac lai",
        "tiếp tục",
        "tiep tuc",
    )
    if any(k in text for k in recall_keywords):
        return True
    # Session already has enough turns, keep continuity context warm.
    return len(recent_messages) >= 4


def _load_memory_context_for_turn(
    db: Session,
    *,
    user_id: str,
    raw_text: str,
    recent_messages: list[dict],
    distress_score: float,
) -> tuple[UserMemoryContext | None, list[str]]:
    """Load memory once per turn, only when the turn benefits from recall/personalization."""
    should_load = (
        distress_score >= 0.35
        or len(raw_text) >= 40
        or _should_load_memory_context(raw_text, recent_messages)
    )
    if not should_load:
        return None, []

    try:
        memory_ctx = build_user_memory_context(
            db,
            user_id=user_id,
            current_query=raw_text,
        )
        return memory_ctx, memory_ctx.recent_summaries
    except Exception as exc:
        logger.warning("build_user_memory_context failed, fallback to recent summaries: %s", exc)
        compat_longterm = get_user_longterm_memories(db, user_id=user_id, limit=3)
        return None, compat_longterm


def _build_voice_intervention(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    assistant_reply_for_tts: str,
    snapshot,
    trigger_reason: str,
    rolling_window_turns: int,
    delta_score: float,
) -> dict:
    """TTS is the same text as the assistant/Friend reply (no separate crisis script, no meta copy)."""
    script = (assistant_reply_for_tts or "").strip()
    tts_cfg = get_settings()
    requested_tts = str(getattr(tts_cfg, "tts_provider", "elevenlabs") or "elevenlabs").lower()
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
        "requested_tts_provider": requested_tts,
        "voice": voice,
        "voice_script": script,
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


def _maybe_enqueue_voice(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    snap,
    assistant_content: str,
    recent_messages: list[dict],
    cooldown_is_active: bool,
    cooldown_seconds: int,
    settings,
) -> dict | None:
    """Single authority for proactive voice trigger decisions on non-SOS turns.

    Evaluates the escalation signal and distress threshold, then either enqueues
    a TTS job or returns a cooldown placeholder. Returns None when voice should
    not fire. SOS path bypasses this function and calls _build_voice_intervention
    directly (unconditional).
    """
    if not str(assistant_content or "").strip():
        return None
    final_distress = float(snap.distress_score)
    history = _recent_distress_history(recent_messages, max_turns=settings.proactive_voice_window_turns)
    signal = compute_escalation_signal(
        current_distress=final_distress,
        previous_distress=history,
        threshold=settings.proactive_voice_threshold,
        delta_threshold=settings.proactive_voice_delta_threshold,
        window_turns=settings.proactive_voice_window_turns,
    )
    auto_thr = float(settings.proactive_voice_auto_distress_threshold)
    if not (signal.escalate or final_distress >= auto_thr):
        return None
    if cooldown_is_active:
        return {
            "type": "proactive_voice",
            "trigger_reason": "cooldown_active",
            "cooldown": {"active": True, "seconds_remaining": cooldown_seconds},
            "voice": {"status": "cooldown", "tts_job_id": None, "audio_url": None},
        }
    trigger_reason = signal.trigger_reason if signal.escalate else "distress_auto_voice"
    return _build_voice_intervention(
        db=db,
        user_id=user_id,
        session_id=session_id,
        assistant_reply_for_tts=assistant_content,
        snapshot=snap,
        trigger_reason=trigger_reason,
        rolling_window_turns=signal.rolling_window_turns,
        delta_score=signal.delta_score,
    )


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
    session.message_count += 1
    session.last_message_at = now

    ctx = load_chat_context_sync(
        db,
        session_id=session.session_id,
        user_id=current_user.user_id,
        message_limit=16,
        message_token_budget=1400,
    )
    previous_user_messages = [str(m.get("content") or "") for m in ctx.recent_messages if m.get("role") == "user"]
    if previous_user_messages and previous_user_messages[-1] == stored_user_content:
        previous_user_messages = previous_user_messages[:-1]
    sos, distress0 = decide_sos(raw_text, recent_user_messages=previous_user_messages)
    cooldown_is_active, cooldown_seconds = cooldown_active(
        user_id=current_user.user_id,
        session_id=session.session_id,
    )

    host = request.client.host if request.client else None

    if sos:
        snap = snapshot_for_sos(distress0)
        sos_count = db.scalar(
            select(func.count(Message.message_id)).where(
                Message.session_id == session.session_id,
                Message.role == "assistant",
                Message.sos_triggered == True,  # noqa: E712
            )
        ) or 0
        assistant_content = assistant_text_for_sos(raw_text, sos_count)
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
        session.message_count += 1
        session.last_message_at = now
        _record_sos_side_effects(
            db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            context_summary=mask_pii(raw_text)[:500],
            request_host=host,
        )
        db.commit()
        data = build_sos_chat_response_data(session.session_id, snap, assistant_text=assistant_content)
        data["intervention"] = _build_voice_intervention(
            db=db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            assistant_reply_for_tts=assistant_content,
            snapshot=snap,
            trigger_reason="sos_gate_forced",
            rolling_window_turns=1,
            delta_score=0.0,
        )
        return ok(data)

    # Persist user turn before calling LLM to release DB connection back to pool.
    db.commit()

    # distress_score frozen after decide_sos() — mood is context for LangGraph, not a routing delta.
    distress = distress0

    turn = None
    message_hash = hash_message(raw_text, context_seed=f"{session.session_id}:{session.message_count}:{len(ctx.recent_messages)}")
    if settings.chat_response_cache_ttl_seconds > 0:
        turn = get_cached_turn(session.session_id, message_hash)

    if turn is None:
        try:
            memory_ctx, compat_longterm = _load_memory_context_for_turn(
                db,
                user_id=current_user.user_id,
                raw_text=raw_text,
                recent_messages=ctx.recent_messages,
                distress_score=distress,
            )
            turn = run_non_sos_turn(
                user_message=raw_text,
                recent_messages=ctx.recent_messages,
                mood_today=ctx.mood_today,
                distress_score=distress,
                long_term_memories=(memory_ctx.recent_summaries if memory_ctx else compat_longterm),
                mem0_facts=(memory_ctx.mem0_facts if memory_ctx else []),
                user_traits=(memory_ctx.traits if memory_ctx else {}),
                top_triggers=(memory_ctx.top_triggers if memory_ctx else []),
                active_goals=(memory_ctx.active_goals if memory_ctx else []),
                effective_coping=(memory_ctx.effective_coping if memory_ctx else []),
                clinical_trajectory=(memory_ctx.clinical_trajectory if memory_ctx else ""),
                persona_id=_active_persona_id(db, current_user.user_id),
                user_id=current_user.user_id,
                session_id=session.session_id,
            )
            set_cached_turn(
                session.session_id,
                message_hash,
                turn,
                ttl_seconds=settings.chat_response_cache_ttl_seconds,
            )
        except Exception as exc:
            logger.exception("langgraph chat failed")
            raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504) from exc

    snap = turn["session_fields"]
    assistant_content = turn["reply"]
    tone = turn["tone_cam_xuc"]
    goi_y = turn["goi_y_nhanh"]
    the_dinh = turn["the_dinh_kem"]
    routing_hist: list[str] = turn.get("routing_history") or []

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
    session.message_count += 1
    session.last_message_at = now
    persist_turn_memory(
        db,
        user_id=current_user.user_id,
        session_id=session.session_id,
        user_message=raw_text,
        assistant_reply=assistant_content,
        sos_triggered=False,
    )
    review_decision = route_for_human_review(
        distress_score=snap.distress_score,
        sos_triggered=False,
        threshold=0.85,
    )
    if review_decision.requires_human_review:
        _queue_human_review(
            db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            distress_score=snap.distress_score,
            message=raw_text,
            host=host,
        )
    db.commit()
    threading.Thread(
        target=_enqueue_turn_mem0,
        args=(current_user.user_id, raw_text, assistant_content),
        daemon=True,
    ).start()

    vhint = None
    if snap.safety_tier == "voice_recommended":
        vhint = (
            "Bạn có thể bấm gọi để nói chuyện trực tiếp với Friend / tổng đài — mình vẫn ở đây trong lúc bạn cân nhắc."
        )

    data = build_normal_envelope(
        session.session_id,
        snap=snap,
        reply=assistant_content,
        tone_cam_xuc=tone,
        goi_y_nhanh=goi_y,
        the_dinh_kem=the_dinh,
        voice_hint=vhint,
        routing_history=routing_hist,
    )
    data["intervention"] = None
    if review_decision.requires_human_review:
        data["pending_human_review"] = True
        data["review_reason"] = review_decision.reason
    data["intervention"] = _maybe_enqueue_voice(
        db=db,
        user_id=current_user.user_id,
        session_id=session.session_id,
        snap=snap,
        assistant_content=assistant_content,
        recent_messages=ctx.recent_messages,
        cooldown_is_active=cooldown_is_active,
        cooldown_seconds=cooldown_seconds,
        settings=settings,
    )
    return ok(data)


@router.post("/message/stream")
def send_message_stream(
    payload: ChatMessageRequest,
    request: Request,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    def event_stream():
        try:
            yield "event: status\ndata: " + json.dumps({"stage": "queued"}, ensure_ascii=False) + "\n\n"
            started_at = time.perf_counter()
            last_heartbeat = started_at
            settings = get_settings()
            limiter = get_rate_limiter()
            limiter.enforce_per_minute(
                key=f"chat:{current_user.user_id}",
                limit=settings.chat_rate_limit_per_minute,
                code="RATE_LIMIT_EXCEEDED",
                message="Cậu ơi, cậu dùng hết gói chat trial rùi nè, hãy đăng ký tài khoản để mình nói chuyện được lâu hơn nhé!",
            )
            last_heartbeat, hb = _build_heartbeat_event(
                started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_rate_limit"
            )
            if hb:
                yield hb

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
            last_heartbeat, hb = _build_heartbeat_event(
                started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_session_ready"
            )
            if hb:
                yield hb

            raw_text = payload.message
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
            session.message_count += 1
            session.last_message_at = now
            last_heartbeat, hb = _build_heartbeat_event(
                started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_user_saved"
            )
            if hb:
                yield hb

            ctx = load_chat_context_sync(
                db,
                session_id=session.session_id,
                user_id=current_user.user_id,
                message_limit=16,
                message_token_budget=1400,
            )
            last_heartbeat, hb = _build_heartbeat_event(
                started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_context_loaded"
            )
            if hb:
                yield hb
            previous_user_messages = [str(m.get("content") or "") for m in ctx.recent_messages if m.get("role") == "user"]
            if previous_user_messages and previous_user_messages[-1] == stored_user_content:
                previous_user_messages = previous_user_messages[:-1]

            sos, distress0 = decide_sos(raw_text, recent_user_messages=previous_user_messages)
            last_heartbeat, hb = _build_heartbeat_event(
                started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_safety_scored"
            )
            if hb:
                yield hb

            cooldown_is_active, cooldown_seconds = cooldown_active(
                user_id=current_user.user_id,
                session_id=session.session_id,
            )
            host = request.client.host if request.client else None

            if sos:
                snap = snapshot_for_sos(distress0)
                sos_count = db.scalar(
                    select(func.count(Message.message_id)).where(
                        Message.session_id == session.session_id,
                        Message.role == "assistant",
                        Message.sos_triggered == True,  # noqa: E712
                    )
                ) or 0
                assistant_content = assistant_text_for_sos(raw_text, sos_count)
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
                session.message_count += 1
                session.last_message_at = now
                _record_sos_side_effects(
                    db,
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                    context_summary=mask_pii(raw_text)[:500],
                    request_host=host,
                )
                db.commit()
                data = build_sos_chat_response_data(session.session_id, snap, assistant_text=assistant_content)
                data["intervention"] = _build_voice_intervention(
                    db=db,
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                    assistant_reply_for_tts=assistant_content,
                    snapshot=snap,
                    trigger_reason="sos_gate_forced",
                    rolling_window_turns=1,
                    delta_score=0.0,
                )
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                yield "event: status\ndata: " + json.dumps({"stage": "ready", "latency_ms": elapsed_ms}, ensure_ascii=False) + "\n\n"
                yield "event: final\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"
                return

            # Persist user turn before any potentially long-running LLM call.
            db.commit()

            # distress_score frozen after decide_sos() — mood is context for LangGraph, not a routing delta.
            distress = distress0

            message_hash = hash_message(
                raw_text,
                context_seed=f"{session.session_id}:{session.message_count}:{len(ctx.recent_messages)}",
            )
            turn = get_cached_turn(session.session_id, message_hash) if settings.chat_response_cache_ttl_seconds > 0 else None
            if turn is None:
                memory_ctx, compat_longterm = _load_memory_context_for_turn(
                    db,
                    user_id=current_user.user_id,
                    raw_text=raw_text,
                    recent_messages=ctx.recent_messages,
                    distress_score=distress,
                )
                last_heartbeat, hb = _build_heartbeat_event(
                    started_at=started_at, last_heartbeat_at=last_heartbeat, stage="pre_llm_memory_ready"
                )
                if hb:
                    yield hb
                yield "event: status\ndata: " + json.dumps({"stage": "model_stream_start"}, ensure_ascii=False) + "\n\n"
                for ev in stream_non_sos_turn_events(
                    user_message=raw_text,
                    recent_messages=ctx.recent_messages,
                    mood_today=ctx.mood_today,
                    distress_score=distress,
                    long_term_memories=(memory_ctx.recent_summaries if memory_ctx else compat_longterm),
                    mem0_facts=(memory_ctx.mem0_facts if memory_ctx else []),
                    user_traits=(memory_ctx.traits if memory_ctx else {}),
                    top_triggers=(memory_ctx.top_triggers if memory_ctx else []),
                    active_goals=(memory_ctx.active_goals if memory_ctx else []),
                    effective_coping=(memory_ctx.effective_coping if memory_ctx else []),
                    clinical_trajectory=(memory_ctx.clinical_trajectory if memory_ctx else ""),
                    persona_id=_active_persona_id(db, current_user.user_id),
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                ):
                    if ev.get("type") == "token":
                        yield "event: delta\ndata: " + json.dumps({"text": str(ev.get("text") or "")}, ensure_ascii=False) + "\n\n"
                    elif ev.get("type") == "final":
                        turn = ev.get("turn")
                if not turn:
                    raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504)
                set_cached_turn(
                    session.session_id,
                    message_hash,
                    turn,
                    ttl_seconds=settings.chat_response_cache_ttl_seconds,
                )

            snap = turn["session_fields"]
            assistant_content = turn["reply"]
            tone = turn["tone_cam_xuc"]
            goi_y = turn["goi_y_nhanh"]
            the_dinh = turn["the_dinh_kem"]
            routing_hist: list[str] = turn.get("routing_history") or []

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
            session.message_count += 1
            session.last_message_at = now
            persist_turn_memory(
                db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                user_message=raw_text,
                assistant_reply=assistant_content,
                sos_triggered=False,
            )
            review_decision = route_for_human_review(
                distress_score=snap.distress_score,
                sos_triggered=False,
                threshold=0.85,
            )
            if review_decision.requires_human_review:
                _queue_human_review(
                    db,
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                    distress_score=snap.distress_score,
                    message=raw_text,
                    host=host,
                )
            db.commit()
            threading.Thread(
                target=_enqueue_turn_mem0,
                args=(current_user.user_id, raw_text, assistant_content),
                daemon=True,
            ).start()

            vhint = None
            if snap.safety_tier == "voice_recommended":
                vhint = "Bạn có thể bấm gọi để nói chuyện trực tiếp với Friend / tổng đài — mình vẫn ở đây trong lúc bạn cân nhắc."

            data = build_normal_envelope(
                session.session_id,
                snap=snap,
                reply=assistant_content,
                tone_cam_xuc=tone,
                goi_y_nhanh=goi_y,
                the_dinh_kem=the_dinh,
                voice_hint=vhint,
                routing_history=routing_hist,
            )
            data["intervention"] = None
            if review_decision.requires_human_review:
                data["pending_human_review"] = True
                data["review_reason"] = review_decision.reason
            data["intervention"] = _maybe_enqueue_voice(
                db=db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                snap=snap,
                assistant_content=assistant_content,
                recent_messages=ctx.recent_messages,
                cooldown_is_active=cooldown_is_active,
                cooldown_seconds=cooldown_seconds,
                settings=settings,
            )

            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            yield "event: status\ndata: " + json.dumps({"stage": "ready", "latency_ms": elapsed_ms}, ensure_ascii=False) + "\n\n"
            yield "event: final\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"
        except AppError as exc:
            yield "event: error\ndata: " + json.dumps({"code": exc.code, "message": exc.message}, ensure_ascii=False) + "\n\n"
        except Exception as exc:
            logger.exception("chat stream failed: %s", exc)
            yield "event: error\ndata: " + json.dumps({"code": "STREAM_INTERNAL_ERROR", "message": "Lỗi stream phản hồi"}, ensure_ascii=False) + "\n\n"
        finally:
            # Ensure any uncommitted transaction is rolled back when the generator
            # exits — including mid-stream client disconnects that abandon the generator.
            try:
                db.rollback()
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/guest-message")
def send_guest_message(payload: GuestChatMessageRequest, _: None = Depends(require_csrf)):
    try:
        if payload.guest_session_id:
            try:
                alive = guest_heartbeat(payload.guest_session_id)
            except Exception as exc:
                logger.exception("guest heartbeat failed")
                raise AppError("GUEST_SESSION_ERROR", "Không thể kiểm tra phiên guest", 500) from exc
            if not alive:
                raise AppError(
                    "GUEST_TRIAL_EXPIRED",
                    "Phiên chat thử đã hết 2 phút. Vui lòng đăng ký để tiếp tục trò chuyện.",
                    403,
                )
            session_id = payload.guest_session_id
        else:
            try:
                session_id, _ = guest_start_session()
            except Exception as exc:
                logger.exception("guest session start failed")
                raise AppError("GUEST_SESSION_ERROR", "Không thể tạo phiên guest", 500) from exc

        raw_text = payload.message
        try:
            sos, distress = decide_sos(raw_text, recent_user_messages=[])
        except TypeError:
            # Backward-compatible path for tests/monkeypatches still using decide_sos(message).
            sos, distress = decide_sos(raw_text)
        if sos:
            snap = snapshot_for_sos(distress)
            data = build_sos_chat_response_data(session_id, snap)
            data["intervention"] = None
            return ok(data)

        try:
            turn = run_non_sos_turn(
                user_message=raw_text,
                recent_messages=[],
                mood_today=None,
                distress_score=distress,
                persona_id=DEFAULT_PERSONA_ID,
                session_id=session_id,
            )
        except Exception as exc:
            logger.exception("guest chat generation failed")
            raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504) from exc

        if not isinstance(turn, dict):
            raise AppError("SCHEMA_VALIDATION_FAILED", "Phản hồi guest không hợp lệ", 500)

        raw_snap = turn.get("session_fields")
        if isinstance(raw_snap, SafetySnapshot):
            snap = raw_snap
        elif isinstance(raw_snap, dict):
            snap = SafetySnapshot(
                distress_score=float(raw_snap.get("distress_score", distress)),
                risk_level=int(raw_snap.get("risk_level", 0)),
                safety_tier=str(raw_snap.get("safety_tier", "normal")),
                conversation_mode=str(raw_snap.get("conversation_mode", "normal")),
            )
        else:
            snap = SafetySnapshot(
                distress_score=float(distress),
                risk_level=0,
                safety_tier="normal",
                conversation_mode="normal",
            )

        assistant_content = str(turn.get("reply") or "")
        tone = str(turn.get("tone_cam_xuc") or "xac_nhan")
        goi_y = turn.get("goi_y_nhanh") if isinstance(turn.get("goi_y_nhanh"), list) else []
        the_dinh = turn.get("the_dinh_kem") if isinstance(turn.get("the_dinh_kem"), list) else []
        routing_hist: list[str] = turn.get("routing_history") if isinstance(turn.get("routing_history"), list) else []

        data = build_normal_envelope(
            session_id,
            snap=snap,
            reply=assistant_content,
            tone_cam_xuc=tone,
            goi_y_nhanh=goi_y,
            the_dinh_kem=the_dinh,
            voice_hint=None,
            routing_history=routing_hist,
        )
        data["intervention"] = None
        return ok(data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("guest message failed unexpectedly")
        raise AppError("SCHEMA_VALIDATION_FAILED", "Đã xảy ra lỗi nội bộ", 500) from exc


@router.get("/voice-jobs/{tts_job_id}")
def get_voice_job_status(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_voice_job(db, tts_job_id)
    if not job or job.get("user_id") != current_user.user_id:
        raise AppError("VOICE_JOB_NOT_FOUND", "Voice job không tồn tại", 404)
    return ok({k: v for k, v in job.items() if k != "user_id"})


@router.get("/voice-jobs/{tts_job_id}/events")
async def stream_voice_job_events(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job_check = get_voice_job(db, tts_job_id)
    if not job_check or job_check.get("user_id") != current_user.user_id:
        raise AppError("VOICE_JOB_NOT_FOUND", "Voice job không tồn tại", 404)

    async def event_stream():
        previous_status = None
        for _ in range(30):
            job = get_voice_job(db, tts_job_id)
            if not job:
                yield "event: error\ndata: {\"code\":\"VOICE_JOB_NOT_FOUND\"}\n\n"
                return
            status = job.get("status")
            if status != previous_status:
                safe_job = {k: v for k, v in job.items() if k != "user_id"}
                payload = json.dumps(safe_job, ensure_ascii=False)
                yield f"event: status\ndata: {payload}\n\n"
                previous_status = status
            if status in {"ready", "failed", "done", "synced"}:
                return
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/voice-jobs/{tts_job_id}/audio")
def get_voice_job_audio(
    tts_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_voice_job(db, tts_job_id)
    if not job or job.get("user_id") != current_user.user_id:
        raise AppError("VOICE_AUDIO_NOT_READY", "Audio chưa sẵn sàng", 404)
    audio_path = get_voice_audio_path(db, tts_job_id)
    if not audio_path:
        raise AppError("VOICE_AUDIO_NOT_READY", "Audio chưa sẵn sàng", 404)
    media_type = mimetypes.guess_type(str(audio_path))[0] or "application/octet-stream"
    return FileResponse(path=audio_path, media_type=media_type, filename=audio_path.name)


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
