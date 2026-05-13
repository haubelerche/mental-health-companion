import logging
import asyncio
import json
import mimetypes
import threading
import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    ensure_policy_acknowledged,
    ensure_policy_acknowledged_for_stream,
    get_current_user,
    get_current_user_for_stream,
    require_csrf,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import ok
from app.services.db.models import AdminAuditLog, Conversation, CrisisLog, Message, NutritionMealCheckin, User, UserProfile
from app.services.risk_writer import record_risk_inference, record_session_risk_snapshot
from app.services.db.session import get_db, get_session_factory
from app.services.schemas.payloads import ChatEndRequest, ChatMessageRequest, GuestChatMessageRequest
from app.services.chat_context import load_chat_context_sync
from app.services.chat_response_cache import get_cached_turn, hash_message, set_cached_turn
from app.services.confidence_router import route_for_human_review
from app.services.guest_service import heartbeat as guest_heartbeat
from app.services.guest_service import start_session as guest_start_session
from app.services.langfuse_tracing import ChatTurnTracer, set_active_tracer
from app.services.langgraph_chat import build_normal_envelope, run_non_sos_turn, stream_non_sos_turn_events
from app.services.longterm_memory import (
    UserMemoryContext,
    build_user_memory_context,
    get_user_longterm_memories,
    persist_turn_memory,
)
from app.services.mem0_service import MemoryManager
from app.safety.output_validator import validate_output as _validate_tts_output
from app.services.pii_mask import mask_pii
from app.services.rate_limit import get_rate_limiter
from app.services.session_summary import close_session_summary
from app.services.sos_handler import (
    assistant_text_for_sos,
    build_sos_chat_response_data,
    decide_sos,
    decide_sos_debug,
    heuristic_distress,
    is_alone_signal,
    snapshot_for_sos,
)
from app.services.crisis_intervention_planner import (
    build_fallback_plan,
    build_fallback_crisis_plan,
    build_llm_crisis_plan,
)
from app.services.clinical_profile import get_or_create_clinical_profile
from app.services.safety_scoring import SafetySnapshot, compute_escalation_signal
from app.services.proactive_voice import (
    cooldown_active,
    enqueue_voice_job,
    get_voice_audio_path,
    get_voice_job,
    mark_cooldown,
    message_suggests_proactive_voice,
)
from app.services.voice_consent import get_voice_consent
from app.services.voice_message_planner import intent_title
from app.services.voice_policy import VoiceMessagePolicyEngine, VoicePolicyContext
from app.services.utils import make_id, get_now
from app.voice.types import TTS_TERMINAL_STATUSES
from app.personas.router import route_persona
from app.personas.greetings import persona_chat_greeting_text
from app.services.persona_unlock_persistence import is_persona_unlocked
from app.services.meme_selector import maybe_select_meme_suggestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_AUDIT_ADMIN = "sys_auto"
DEFAULT_PERSONA_ID = "dung_luong"


def _mark_stage(latency_map: dict[str, int], stage: str, started_at: float) -> None:
    latency_map[stage] = int((time.perf_counter() - started_at) * 1000)


def _build_heartbeat_event(*, started_at: float, last_heartbeat_at: float, stage: str, interval_seconds: float = 0.4):
    now = time.perf_counter()
    if now - last_heartbeat_at < interval_seconds:
        return last_heartbeat_at, None
    payload = {
        "stage": stage,
        "elapsed_ms": int((now - started_at) * 1000),
    }
    return now, "event: heartbeat\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def _enqueue_turn_mem0(
    user_id: str,
    raw_text: str,
    assistant_text: str,
    *,
    user_name: str | None = None,
) -> None:
    """Persist recent turn to Mem0 without blocking the API response path."""
    try:
        MemoryManager.instance().add_session(
            user_id=user_id,
            messages=[
                {"role": "user", "content": mask_pii(raw_text)},
                {"role": "assistant", "content": mask_pii(assistant_text)},
            ],
            user_name=user_name,
        )
    except Exception as exc:  # pragma: no cover - fail-safe
        logger.warning("mem0 turn add failed for %s: %s", user_id, exc)


def _active_persona_id(db: Session, user_id: str, *, distress: float = 0.0) -> str:
    if not hasattr(db, "scalar"):
        return DEFAULT_PERSONA_ID
    try:
        profile_row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    except Exception:
        return DEFAULT_PERSONA_ID
    profile_data = dict(profile_row.profile or {}) if profile_row else {}
    persona_data = dict(profile_data.get("persona") or {})
    selected = str(persona_data.get("selected") or "").strip()
    requested = selected or DEFAULT_PERSONA_ID
    unlocked = is_persona_unlocked(db, user_id=user_id, persona_id=requested) if requested != DEFAULT_PERSONA_ID else True
    decision = route_persona(
        current_persona_id=DEFAULT_PERSONA_ID,
        requested_persona_id=requested if requested != DEFAULT_PERSONA_ID else None,
        distress=distress,
        sos_triggered=False,
        is_unlocked=unlocked,
    )
    return decision.target_persona_id


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
            severity_level="high",
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
    clin.last_scored_at = get_now().replace(tzinfo=None)

    record_risk_inference(
        db,
        user_id=user_id,
        session_id=session_id,
        inferred_signal="sos_keyword_detected",
        score=1.0,
        detail={"source": "safety_gate", "host": request_host},
    )
    record_session_risk_snapshot(
        db,
        session_id=session_id,
        user_id=user_id,
        risk_score=1.0,
        intent_severity=1.0,
        intent_immediacy=1.0,
        crisis_mode=True,
        escalation_flag=True,
        components={"trigger": "sos_keyword"},
        source="sos_override",
    )


def _queue_human_review(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    distress_score: float,
    message: str,
    host: str | None,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    row = CrisisLog(
        log_id=make_id("cl"),
        session_id=session_id,
        user_id=user_id,
        severity_level="high",
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
    record_risk_inference(
        db,
        user_id=user_id,
        session_id=session_id,
        inferred_signal="high_distress_review",
        score=float(distress_score),
        detail={"source": "confidence_router", "host": host},
    )
    record_session_risk_snapshot(
        db,
        session_id=session_id,
        user_id=user_id,
        risk_score=float(distress_score),
        intent_severity=float(distress_score),
        escalation_flag=True,
        components={"trigger": "high_distress_threshold"},
        source="supervisor",
    )

    # Push real-time notification for high distress
    try:
        from app.services.notification_service import send_instant_notification
        send_instant_notification(
            db,
            user_id=user_id,
            event_type="crisis.detected",
            payload={
                "level": "high_distress",
                "distress_score": distress_score,
                "message": "Cậu đang cảm thấy bất ổn phải không? Mình luôn ở đây lắng nghe nhé."
            },
            background_tasks=background_tasks
        )
    except Exception:
        pass



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


def _load_today_meals(db: Session, user_id: str) -> list[dict]:
    try:
        rows = db.scalars(
            select(NutritionMealCheckin)
            .where(NutritionMealCheckin.user_id == user_id)
            .where(NutritionMealCheckin.meal_date == date.today())
            .order_by(NutritionMealCheckin.meal_slot)
        ).all()
        return [
            {"slot": r.meal_slot, "items": r.items_text, "mood_before": r.mood_before, "mood_after": r.mood_after}
            for r in rows
        ]
    except Exception as exc:
        logger.debug("meal load failed for %s: %s", user_id, exc)
        return []


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
    voice_script: str,
    snapshot,
    trigger_reason: str,
    rolling_window_turns: int,
    delta_score: float,
    voice_scripts: list[str] | None = None,
) -> dict:
    """Build a voice intervention from an explicit TTS-only script."""
    tts_cfg = get_settings()
    requested_tts = str(getattr(tts_cfg, "tts_provider", "elevenlabs") or "elevenlabs").lower()
    _trigger_snapshot = {
        "distress_score": snapshot.distress_score,
        "risk_level": snapshot.risk_level,
        "safety_tier": snapshot.safety_tier,
        "rolling_window_turns": rolling_window_turns,
        "delta_score": delta_score,
    }

    scripts_to_enqueue: list[str] = [s for s in (voice_scripts or []) if s and s.strip()]
    if not scripts_to_enqueue:
        scripts_to_enqueue = [(voice_script or "").strip()]

    voice_jobs: list[dict] = []
    for script in scripts_to_enqueue:
        _tts_verdict = _validate_tts_output(script, surface="tts")
        if _tts_verdict.is_blocked:
            logger.warning(
                "SafetyOutputValidator blocked TTS script for user=%s: %s",
                user_id,
                _tts_verdict.reason_codes,
            )
            voice_jobs.append({"tts_job_id": None, "blocked": True, "reason": _tts_verdict.reason_codes})
            continue
        job = enqueue_voice_job(
            db,
            user_id=user_id,
            session_id=session_id,
            voice_script=script,
            trigger_reason=trigger_reason,
            trigger_snapshot=_trigger_snapshot,
        )
        voice_jobs.append(job)

    mark_cooldown(user_id=user_id, session_id=session_id)

    primary_voice = voice_jobs[0] if voice_jobs else {}
    primary_script = scripts_to_enqueue[0] if scripts_to_enqueue else (voice_script or "").strip()

    return {
        "type": "proactive_voice",
        "trigger_reason": trigger_reason,
        "trigger_snapshot": _trigger_snapshot,
        "cooldown": {"active": False, "seconds_remaining": 0},
        "requested_tts_provider": requested_tts,
        "voice": primary_voice,
        "voice_script": primary_script,
        "voice_script_hash": primary_voice.get("voice_script_hash") or primary_voice.get("event_signature"),
        "tts_job_id": primary_voice.get("tts_job_id"),
        "voice_status": primary_voice.get("status"),
        "voice_job_ids": [j.get("tts_job_id") for j in voice_jobs if j.get("tts_job_id")],
        "voice_jobs": voice_jobs,
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


def _client_payload_for_terminal_policy(reason: str, *, risk_mode: str) -> dict:
    status = "provider_disabled" if reason == "provider_disabled" else "cancelled"
    return {
        "id": f"{risk_mode}_voice_unavailable",
        "intent": "sos_grounding" if risk_mode == "sos" else "elevated_encouragement",
        "title": "Tin nhan thoai tam chua san sang",
        "status": status,
        "tts_job_id": None,
        "audio_url": None,
        "error_code": reason,
    }


def _enqueue_voice_policy(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    persona_id: str | None,
    decision,
    snap,
    trigger_reason: str,
    rolling_window_turns: int = 1,
    delta_score: float = 0.0,
) -> dict:
    """Enqueue backend-approved voice plans and build client payloads.

    The visible text has already been committed; TTS queueing must remain a
    non-blocking attachment path from the frontend's perspective.
    """
    trigger_snapshot = {
        "distress_score": snap.distress_score,
        "risk_level": snap.risk_level,
        "safety_tier": snap.safety_tier,
        "rolling_window_turns": rolling_window_turns,
        "delta_score": delta_score,
        "risk_mode": decision.risk_mode,
    }
    client_messages: list[dict] = []
    voice_jobs: list[dict] = []

    if decision.should_attach_voice:
        for plan in decision.voice_messages:
            _tts_verdict = _validate_tts_output(plan.voice_script, surface="tts")
            if _tts_verdict.is_blocked:
                client_messages.append({
                    "id": plan.id,
                    "intent": plan.intent,
                    "title": intent_title(str(plan.intent)),
                    "status": "failed",
                    "tts_job_id": None,
                    "audio_url": None,
                    "error_code": ",".join(_tts_verdict.reason_codes),
                })
                continue
            job = enqueue_voice_job(
                db,
                user_id=user_id,
                session_id=session_id,
                voice_script=plan.voice_script,
                trigger_reason=trigger_reason,
                trigger_snapshot=trigger_snapshot,
                persona_id=persona_id,
                risk_mode=decision.risk_mode,
                voice_intent=str(plan.intent),
                priority=plan.priority,
            )
            voice_jobs.append(job)
            client_messages.append({
                "id": plan.id,
                "intent": plan.intent,
                "title": intent_title(str(plan.intent)),
                "status": job.get("status") or "queued",
                "tts_job_id": job.get("tts_job_id"),
                "audio_url": job.get("audio_url"),
                "error_code": job.get("error_code"),
            })
        if voice_jobs:
            mark_cooldown(user_id=user_id, session_id=session_id)
    elif decision.risk_mode == "sos":
        terminal_reason = next((r for r in decision.reason_codes if r in {"provider_disabled", "user_voice_disabled"}), "voice_policy_skipped")
        client_messages.append(_client_payload_for_terminal_policy(terminal_reason, risk_mode=decision.risk_mode))

    policy_payload = {
        "should_attach_voice": decision.should_attach_voice,
        "risk_mode": decision.risk_mode,
        "ordinary_cooldown_bypassed": decision.ordinary_cooldown_bypassed,
        "reason_codes": decision.reason_codes,
        "voice_messages": client_messages,
    }

    primary_voice = voice_jobs[0] if voice_jobs else (client_messages[0] if client_messages else {})
    intervention = None
    if client_messages:
        intervention = {
            "type": "proactive_voice",
            "trigger_reason": trigger_reason,
            "trigger_snapshot": trigger_snapshot,
            "cooldown": {"active": False, "seconds_remaining": 0},
            "voice": primary_voice,
            "tts_job_id": primary_voice.get("tts_job_id"),
            "voice_status": primary_voice.get("status"),
            "voice_job_ids": [m.get("tts_job_id") for m in client_messages if m.get("tts_job_id")],
            "voice_jobs": voice_jobs,
        }
    return {"voice_policy": policy_payload, "intervention": intervention}


def _maybe_enqueue_voice(
    *,
    db: Session,
    user_id: str,
    session_id: str,
    snap,
    assistant_content: str,
    user_message: str,
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
    keyword_voice = message_suggests_proactive_voice(str(user_message or ""))
    # Avoid TTS on casual mentions; combine keywords with a modest distress floor.
    keyword_distress_floor = 0.48
    should_voice = (
        signal.escalate
        or final_distress >= auto_thr
        or (keyword_voice and final_distress >= keyword_distress_floor)
    )
    if not should_voice:
        return None
    if cooldown_is_active:
        return {
            "type": "proactive_voice",
            "trigger_reason": "cooldown_active",
            "cooldown": {"active": True, "seconds_remaining": cooldown_seconds},
            "voice": {"status": "cooldown", "tts_job_id": None, "audio_url": None},
        }
    if signal.escalate:
        trigger_reason = signal.trigger_reason
    elif final_distress >= auto_thr:
        trigger_reason = "distress_auto_voice"
    else:
        trigger_reason = "keyword_intensity_voice"
    return _build_voice_intervention(
        db=db,
        user_id=user_id,
        session_id=session_id,
        voice_script=assistant_content,
        snapshot=snap,
        trigger_reason=trigger_reason,
        rolling_window_turns=signal.rolling_window_turns,
        delta_score=signal.delta_score,
    )


def _compact_recommendation_attachments(items: list[dict] | None) -> list[dict]:
    """Normalize recommendation cards so frontend can render a compact layout."""
    if not items:
        return []
    compact: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        item_type = str(item.get("type") or "").strip().lower()
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        if len(title) > 48:
            title = title[:45].rstrip() + "..."
        if len(description) > 90:
            description = description[:87].rstrip() + "..."
        item["type"] = item_type or "resource"
        item["title"] = title or "Gợi ý cho bạn"
        item["description"] = description or None
        compact.append(item)
    return compact


_PERSONA_GREETINGS: dict[str, str] = {
    "ban_than": "Wassupp, hôm nay cậu ổn không? Tui luôn ở đây lắng nghe chia sẻ của cậu.",
    "dat_le": "Chào em, hôm nay em có điều gì muốn kể cho thầy nghe không?",
    "cun": "Gâu Gâu! cục vàng của sen yêu đây! Hôm nay sen có chuyện gì muốn kể cho cún nghe không? 🐾",
    "meo": "Mèo méooo~ Hôm nay sen lèm sao? Có gì vui kể cho hoàng thượng nghe không? 🐱",
    "crush": "Hey, mình ở đây rồi. Hôm nay bạn thế nào? 💬",
}


@router.get("/greeting")
def get_greeting(
    persona_id: str = Query(default="dung_luong"),
    current_user: User = Depends(get_current_user),
) -> dict:
    pid = persona_id.strip() or DEFAULT_PERSONA_ID
    text = persona_chat_greeting_text(pid)
    return ok({"text": text, "persona_id": pid})


@router.post("/message")
def send_message(
    payload: ChatMessageRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(ensure_policy_acknowledged),
    db: Session = Depends(get_db),
):
    request_started = time.perf_counter()
    stage_started = request_started
    latency_trace: dict[str, int] = {}
    settings = get_settings()
    _mark_stage(latency_trace, "backend_request_parse_ms", stage_started)
    stage_started = time.perf_counter()
    limiter = get_rate_limiter()
    limiter.enforce_per_minute(
        key=f"chat:{current_user.user_id}",
        limit=settings.chat_rate_limit_per_minute,
        code="RATE_LIMIT_EXCEEDED",
        message="Cậu ơi, cậu dùng hết gói chat trial rùi nè, hãy đăng ký tài khoản để mình nói chuyện được lâu hơn nhé!",
    )
    _mark_stage(latency_trace, "auth_or_session_load_ms", stage_started)
    stage_started = time.perf_counter()

    now = get_now().replace(tzinfo=None)
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
    _sos_debug = decide_sos_debug(raw_text, recent_user_messages=previous_user_messages)
    sos, distress0 = _sos_debug.sos_triggered, _sos_debug.distress_score
    _mark_stage(latency_trace, "safety_gate_ms", stage_started)
    stage_started = time.perf_counter()
    cooldown_is_active, cooldown_seconds = cooldown_active(
        user_id=current_user.user_id,
        session_id=session.session_id,
    )

    host = request.client.host if request.client else None

    if sos:
        safety_tracer = ChatTurnTracer(
            correlation_id=make_id("trace"),
            user_id=current_user.user_id,
            session_id=session.session_id,
            input_meta={
                "agent": "safety",
                "sos_path": True,
                "user_message_len": len(raw_text),
                "recent_user_message_count": len(previous_user_messages),
            },
        )
        set_active_tracer(safety_tracer)
        snap = snapshot_for_sos(distress0)
        try:
            safety_tracer.guardrail(
                "safety_gate",
                input_data={"user_message_len": len(raw_text), "recent_user_message_count": len(previous_user_messages)},
                output_data={
                    "sos_triggered": True,
                    "distress_score": float(distress0),
                    "risk_level": int(snap.risk_level),
                    "safety_tier": str(snap.safety_tier),
                    "reason_codes": list(getattr(_sos_debug, "reason_codes", []) or []),
                },
                metadata={"agent": "safety", "route": "sos_bypass"},
            )
            sos_count = db.scalar(
                select(func.count(Message.message_id)).where(
                    Message.session_id == session.session_id,
                    Message.role == "assistant",
                    Message.sos_triggered == True,  # noqa: E712
                )
            ) or 0
            _is_alone = is_alone_signal(raw_text)
            _settings = get_settings()
            crisis_plan_base = build_fallback_crisis_plan(
                is_alone=_is_alone,
                session_sos_count=sos_count,
                reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
            )
            try:
                crisis_plan = asyncio.run(build_llm_crisis_plan(
                    user_message=raw_text,
                    session_sos_count=sos_count,
                    is_alone=_is_alone,
                    openai_api_key=_settings.openai_api_key,
                ))
                # Always use curated action_cards and safety codes from deterministic base
                crisis_plan = crisis_plan.model_copy(update={
                    "action_cards": crisis_plan_base.action_cards,
                    "safety_reason_codes": crisis_plan_base.safety_reason_codes,
                    "should_enqueue_voice": crisis_plan_base.should_enqueue_voice,
                })
                safety_tracer.generation(
                    "safety_crisis_enrichment",
                    model="gpt-4o-mini",
                    input_messages=[{"role": "user", "content": {"message_len": len(raw_text), "is_alone": _is_alone}}],
                    output="crisis_plan_llm",
                    metadata={"agent": "safety", "session_sos_count": int(sos_count or 0)},
                )
            except Exception as _exc:
                logger.warning("LLM crisis plan failed, using base plan: %s", _exc)
                crisis_plan = crisis_plan_base
            assistant_msg = Message(
                message_id=make_id("msg"),
                session_id=session.session_id,
                user_id=current_user.user_id,
                role="assistant",
                content=crisis_plan.visible_text,
                assistant_tone=None,
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
            data = build_sos_chat_response_data(session.session_id, snap, assistant_text=crisis_plan.visible_text)
            data["voice_script"] = crisis_plan.voice_script
            data["crisis_plan"] = crisis_plan.model_dump()
            if settings.chat_expose_scoring_debug:
                data["scoring_debug"] = _sos_debug.model_dump()
            voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
                user_id=current_user.user_id,
                session_id=session.session_id,
                distress_score=float(distress0),
                safety_tier=str(snap.safety_tier),
                sos_triggered=True,
                cooldown_active=cooldown_is_active,
                cooldown_seconds_remaining=cooldown_seconds,
                user_voice_enabled=get_voice_consent(db, current_user.user_id),
                provider_enabled=True,
                current_turn_has_emotional_weight=True,
                purely_technical_turn=False,
                visible_text=crisis_plan.visible_text,
                reason_codes=tuple(getattr(_sos_debug, "reason_codes", []) or []),
            ))
            voice_result = _enqueue_voice_policy(
                db=db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                persona_id=DEFAULT_PERSONA_ID,
                decision=voice_decision,
                snap=snap,
                trigger_reason="sos_gate_forced",
                rolling_window_turns=1,
                delta_score=0.0,
            )
            data["voice_policy"] = voice_result["voice_policy"]
            data["intervention"] = voice_result["intervention"]
            _mark_stage(latency_trace, "tts_enqueue_ms", stage_started)
            latency_trace["total_backend_ms"] = int((time.perf_counter() - request_started) * 1000)
            latency_trace["total_frontend_visible_latency_ms"] = latency_trace["total_backend_ms"]
            data["latency_trace"] = latency_trace
            safety_tracer.score("distress_score", distress0, comment="sos_gate_forced")
            safety_tracer.update_output(
                crisis_plan.visible_text,
                metadata={
                    "routing_history": ["safety"],
                    "crisis_plan_source": crisis_plan.source,
                    "latency_trace": latency_trace,
                },
            )
            return ok(data)
        finally:
            safety_tracer.flush()
            set_active_tracer(None)

    # Persist user turn before calling LLM to release DB connection back to pool.
    db.commit()

    # distress_score frozen after decide_sos() — mood is context for LangGraph, not a routing delta.
    distress = distress0
    selected_persona_id = _active_persona_id(db, current_user.user_id, distress=distress)

    turn = None
    message_hash = hash_message(raw_text, context_seed=f"{session.session_id}:{session.message_count}:{len(ctx.recent_messages)}")
    if settings.chat_response_cache_ttl_seconds > 0:
        turn = get_cached_turn(session.session_id, message_hash)

    if turn is None:
        try:
            memory_started = time.perf_counter()
            memory_ctx, compat_longterm = _load_memory_context_for_turn(
                db,
                user_id=current_user.user_id,
                raw_text=raw_text,
                recent_messages=ctx.recent_messages,
                distress_score=distress,
            )
            _mark_stage(latency_trace, "memory_load_ms", memory_started)
            llm_started = time.perf_counter()
            # Keep request path low-latency: avoid synchronous Neo4j prefetch here.
            _graph_patterns: dict = {}
            _nutrition_meals = _load_today_meals(db, current_user.user_id)
            _base_traits = dict(memory_ctx.traits if memory_ctx else {})
            if memory_ctx and memory_ctx.onboarding:
                _base_traits.setdefault("onboarding", memory_ctx.onboarding)
            turn = run_non_sos_turn(
                user_message=raw_text,
                recent_messages=ctx.recent_messages,
                mood_today=ctx.mood_today,
                distress_score=distress,
                long_term_memories=(memory_ctx.recent_summaries if memory_ctx else compat_longterm),
                mem0_facts=(memory_ctx.mem0_facts if memory_ctx else []),
                user_traits=_base_traits,
                top_triggers=(memory_ctx.top_triggers if memory_ctx else []),
                active_goals=(memory_ctx.active_goals if memory_ctx else []),
                effective_coping=(memory_ctx.effective_coping if memory_ctx else []),
                clinical_trajectory=(memory_ctx.clinical_trajectory if memory_ctx else ""),
                persona_id=selected_persona_id,
                user_id=current_user.user_id,
                session_id=session.session_id,
                active_memory_text="",
                graph_patterns=_graph_patterns,
                nutrition_meals=_nutrition_meals or None,
            )
            _mark_stage(latency_trace, "friend_llm_call_ms", llm_started)
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
    tone = turn["assistant_tone"]
    goi_y = turn["goi_y_nhanh"] #gợi ý
    the_dinh = _compact_recommendation_attachments(turn["the_dinh_kem"])
    routing_hist: list[str] = turn.get("routing_history") or []

    assistant_msg = Message(
        message_id=make_id("msg"),
        session_id=session.session_id,
        user_id=current_user.user_id,
        role="assistant",
        content=mask_pii(assistant_content),
        assistant_tone=tone if tone in ("supportive", "validating", "cheerful", "calming", "mentor", "neutral") else "validating",
        sos_triggered=False,
        created_at=now,
    )
    db.add(assistant_msg)
    session.message_count += 1
    session.last_message_at = now
    try:
        persist_turn_memory(
            db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            user_message=raw_text,
            assistant_reply=assistant_content,
            sos_triggered=False,
        )
    except Exception as exc:  # pragma: no cover - fail-open persistence path
        logger.warning("turn memory persistence failed for %s: %s", current_user.user_id, exc)
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
            background_tasks=background_tasks,
        )
    db.commit()
    threading.Thread(
        target=_enqueue_turn_mem0,
        args=(current_user.user_id, raw_text, assistant_content),
        kwargs={
            "user_name": str(getattr(current_user, "display_name", None) or "bạn"),
        },
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
        assistant_tone=tone,
        goi_y_nhanh=goi_y,
        the_dinh_kem=the_dinh,
        voice_hint=vhint,
        routing_history=routing_hist,
    )
    data["intervention"] = None
    if review_decision.requires_human_review:
        data["pending_human_review"] = True
        data["review_reason"] = review_decision.reason
    distress_for_voice = float(snap.distress_score)
    history_for_voice = _recent_distress_history(ctx.recent_messages, max_turns=settings.proactive_voice_window_turns)
    signal_for_voice = compute_escalation_signal(
        current_distress=distress_for_voice,
        previous_distress=history_for_voice,
        threshold=settings.proactive_voice_threshold,
        delta_threshold=settings.proactive_voice_delta_threshold,
        window_turns=settings.proactive_voice_window_turns,
    )
    keyword_voice = message_suggests_proactive_voice(str(raw_text or ""))
    emotional_weight = (
        distress_for_voice >= 0.55
        or signal_for_voice.escalate
        or keyword_voice
        or any(k in str(raw_text or "").lower() for k in ("buon", "met", "lo", "stress", "ap luc", "khong on"))
    )
    purely_technical = any(k in str(raw_text or "").lower() for k in ("api", "code", "bug", "deploy", "database")) and distress_for_voice < 0.55
    voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
        user_id=current_user.user_id,
        session_id=session.session_id,
        distress_score=distress_for_voice,
        safety_tier=str(snap.safety_tier),
        sos_triggered=False,
        cooldown_active=cooldown_is_active,
        cooldown_seconds_remaining=cooldown_seconds,
        user_voice_enabled=get_voice_consent(db, current_user.user_id),
        provider_enabled=True,
        current_turn_has_emotional_weight=emotional_weight,
        purely_technical_turn=purely_technical,
        visible_text=assistant_content,
        reason_codes=tuple([signal_for_voice.trigger_reason] if signal_for_voice.escalate else []),
    ))
    meme_suggestion = maybe_select_meme_suggestion(
        persona_id=selected_persona_id,
        safety_tier=str(snap.safety_tier),
        distress_score=float(snap.distress_score),
        session_id=session.session_id,
        assistant_turn_index=int(session.message_count),
        user_message=str(raw_text or ""),
        assistant_text=str(assistant_content or ""),
    )
    if meme_suggestion:
        data["meme_suggestion"] = meme_suggestion

    voice_result = _enqueue_voice_policy(
        db=db,
        user_id=current_user.user_id,
        session_id=session.session_id,
        persona_id=selected_persona_id,
        decision=voice_decision,
        snap=snap,
        trigger_reason=signal_for_voice.trigger_reason if signal_for_voice.escalate else f"{voice_decision.risk_mode}_voice_policy",
        rolling_window_turns=signal_for_voice.rolling_window_turns,
        delta_score=signal_for_voice.delta_score,
    )
    data["voice_policy"] = voice_result["voice_policy"]
    data["intervention"] = voice_result["intervention"]
    _mark_stage(latency_trace, "tts_enqueue_ms", stage_started)
    latency_trace.setdefault("memory_load_ms", 0)
    latency_trace.setdefault("friend_llm_call_ms", 0)
    latency_trace.setdefault("persona_router_ms", 0)
    latency_trace.setdefault("unlock_gate_ms", 0)
    latency_trace.setdefault("vietnamese_style_controller_ms", 0)
    latency_trace.setdefault("response_planner_ms", 0)
    latency_trace.setdefault("analyst_agent_ms", 0)
    latency_trace.setdefault("safety_output_validator_ms", 0)
    latency_trace.setdefault("db_write_ms", 0)
    latency_trace.setdefault("frontend_send_to_backend_ms", 0)
    latency_trace["total_backend_ms"] = int((time.perf_counter() - request_started) * 1000)
    latency_trace["total_frontend_visible_latency_ms"] = latency_trace["total_backend_ms"]
    data["latency_trace"] = latency_trace
    logger.info("chat.latency_trace user_id=%s session_id=%s trace=%s", current_user.user_id, session.session_id, latency_trace)
    return ok(data)


@router.post("/message/stream")
def send_message_stream(
    payload: ChatMessageRequest,
    request: Request,
    current_user: User = Depends(ensure_policy_acknowledged_for_stream),
):
    def event_stream():
        db: Session | None = get_session_factory()()
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

            now = get_now().replace(tzinfo=None)
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

            _sos_debug = decide_sos_debug(raw_text, recent_user_messages=previous_user_messages)
            sos, distress0 = _sos_debug.sos_triggered, _sos_debug.distress_score
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
                safety_tracer = ChatTurnTracer(
                    correlation_id=make_id("trace"),
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                    input_meta={
                        "agent": "safety",
                        "sos_path": True,
                        "stream": True,
                        "user_message_len": len(raw_text),
                        "recent_user_message_count": len(previous_user_messages),
                    },
                )
                set_active_tracer(safety_tracer)
                snap = snapshot_for_sos(distress0)
                try:
                    safety_tracer.guardrail(
                        "safety_gate",
                        input_data={"user_message_len": len(raw_text), "recent_user_message_count": len(previous_user_messages), "stream": True},
                        output_data={
                            "sos_triggered": True,
                            "distress_score": float(distress0),
                            "risk_level": int(snap.risk_level),
                            "safety_tier": str(snap.safety_tier),
                            "reason_codes": list(getattr(_sos_debug, "reason_codes", []) or []),
                        },
                        metadata={"agent": "safety", "route": "sos_stream_bypass"},
                    )
                    sos_count = db.scalar(
                        select(func.count(Message.message_id)).where(
                            Message.session_id == session.session_id,
                            Message.role == "assistant",
                            Message.sos_triggered == True,  # noqa: E712
                        )
                    ) or 0
                    _is_alone = is_alone_signal(raw_text)
                    _settings = get_settings()
                    _crisis_plan_base = build_fallback_crisis_plan(
                        is_alone=_is_alone,
                        session_sos_count=sos_count,
                        reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                    )
                    try:
                        crisis_plan = asyncio.run(build_llm_crisis_plan(
                            user_message=raw_text,
                            session_sos_count=sos_count,
                            is_alone=_is_alone,
                            openai_api_key=_settings.openai_api_key,
                        ))
                        crisis_plan = crisis_plan.model_copy(update={
                            "action_cards": _crisis_plan_base.action_cards,
                            "safety_reason_codes": _crisis_plan_base.safety_reason_codes,
                            "should_enqueue_voice": _crisis_plan_base.should_enqueue_voice,
                        })
                        safety_tracer.generation(
                            "safety_crisis_enrichment",
                            model="gpt-4o-mini",
                            input_messages=[{"role": "user", "content": {"message_len": len(raw_text), "is_alone": _is_alone, "stream": True}}],
                            output="crisis_plan_llm",
                            metadata={"agent": "safety", "session_sos_count": int(sos_count or 0), "stream": True},
                        )
                    except Exception as _exc:
                        logger.warning("LLM crisis plan failed, using base plan: %s", _exc)
                        crisis_plan = _crisis_plan_base
                    assistant_msg = Message(
                        message_id=make_id("msg"),
                        session_id=session.session_id,
                        user_id=current_user.user_id,
                        role="assistant",
                        content=crisis_plan.visible_text,
                        assistant_tone=None,
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
                    data = build_sos_chat_response_data(session.session_id, snap, assistant_text=crisis_plan.visible_text)
                    data["voice_script"] = crisis_plan.voice_script
                    data["crisis_plan"] = crisis_plan.model_dump()
                    if settings.chat_expose_scoring_debug:
                        data["scoring_debug"] = _sos_debug.model_dump()
                    voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
                        user_id=current_user.user_id,
                        session_id=session.session_id,
                        distress_score=float(distress0),
                        safety_tier=str(snap.safety_tier),
                        sos_triggered=True,
                        cooldown_active=cooldown_is_active,
                        cooldown_seconds_remaining=cooldown_seconds,
                        user_voice_enabled=get_voice_consent(db, current_user.user_id),
                        provider_enabled=True,
                        current_turn_has_emotional_weight=True,
                        purely_technical_turn=False,
                        visible_text=crisis_plan.visible_text,
                        reason_codes=tuple(getattr(_sos_debug, "reason_codes", []) or []),
                    ))
                    voice_result = _enqueue_voice_policy(
                        db=db,
                        user_id=current_user.user_id,
                        session_id=session.session_id,
                        persona_id=DEFAULT_PERSONA_ID,
                        decision=voice_decision,
                        snap=snap,
                        trigger_reason="sos_gate_forced",
                        rolling_window_turns=1,
                        delta_score=0.0,
                    )
                    data["voice_policy"] = voice_result["voice_policy"]
                    data["intervention"] = voice_result["intervention"]
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    safety_tracer.score("distress_score", distress0, comment="sos_gate_forced")
                    safety_tracer.update_output(
                        crisis_plan.visible_text,
                        metadata={
                            "routing_history": ["safety"],
                            "crisis_plan_source": crisis_plan.source,
                            "stream": True,
                            "latency_ms": elapsed_ms,
                        },
                    )
                    yield "event: status\ndata: " + json.dumps({"stage": "ready", "latency_ms": elapsed_ms}, ensure_ascii=False) + "\n\n"
                    yield "event: final\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"
                    return
                finally:
                    safety_tracer.flush()
                    set_active_tracer(None)

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
                # Keep stream first-token latency low: skip synchronous Neo4j prefetch.
                _stream_graph_patterns: dict = {}
                _stream_nutrition_meals = _load_today_meals(db, current_user.user_id)
                _stream_base_traits = dict(memory_ctx.traits if memory_ctx else {})
                if memory_ctx and memory_ctx.onboarding:
                    _stream_base_traits.setdefault("onboarding", memory_ctx.onboarding)
                _stream_persona_id = _active_persona_id(db, current_user.user_id, distress=distress)
                _stream_session_id = session.session_id
                _stream_user_id = current_user.user_id
                # Return the pooled connection before the long LLM stream so parallel
                # requests (auth, WS, voice) do not block on pool_size=1 deployments.
                try:
                    db.rollback()
                except Exception:
                    pass
                try:
                    db.close()
                except Exception:
                    pass
                db = None

                for ev in stream_non_sos_turn_events(
                    user_message=raw_text,
                    recent_messages=ctx.recent_messages,
                    mood_today=ctx.mood_today,
                    distress_score=distress,
                    long_term_memories=(memory_ctx.recent_summaries if memory_ctx else compat_longterm),
                    mem0_facts=(memory_ctx.mem0_facts if memory_ctx else []),
                    user_traits=_stream_base_traits,
                    top_triggers=(memory_ctx.top_triggers if memory_ctx else []),
                    active_goals=(memory_ctx.active_goals if memory_ctx else []),
                    effective_coping=(memory_ctx.effective_coping if memory_ctx else []),
                    clinical_trajectory=(memory_ctx.clinical_trajectory if memory_ctx else ""),
                    persona_id=_stream_persona_id,
                    user_id=_stream_user_id,
                    session_id=_stream_session_id,
                    active_memory_text="",
                    graph_patterns=_stream_graph_patterns,
                    nutrition_meals=_stream_nutrition_meals or None,
                ):
                    if ev.get("type") == "token":
                        yield "event: delta\ndata: " + json.dumps({"text": str(ev.get("text") or "")}, ensure_ascii=False) + "\n\n"
                    elif ev.get("type") == "final":
                        turn = ev.get("turn")
                if not turn:
                    raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504)
                set_cached_turn(
                    _stream_session_id,
                    message_hash,
                    turn,
                    ttl_seconds=settings.chat_response_cache_ttl_seconds,
                )

                db = get_session_factory()()
                session = db.scalar(
                    select(Conversation).where(
                        Conversation.session_id == _stream_session_id,
                        Conversation.user_id == _stream_user_id,
                        Conversation.deleted_at.is_(None),
                    )
                )
                if not session:
                    raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404)

            snap = turn["session_fields"]
            assistant_content = turn["reply"]
            tone = turn["assistant_tone"]
            goi_y = turn["goi_y_nhanh"]
            the_dinh = _compact_recommendation_attachments(turn["the_dinh_kem"])
            routing_hist: list[str] = turn.get("routing_history") or []

            assistant_msg = Message(
                message_id=make_id("msg"),
                session_id=session.session_id,
                user_id=current_user.user_id,
                role="assistant",
                content=mask_pii(assistant_content),
                assistant_tone=tone if tone in ("supportive", "validating", "cheerful", "calming", "mentor", "neutral") else "validating",
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
                kwargs={
                    "user_name": str(getattr(current_user, "display_name", None) or "bạn"),
                },
                daemon=True,
            ).start()

            vhint = None
            if snap.safety_tier == "voice_recommended":
                vhint = "Bạn có thể bấm gọi để nói chuyện trực tiếp với tổng đài — mình vẫn ở đây trong lúc bạn cân nhắc."

            data = build_normal_envelope(
                session.session_id,
                snap=snap,
                reply=assistant_content,
                assistant_tone=tone,
                goi_y_nhanh=goi_y,
                the_dinh_kem=the_dinh,
                voice_hint=vhint,
                routing_history=routing_hist,
            )
            data["intervention"] = None
            if review_decision.requires_human_review:
                data["pending_human_review"] = True
                data["review_reason"] = review_decision.reason
            distress_for_voice = float(snap.distress_score)
            history_for_voice = _recent_distress_history(ctx.recent_messages, max_turns=settings.proactive_voice_window_turns)
            signal_for_voice = compute_escalation_signal(
                current_distress=distress_for_voice,
                previous_distress=history_for_voice,
                threshold=settings.proactive_voice_threshold,
                delta_threshold=settings.proactive_voice_delta_threshold,
                window_turns=settings.proactive_voice_window_turns,
            )
            keyword_voice = message_suggests_proactive_voice(str(raw_text or ""))
            emotional_weight = (
                distress_for_voice >= 0.55
                or signal_for_voice.escalate
                or keyword_voice
                or any(k in str(raw_text or "").lower() for k in ("buon", "met", "lo", "stress", "ap luc", "khong on"))
            )
            purely_technical = any(k in str(raw_text or "").lower() for k in ("api", "code", "bug", "deploy", "database")) and distress_for_voice < 0.55
            voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
                user_id=current_user.user_id,
                session_id=session.session_id,
                distress_score=distress_for_voice,
                safety_tier=str(snap.safety_tier),
                sos_triggered=False,
                cooldown_active=cooldown_is_active,
                cooldown_seconds_remaining=cooldown_seconds,
                user_voice_enabled=get_voice_consent(db, current_user.user_id),
                provider_enabled=True,
                current_turn_has_emotional_weight=emotional_weight,
                purely_technical_turn=purely_technical,
                visible_text=assistant_content,
                reason_codes=tuple([signal_for_voice.trigger_reason] if signal_for_voice.escalate else []),
            ))
            voice_result = _enqueue_voice_policy(
                db=db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                persona_id=_stream_persona_id,
                decision=voice_decision,
                snap=snap,
                trigger_reason=signal_for_voice.trigger_reason if signal_for_voice.escalate else f"{voice_decision.risk_mode}_voice_policy",
                rolling_window_turns=signal_for_voice.rolling_window_turns,
                delta_score=signal_for_voice.delta_score,
            )
            data["voice_policy"] = voice_result["voice_policy"]
            data["intervention"] = voice_result["intervention"]

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
            if db is not None:
                try:
                    db.rollback()
                except Exception:
                    pass
                try:
                    db.close()
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
            guest_sos_text = assistant_text_for_sos(raw_text, 0)
            guest_crisis_plan = build_fallback_plan(
                guest_sos_text,
                is_alone=is_alone_signal(raw_text),
                session_sos_count=0,
            )
            data = build_sos_chat_response_data(session_id, snap, assistant_text=guest_crisis_plan.visible_text)
            data["voice_script"] = guest_crisis_plan.voice_script
            data["crisis_plan"] = guest_crisis_plan.model_dump()
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
        tone = str(turn.get("assistant_tone") or "validating")
        goi_y = turn.get("goi_y_nhanh") if isinstance(turn.get("goi_y_nhanh"), list) else []
        the_dinh = _compact_recommendation_attachments(
            turn.get("the_dinh_kem") if isinstance(turn.get("the_dinh_kem"), list) else []
        )
        routing_hist: list[str] = turn.get("routing_history") if isinstance(turn.get("routing_history"), list) else []

        data = build_normal_envelope(
            session_id,
            snap=snap,
            reply=assistant_content,
            assistant_tone=tone,
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
    current_user: User = Depends(get_current_user_for_stream),
):
    with get_session_factory()() as db:
        job_check = get_voice_job(db, tts_job_id)
        if not job_check or job_check.get("user_id") != current_user.user_id:
            raise AppError("VOICE_JOB_NOT_FOUND", "Voice job không tồn tại", 404)

    async def event_stream():
        previous_status = None
        for _ in range(30):
            with get_session_factory()() as db:
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
            if status in TTS_TERMINAL_STATUSES or status in {"done", "synced"}:
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
            "assistant_tone": m.assistant_tone,
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

    now = get_now().replace(tzinfo=None)
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
