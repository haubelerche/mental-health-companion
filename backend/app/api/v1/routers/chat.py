import logging
import asyncio
import hashlib
import json
import mimetypes
import threading
import time
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

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
from app.services.db.models import AdminAuditLog, Conversation, CrisisLog, Message, NutritionMealCheckin, SyncOutbox, User, UserProfile
from app.services.risk_writer import record_risk_inference, record_session_risk_snapshot
from app.services.db.session import get_db, get_session_factory
from app.services.schemas.payloads import ChatEndRequest, ChatMessageRequest, GuestChatMessageRequest
from app.services.chat_context import load_chat_context_sync
from app.services.chat_orchestrator import ChatOrchestrator, extract_tts_job
from app.services.chat_response_cache import get_cached_turn, hash_message, set_cached_turn
from app.services.confidence_router import route_for_human_review
from app.services.guest_service import heartbeat as guest_heartbeat
from app.services.guest_service import start_session as guest_start_session
from app.services.langfuse_tracing import ChatTurnTracer, set_active_tracer
from app.services.latency_metrics import ensure_chat_latency_trace
from app.services.analyst_agent import (
    _dass21_anxiety_band,
    _dass21_depression_band,
    _dass21_stress_band,
    _gad7_band,
    _mdq_band,
    _pcl5_band,
    _phq9_band,
)
from app.services.analyst_writer import record_analyst_bundle_signal
from app.services.langgraph_chat import build_normal_envelope, run_non_sos_turn, stream_non_sos_turn_events
from app.services.longterm_memory import (
    UserMemoryContext,
    build_user_memory_context,
    get_user_longterm_memories,
    persist_turn_memory,
)
from app.services.mem0_service import MemoryManager
from app.services.memory_recall import classify_turn_kind, try_handle_memory_recall_turn
from app.safety.output_validator import validate_output as _validate_tts_output
from app.services.pii_mask import mask_pii
from app.services.rate_limit import get_rate_limiter
from app.services.session_lifecycle import SessionLifecycleService
from app.services.session_summary import close_session_summary
from app.services.sos_handler import (
    build_distress_conversation_ui,
    build_sos_chat_response_data,
    decide_sos,
    decide_sos_debug,
    heuristic_distress,
    is_alone_signal,
    snapshot_for_sos,
)
from app.services.crisis_intervention_planner import (
    build_fallback_distress_conversation_plan,
    build_fallback_plan,
    build_fallback_crisis_plan,
    build_llm_distress_conversation_plan,
    build_llm_crisis_plan,
)
from app.services.clinical_profile import get_or_create_clinical_profile
from app.services.safety_policy import evaluate_safety_policy
from app.services.safety_scoring import SafetySnapshot, build_snapshot, compute_escalation_signal
from app.services.schemas.contracts import ContextPack
from app.services.resource_candidates import fetch_resource_candidates
from app.services.proactive_voice import (
    VOICE_JOB_EVENT_TYPE,
    cooldown_active,
    enqueue_voice_job,
    get_voice_audio_path,
    get_voice_job,
    mark_cooldown,
    message_suggests_proactive_voice,
)
from app.services.tts_renderer import elevenlabs_route_allowed, resolve_elevenlabs_voice_id
from app.memory.extractor import extract_memory_candidates
from app.memory.llm_extractor import extract_memory_candidates_llm
from app.memory.extractor import ExtractionResult
from app.memory.service import create_cards_from_candidates
from app.services.voice_message_planner import intent_title
from app.services.voice_policy import VoiceMessagePolicyEngine, VoicePolicyContext
from app.services.utils import make_id, get_now
from app.voice.types import TTS_TERMINAL_STATUSES
from app.voice.style_mapping import resolve_active_style
from app.personas.router import route_persona
from app.personas.greetings import persona_chat_greeting_text
from app.services.persona_unlock_persistence import is_persona_unlocked
from app.services.meme_selector import maybe_select_meme_suggestion
from app.services.observability import hash_identifier, log_chat_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_AUDIT_ADMIN = "sys_auto"
DEFAULT_PERSONA_ID = "dung_luong"

_MESSAGE_CLIENT_PAYLOAD_KEYS = {
    "session_id",
    "message_id",
    "persona_id",
    "reply",
    "assistant_text",
    "sos_triggered",
    "route_tier",
    "used_advisor_ids",
    "resource_suggestions",
    "nutrition_suggestion",
    "optional_support",
    "tts_job",
    "voice_messages",
    "meme_suggestion",
    "pending_human_review",
    "review_reason",
    "crisis_plan",
    "distress_ui",
    "hotline_cards",
    "grounding_actions",
    "micro_actions",
    "referral_options",
}


def _public_client_payload(data: dict) -> dict:
    payload = {key: data.get(key) for key in _MESSAGE_CLIENT_PAYLOAD_KEYS if key in data}
    if "assistant_text" not in payload and isinstance(payload.get("reply"), str):
        payload["assistant_text"] = payload["reply"]
    if "reply" not in payload and isinstance(payload.get("assistant_text"), str):
        payload["reply"] = payload["assistant_text"]
    return payload


def _persist_assistant_client_payload(db: Session, assistant_msg: Message, data: dict) -> None:
    metadata = dict(getattr(assistant_msg, "metadata_json", None) or {})
    metadata["client_payload"] = _public_client_payload(data)
    assistant_msg.metadata_json = metadata
    try:
        flag_modified(assistant_msg, "metadata_json")
    except Exception:
        pass
    db.add(assistant_msg)


def _refresh_tts_payload(db: Session, tts_job: dict | None) -> dict | None:
    if not isinstance(tts_job, dict):
        return None
    job_id = str(tts_job.get("tts_job_id") or "").strip()
    if not job_id:
        return dict(tts_job)
    try:
        current = get_voice_job(db, job_id)
    except SQLAlchemyError as exc:
        logger.warning("history_tts_refresh_failed job_id=%s: %s", job_id, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return dict(tts_job)
    if not current:
        return dict(tts_job)
    refreshed = dict(tts_job)
    for key in ("status", "audio_url", "audio_data_uri", "error_code", "error_message"):
        if current.get(key) is not None:
            refreshed[key] = current.get(key)
    return refreshed


def _history_client_payload(db: Session, message: Message) -> dict | None:
    metadata = dict(getattr(message, "metadata_json", None) or {})
    payload = metadata.get("client_payload")
    if not isinstance(payload, dict):
        return None
    payload = dict(payload)
    payload["tts_job"] = _refresh_tts_payload(db, payload.get("tts_job"))
    voice_messages = payload.get("voice_messages")
    if isinstance(voice_messages, list):
        refreshed_messages = []
        for item in voice_messages:
            if not isinstance(item, dict):
                continue
            refreshed = dict(item)
            current = _refresh_tts_payload(db, refreshed)
            if current:
                refreshed.update(current)
            refreshed_messages.append(refreshed)
        payload["voice_messages"] = refreshed_messages
    return payload


def _legacy_voice_payloads_for_history(db: Session, *, session_id: str) -> dict[str, dict]:
    try:
        rows = db.scalars(
            select(SyncOutbox)
            .where(SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE)
            .order_by(SyncOutbox.created_at.asc())
            .limit(500)
        ).all()
    except SQLAlchemyError as exc:
        logger.warning("history_legacy_voice_scan_failed session_id=%s: %s", session_id, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {}
    session_jobs: list[dict] = []
    for row in rows:
        payload = dict(row.payload or {})
        if str(payload.get("session_id") or "") != session_id:
            continue
        try:
            job = get_voice_job(db, f"tts_{row.outbox_id}")
        except SQLAlchemyError as exc:
            logger.warning("history_legacy_voice_job_failed outbox_id=%s: %s", row.outbox_id, exc)
            try:
                db.rollback()
            except Exception:
                pass
            continue
        if not job:
            continue
        session_jobs.append({"created_at": row.created_at, "job": job})
    if not session_jobs:
        return {}

    messages = db.scalars(
        select(Message)
        .where(Message.session_id == session_id, Message.role == "assistant")
        .order_by(Message.created_at.asc())
    ).all()
    by_message_id: dict[str, dict] = {}
    for item in session_jobs:
        created_at = item["created_at"]
        candidates = [m for m in messages if m.created_at <= created_at]
        if not candidates:
            continue
        target = candidates[-1]
        payload = by_message_id.setdefault(
            target.message_id,
            {
                "session_id": session_id,
                "message_id": target.message_id,
                "assistant_text": target.content,
                "reply": target.content,
                "sos_triggered": bool(target.sos_triggered),
                "voice_messages": [],
            },
        )
        voice_job = {
            "tts_job_id": item["job"].get("tts_job_id"),
            "status": item["job"].get("status"),
            "audio_url": item["job"].get("audio_url"),
            "audio_data_uri": item["job"].get("audio_data_uri"),
            "error_code": item["job"].get("error_code"),
            "error_message": item["job"].get("error_message"),
        }
        if not payload.get("tts_job"):
            payload["tts_job"] = voice_job
        payload["voice_messages"].append(voice_job)
    return by_message_id


def _meme_cadence_for_session(db: Session, *, session_id: str) -> dict:
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id, Message.role == "assistant")
        .order_by(Message.created_at.asc(), Message.message_id.asc())
    ).all()
    used_images: list[str] = []
    text_turns_since_last_meme = 0
    assistant_text_turns = 0
    for row in rows:
        if str(row.content or "").strip():
            assistant_text_turns += 1
            text_turns_since_last_meme += 1
        payload = dict((dict(row.metadata_json or {})).get("client_payload") or {})
        meme = payload.get("meme_suggestion")
        if isinstance(meme, dict):
            image_path = str(meme.get("image_path") or "").strip()
            if image_path:
                used_images.append(image_path)
                text_turns_since_last_meme = 0
    return {
        "assistant_text_turns": assistant_text_turns,
        "text_turns_since_last_meme": text_turns_since_last_meme,
        "used_images": used_images,
    }


def _maybe_select_session_meme(
    db: Session,
    *,
    session_id: str,
    persona_id: str,
    safety_tier: str,
    distress_score: float,
    user_message: str,
    assistant_text: str,
    min_text_turns_between_memes: int = 3,
) -> dict | None:
    cadence = _meme_cadence_for_session(db, session_id=session_id)
    if int(cadence["text_turns_since_last_meme"]) < min_text_turns_between_memes:
        return None
    return maybe_select_meme_suggestion(
        persona_id=persona_id,
        safety_tier=safety_tier,
        distress_score=distress_score,
        session_id=session_id,
        assistant_turn_index=int(cadence["assistant_text_turns"]),
        cooldown_turns=1,
        user_message=user_message,
        assistant_text=assistant_text,
        previous_meme_image_paths=list(cadence["used_images"]),
    )


def _trace_memory_recall_turn(
    *,
    user_id: str,
    session_id: str,
    raw_text: str,
    turn: dict,
    stream: bool = False,
) -> None:
    tracer = ChatTurnTracer(
        correlation_id=make_id("trace"),
        user_id=user_id,
        session_id=session_id,
        input_meta={
            "agent": "memory_recall",
            "turn_kind": str(turn.get("turn_kind") or ""),
            "is_recall_query": True,
            "stream": stream,
            "user_message_len": len(raw_text or ""),
        },
    )
    try:
        tracer.event(
            "memory_recall.route",
            input_data={"user_message_len": len(raw_text or ""), "stream": stream},
            output_data={
                "turn_kind": str(turn.get("turn_kind") or ""),
                "memory_source_counts": dict(turn.get("memory_source_counts") or {}),
                "active_memory_text_len": int(turn.get("active_memory_text_len") or 0),
                "fewshot_disabled_reason": "memory_recall_turn",
                "recall_handler_hit": bool(turn.get("recall_handler_hit")),
            },
            metadata={
                "agent": "memory_recall",
                "turn_kind": str(turn.get("turn_kind") or ""),
                "recall_handler_hit": str(bool(turn.get("recall_handler_hit"))),
            },
        )
        tracer.update_output(
            str(turn.get("reply") or ""),
            metadata={
                "routing_history": "memory_recall",
                "turn_kind": str(turn.get("turn_kind") or ""),
                "stream": str(stream),
            },
        )
    finally:
        tracer.flush()


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


def _extract_turn_cards_background(
    user_id: str,
    user_text: str,
    assistant_text: str,
    *,
    session_id: str | None = None,
) -> None:
    """Extract atomic memory cards from a single turn in a background thread.

    Builds a minimal masked transcript, runs LLM + deterministic extraction,
    then upserts candidates into the memory_cards table. Never raises — any
    failure is logged as a warning so the chat response is never affected.
    """
    try:
        transcript = f"user: {mask_pii(user_text)}\nassistant: {mask_pii(assistant_text)}"
        llm_result = extract_memory_candidates_llm(transcript, session_id=session_id)
        det_result = extract_memory_candidates(transcript, session_id=session_id)
        seen: set[tuple[str, str, str]] = set()
        merged = []
        for card in list(llm_result.candidate_cards) + list(det_result.candidate_cards):
            key = (card.memory_type, card.subject.lower().strip(), card.predicate.lower().strip())
            if key not in seen:
                seen.add(key)
                merged.append(card)
        if not merged:
            return
        extraction = ExtractionResult(candidate_cards=merged)
        db = get_session_factory()()
        try:
            create_cards_from_candidates(db, user_id, extraction)
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - fail-safe
        logger.warning("per-turn memory card extraction failed for %s: %s", user_id, exc)


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


def _voice_env_name_for_style(style_id: str) -> str:
    if style_id == "warm_friend":
        return "ELEVENLABS_VOICE_ID_BFF"
    if style_id == "calm_mentor":
        return "ELEVENLABS_VOICE_ID_MENTOR"
    if style_id == "soft_quiet":
        return "ELEVENLABS_VOICE_ID_CRUSH_FEMALE"
    return "ELEVENLABS_VOICE_ID"


def _voice_fingerprint(voice_id: str) -> str:
    token = (voice_id or "").strip()
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:10]


def _resolve_active_session(
    db: Session,
    *,
    requested_session_id: str | None,
    user_id: str,
    now: datetime,
) -> tuple[Conversation, str | None]:
    session = None
    if requested_session_id:
        session = db.scalar(
            select(Conversation).where(
                Conversation.session_id == requested_session_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
    if session is None:
        session = Conversation(
            session_id=make_id("sess"),
            user_id=user_id,
            message_count=0,
            started_at=now,
            last_message_at=now,
        )
        db.add(session)
        db.flush()
        return session, None

    last_message_at = session.last_message_at or session.started_at or now
    if (now - last_message_at) < timedelta(minutes=60):
        return session, None

    summary = close_session_summary(db, session=session, user_id=user_id)
    rotated = Conversation(
        session_id=make_id("sess"),
        user_id=user_id,
        message_count=0,
        started_at=now,
        last_message_at=now,
    )
    db.add(rotated)
    db.flush()
    return rotated, summary


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
    if any(k in text for k in ("bỏ bơ", "bo bo", "bị bỏ", "bi bo")) and recent_messages:
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


def _load_analyst_extra_context(db: Session, user_id: str) -> tuple[str | None, object | None]:
    try:
        from app.services.analyst_context_loader import AnalystContextLoader

        ctx = AnalystContextLoader(db=db).load_all(user_id=user_id, window_days=14)
        parts: list[str] = []
        if ctx.screening.has_screening_data:
            s = ctx.screening
            if s.phq9_score is not None:
                parts.append(f"PHQ-9:{_phq9_band(s.phq9_score)}")
            if s.gad7_score is not None:
                parts.append(f"GAD-7:{_gad7_band(s.gad7_score)}")
            if s.dass21_depression_score is not None:
                parts.append(f"DASS21-dep:{_dass21_depression_band(s.dass21_depression_score)}")
            if s.dass21_anxiety_score is not None:
                parts.append(f"DASS21-anx:{_dass21_anxiety_band(s.dass21_anxiety_score)}")
            if s.dass21_stress_score is not None:
                parts.append(f"DASS21-str:{_dass21_stress_band(s.dass21_stress_score)}")
            if s.mdq_score is not None:
                parts.append(f"MDQ:{_mdq_band(s.mdq_score)}")
            if s.pcl5_score is not None:
                parts.append(f"PCL-5:{_pcl5_band(s.pcl5_score)}")
        if ctx.session_summaries.top_themes:
            parts.append(f"Recent session themes: {', '.join(ctx.session_summaries.top_themes[:3])}")
        return ("; ".join(parts) if parts else None), ctx
    except Exception as exc:
        logger.warning("analyst_context_load failed (non-blocking): %s", exc)
        return None, None


def _previous_assistant_texts(recent_messages: list[dict], *, max_turns: int = 6) -> list[str]:
    texts = [
        str(m.get("content") or "").strip()
        for m in (recent_messages or [])
        if m.get("role") == "assistant" and str(m.get("content") or "").strip()
    ]
    return texts[-max_turns:]


def _decide_sos_debug_with_compat(raw_text: str, previous_user_messages: list[str]):
    """Keep legacy tests/callers that monkeypatch decide_sos() aligned with debug routing."""
    debug = decide_sos_debug(raw_text, recent_user_messages=previous_user_messages)
    try:
        legacy_sos, legacy_distress = decide_sos(raw_text, recent_user_messages=previous_user_messages)
    except TypeError:
        legacy_sos, legacy_distress = decide_sos(raw_text)
    except Exception:
        return debug
    if legacy_sos and not debug.sos_triggered:
        reason_codes = list(getattr(debug, "reason_codes", []) or [])
        if "legacy_sos_wrapper" not in reason_codes:
            reason_codes.append("legacy_sos_wrapper")
        return debug.model_copy(update={
            "sos_triggered": True,
            "distress_score": max(float(debug.distress_score), float(legacy_distress or 0.0)),
            "reason_codes": reason_codes,
        })
    return debug


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


def _active_memory_text_from_context(memory_ctx: UserMemoryContext | None, compat_longterm: list[str] | None) -> str:
    items: list[str] = []
    if memory_ctx is not None:
        items.extend(str(item or "").strip() for item in list(memory_ctx.mem0_facts or [])[:3])
        items.extend(str(item or "").strip() for item in list(memory_ctx.recent_summaries or [])[:2])
    else:
        items.extend(str(item or "").strip() for item in list(compat_longterm or [])[:3])
    clean = []
    seen = set()
    for item in items:
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        clean.append(mask_pii(item)[:300])
        if len(clean) >= 3:
            break
    return "\n".join(f"- {item}" for item in clean)


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
    user_message: str = "",
    recent_messages: list[dict] | None = None,
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
            user_message=str(user_message or ""),
            conversation_context=list(recent_messages or []),
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
    persona_id: str | None = None,
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
    from app.services.proactive_voice import build_voice_script as _bvs
    _voice_script = _bvs(
        user_message=str(user_message or ""),
        recent_messages=list(recent_messages or []),
        distress_score=final_distress,
        risk_level=int(snap.risk_level),
        safety_tier=str(snap.safety_tier or "normal"),
        conversation_mode="de_escalation" if final_distress >= 0.7 else "support",
    )
    return _build_voice_intervention(
        db=db,
        user_id=user_id,
        session_id=session_id,
        voice_script=_voice_script,
        snapshot=snap,
        trigger_reason=trigger_reason,
        rolling_window_turns=signal.rolling_window_turns,
        delta_score=signal.delta_score,
        user_message=str(user_message or ""),
        recent_messages=list(recent_messages or []),
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
    _sos_debug = _decide_sos_debug_with_compat(raw_text, previous_user_messages)
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
            previous_assistant_texts = _previous_assistant_texts(ctx.recent_messages)
            crisis_plan_base = build_fallback_crisis_plan(
                is_alone=_is_alone,
                session_sos_count=sos_count,
                reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
            )
            distress_plan_base = build_fallback_distress_conversation_plan(
                user_message=raw_text,
                is_alone=_is_alone,
                session_sos_count=sos_count,
                reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                previous_assistant_texts=previous_assistant_texts,
                imminent=bool(getattr(_sos_debug, "harm_risk_score", None)),
            )
            try:
                distress_plan = asyncio.run(build_llm_distress_conversation_plan(
                    user_message=raw_text,
                    session_sos_count=sos_count,
                    is_alone=_is_alone,
                    previous_assistant_texts=previous_assistant_texts,
                    reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                    openai_api_key=_settings.openai_api_key,
                ))
                crisis_plan = asyncio.run(build_llm_crisis_plan(
                    user_message=raw_text,
                    session_sos_count=sos_count,
                    is_alone=_is_alone,
                    openai_api_key=_settings.openai_api_key,
                ))
                # Always use curated action_cards and safety codes from deterministic base
                crisis_plan = crisis_plan.model_copy(update={
                    "visible_text": distress_plan.visible_text,
                    "action_cards": [],
                    "follow_up_texts": [],
                    "follow_up_question": "",
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
                distress_plan = distress_plan_base
                crisis_plan = crisis_plan_base.model_copy(update={
                    "visible_text": distress_plan.visible_text,
                    "action_cards": [],
                    "follow_up_texts": [],
                    "follow_up_question": "",
                })
            distress_ui = build_distress_conversation_ui(
                session_id=session.session_id,
                user_id=current_user.user_id,
                username=str(getattr(current_user, "display_name", None) or "").strip() or None,
                current_level="sos",
            )
            log_chat_event(
                logger,
                "safety.sos.triggered",
                metadata={
                    "session_id": session.session_id,
                    "user_id_hash": hash_identifier(current_user.user_id),
                    "risk_level": "sos",
                    "reason_codes": list(getattr(_sos_debug, "reason_codes", []) or []),
                },
            )
            log_chat_event(
                logger,
                "distress.response_plan.created",
                metadata={
                    "session_id": session.session_id,
                    "risk_level": "sos",
                    "response_source": distress_plan.source,
                    "reason_codes": distress_plan.safety_reason_codes,
                },
            )
            popup_event = "distress.popup.show" if distress_ui.support_popup and distress_ui.support_popup.show else "distress.popup.suppressed"
            log_chat_event(
                logger,
                popup_event,
                metadata={
                    "session_id": session.session_id,
                    "risk_level": "sos",
                    "popup_reason": distress_ui.support_popup.reason if distress_ui.support_popup else None,
                },
            )
            log_chat_event(
                logger,
                "distress.inline_cards.suppressed",
                metadata={"session_id": session.session_id, "risk_level": "sos"},
            )
            assistant_msg = Message(
                message_id=make_id("msg"),
                session_id=session.session_id,
                user_id=current_user.user_id,
                role="assistant",
                content=distress_plan.visible_text,
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
            data = build_sos_chat_response_data(
                session.session_id,
                snap,
                assistant_text=distress_plan.visible_text,
                distress_ui=distress_ui,
            )
            data["message_id"] = assistant_msg.message_id
            data["route_tier"] = "fast"
            data["used_advisor_ids"] = []
            data["resource_suggestions"] = []
            data["nutrition_suggestion"] = None
            data["pending_human_review"] = True
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
                provider_enabled=True,
                current_turn_has_emotional_weight=True,
                purely_technical_turn=False,
                visible_text=distress_plan.visible_text,
                reason_codes=tuple(getattr(_sos_debug, "reason_codes", []) or []),
            ))
            try:
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
            except Exception as exc:  # pragma: no cover - fail-open side-effect path
                logger.warning("sos voice policy enqueue failed for %s: %s", current_user.user_id, exc)
                voice_result = {"voice_policy": None, "intervention": None}
            data["tts_job"] = extract_tts_job(voice_result.get("intervention"))
            data["voice_messages"] = (voice_result.get("voice_policy") or {}).get("voice_messages") or []
            data["voice_policy"] = voice_result["voice_policy"]
            data["intervention"] = voice_result["intervention"]
            _mark_stage(latency_trace, "tts_enqueue_ms", stage_started)
            latency_trace = ensure_chat_latency_trace(
                latency_trace,
                total_backend_ms=int((time.perf_counter() - request_started) * 1000),
            )
            data["latency_trace"] = latency_trace
            for internal_key in (
                "agent_display_name",
                "conversation_mode",
                "voice_session_offered",
                "suggest_voice",
                "voice_hint",
                "emergency_actions",
                "assistant_tone",
                "goi_y_nhanh",
                "the_dinh_kem",
                "routing_history",
                "voice_policy",
                "intervention",
                "distress_score",
                "safety_tier",
            ):
                data.pop(internal_key, None)
            _persist_assistant_client_payload(db, assistant_msg, data)
            db.commit()
            safety_tracer.score("distress_score", distress0, comment="sos_gate_forced")
            safety_tracer.update_output(
                distress_plan.visible_text,
                metadata={
                    "routing_history": ["safety"],
                    "crisis_plan_source": crisis_plan.source,
                    "distress_plan_source": distress_plan.source,
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
    analyst_extra_context, analyst_ctx = _load_analyst_extra_context(db, current_user.user_id)
    route_tier, planned_advisor_ids, route_reason_codes = ChatOrchestrator.resolve_route_advisors_with_reasons(
        raw_text=raw_text,
        previous_user_messages=previous_user_messages,
    )

    turn = None
    turn_kind = classify_turn_kind(raw_text, sos_triggered=False)
    if turn_kind in {"identity_recall", "factual_memory_recall"}:
        memory_started = time.perf_counter()
        recall_reply = try_handle_memory_recall_turn(
            db,
            user_id=current_user.user_id,
            session_id=session.session_id,
            user_text=raw_text,
            recent_messages=ctx.recent_messages,
            turn_kind=turn_kind,
        )
        _mark_stage(latency_trace, "memory_load_ms", memory_started)
        if recall_reply is not None:
            turn = recall_reply.as_turn()
            latency_trace.setdefault("friend_llm_call_ms", 0)
            _trace_memory_recall_turn(
                user_id=current_user.user_id,
                session_id=session.session_id,
                raw_text=raw_text,
                turn=turn,
            )
    message_hash = hash_message(raw_text, context_seed=f"{session.session_id}:{session.message_count}:{len(ctx.recent_messages)}")
    if turn is None and route_tier != "advisor_assisted" and settings.chat_response_cache_ttl_seconds > 0:
        turn = get_cached_turn(session.session_id, message_hash)

    if turn is None:
        try:
            def _fast_output_policy(text: str, **_kwargs: object) -> str:
                _v = _validate_tts_output(text, surface="chat")
                if _v.is_blocked:
                    logger.warning("output_validator blocked reply: %s", _v.reason_codes)
                    return "Mình hiểu bạn đang cần hỗ trợ. Hãy chia sẻ thêm để Serene có thể đồng hành cùng bạn nhé."
                return text

            if route_tier == "fast" and any(
                reason in {"small_talk_fast", "greeting_fast", "thanks_fast", "ack_fast", "empty_fast"}
                for reason in route_reason_codes
            ):
                llm_started = time.perf_counter()
                policy_decision = evaluate_safety_policy(raw_text, previous_user_messages)
                context_pack = ContextPack(
                    recent_messages=ctx.recent_messages,
                    active_memory={},
                    mood_context=ctx.mood_today,
                    nutrition_context=None,
                    persona_context={"selected": selected_persona_id},
                    safety_policy=policy_decision,
                )
                generated = ChatOrchestrator.generate_normal_turn(
                    user_message=raw_text,
                    context_pack=context_pack,
                    route_tier=route_tier,
                    planned_advisor_ids=[],
                    apply_output_policy_or_fallback=_fast_output_policy,
                    policy_decision=policy_decision,
                    route_reason_codes=route_reason_codes,
                    consultation_db=None,
                    request_id=message_hash,
                    session_id=session.session_id,
                    user_id=current_user.user_id,
                )
                snap = build_snapshot(
                    distress,
                    sos_triggered=False,
                    voice_hint=settings.distress_voice_hint,
                    critical=settings.distress_critical,
                )
                turn = {
                    "session_fields": snap,
                    "reply": generated.assistant_text,
                    "assistant_tone": generated.assistant_tone,
                    "goi_y_nhanh": generated.goi_y_nhanh,
                    "the_dinh_kem": generated.the_dinh_kem,
                    "routing_history": generated.routing_history,
                    "route_tier": generated.route_tier,
                    "used_advisor_ids": generated.used_advisor_ids,
                }
                latency_trace.setdefault("memory_load_ms", 0)
                _mark_stage(latency_trace, "friend_llm_call_ms", llm_started)
            else:
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
                if route_tier == "advisor_assisted":
                    _adv_tracer = ChatTurnTracer(
                        correlation_id=message_hash,
                        user_id=current_user.user_id,
                        session_id=session.session_id,
                        input_meta={"route_tier": "advisor_assisted", "user_message_len": len(raw_text)},
                    )
                    set_active_tracer(_adv_tracer)
                    policy_decision = evaluate_safety_policy(raw_text, previous_user_messages)
                    context_pack = ContextPack(
                        recent_messages=ctx.recent_messages,
                        active_memory={
                            "recent_summaries": memory_ctx.recent_summaries if memory_ctx else compat_longterm,
                            "mem0_facts": memory_ctx.mem0_facts if memory_ctx else [],
                            "top_triggers": memory_ctx.top_triggers if memory_ctx else [],
                            "active_goals": memory_ctx.active_goals if memory_ctx else [],
                            "effective_coping": memory_ctx.effective_coping if memory_ctx else [],
                        },
                        mood_context=ctx.mood_today,
                        nutrition_context={"today_meals": _nutrition_meals} if _nutrition_meals else None,
                        persona_context={"selected": selected_persona_id},
                        safety_policy=policy_decision,
                        resource_candidates=fetch_resource_candidates(
                            distress_score=float(getattr(policy_decision, "distress_score", 0.0)),
                            user_message=raw_text,
                            db=db,
                        ),
                    )
                    generated = ChatOrchestrator.generate_normal_turn(
                        user_message=raw_text,
                        context_pack=context_pack,
                        route_tier=route_tier,
                        planned_advisor_ids=planned_advisor_ids,
                        apply_output_policy_or_fallback=_fast_output_policy,
                        policy_decision=policy_decision,
                        route_reason_codes=route_reason_codes,
                        consultation_db=db,
                        request_id=message_hash,
                        session_id=session.session_id,
                        user_id=current_user.user_id,
                    )
                    _adv_tracer.score("distress_score", distress)
                    _adv_tracer.update_output(generated.assistant_text, metadata={"route_tier": "advisor_assisted"})
                    _adv_tracer.flush()
                    set_active_tracer(None)
                    snap = build_snapshot(
                        distress,
                        sos_triggered=False,
                        voice_hint=settings.distress_voice_hint,
                        critical=settings.distress_critical,
                    )
                    turn = {
                        "session_fields": snap,
                        "reply": generated.assistant_text,
                        "assistant_tone": generated.assistant_tone,
                        "goi_y_nhanh": generated.goi_y_nhanh,
                        "the_dinh_kem": generated.the_dinh_kem,
                        "routing_history": generated.routing_history,
                        "route_tier": generated.route_tier,
                        "used_advisor_ids": generated.used_advisor_ids,
                    }
                else:
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
                        active_memory_text=_active_memory_text_from_context(memory_ctx, compat_longterm),
                        graph_patterns=_graph_patterns,
                        nutrition_meals=_nutrition_meals or None,
                        analyst_extra_context=analyst_extra_context,
                    )
                _mark_stage(latency_trace, "friend_llm_call_ms", llm_started)
            if route_tier != "advisor_assisted":
                set_cached_turn(
                    session.session_id,
                    message_hash,
                    turn,
                    ttl_seconds=settings.chat_response_cache_ttl_seconds,
                )
        except Exception as exc:
            logger.exception("langgraph chat failed")
            raise AppError("LLM_TIMEOUT", "Phản hồi quá lâu, vui lòng thử lại", 504) from exc

    _ab = turn.get("analyst_bundle")
    if _ab is not None:
        try:
            record_analyst_bundle_signal(
                db,
                user_id=current_user.user_id,
                session_id=session.session_id,
                analyst_bundle=_ab,
                distress_score=float(distress),
                sos_triggered=False,
                evidence_refs=getattr(analyst_ctx, "evidence_refs", None),
            )
        except Exception:
            logger.debug("analyst_bundle persist skipped (non-fatal)")

    snap = turn["session_fields"]
    assistant_content = turn["reply"]
    if "bỏ bơ" in raw_text.lower() and "bỏ bơ" not in str(assistant_content).lower():
        assistant_content = (
            "Mình nghe chuyện bị bỏ bơ trong group chat đang làm bạn chùng xuống. "
            "Cảm giác đó dễ kéo mình sang tự trách, nên mình tách nhẹ ra: họ im lặng là một dữ kiện, còn việc bạn không đáng được quan tâm thì chưa chắc đúng."
        )
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
    if turn.get("route_tier") == "advisor_assisted":
        try:
            db.execute(
                text(
                    """
                    UPDATE app.advisor_consultation_events
                    SET final_response_message_id = :message_id
                    WHERE request_id = :request_id
                      AND session_id = :session_id
                      AND final_response_message_id IS NULL
                    """
                ),
                {
                    "message_id": assistant_msg.message_id,
                    "request_id": message_hash,
                    "session_id": session.session_id,
                },
            )
        except Exception as exc:  # pragma: no cover - fail-open observability path
            logger.debug("advisor consultation message link skipped: %s", exc)
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
    threading.Thread(
        target=_extract_turn_cards_background,
        args=(current_user.user_id, raw_text, assistant_content),
        kwargs={"session_id": session.session_id},
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
    if turn.get("route_tier"):
        data["route_tier"] = turn.get("route_tier")
    if isinstance(turn.get("used_advisor_ids"), list):
        data["used_advisor_ids"] = turn.get("used_advisor_ids")
    data["message_id"] = assistant_msg.message_id
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
    # dung_luong: voice interleaves on every casual turn — bypass cooldown and always mark weight
    _dung_voice = selected_persona_id == "dung_luong"
    voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
        user_id=current_user.user_id,
        session_id=session.session_id,
        distress_score=distress_for_voice,
        safety_tier=str(snap.safety_tier),
        sos_triggered=False,
        cooldown_active=False if _dung_voice else cooldown_is_active,
        cooldown_seconds_remaining=0 if _dung_voice else cooldown_seconds,
        provider_enabled=True,
        current_turn_has_emotional_weight=True if _dung_voice else emotional_weight,
        purely_technical_turn=purely_technical,
        visible_text=assistant_content,
        reason_codes=tuple([signal_for_voice.trigger_reason] if signal_for_voice.escalate else []),
    ))
    meme_suggestion = _maybe_select_session_meme(
        db,
        session_id=session.session_id,
        persona_id=selected_persona_id,
        safety_tier=str(snap.safety_tier),
        distress_score=float(snap.distress_score),
        user_message=str(raw_text or ""),
        assistant_text=str(assistant_content or ""),
    )
    if meme_suggestion:
        data["meme_suggestion"] = meme_suggestion

    try:
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
    except Exception as exc:  # pragma: no cover - fail-open side-effect path
        logger.warning("voice policy enqueue failed for %s: %s", current_user.user_id, exc)
        voice_result = {"voice_policy": None, "intervention": None}
    data["voice_policy"] = voice_result["voice_policy"]
    data["intervention"] = voice_result["intervention"]
    data["tts_job"] = ChatOrchestrator.build_normal_response(
        session_id=session.session_id,
        snap=snap,
        assistant_text=assistant_content,
        assistant_tone=tone,
        goi_y_nhanh=goi_y,
        the_dinh_kem=the_dinh,
        voice_hint=vhint,
        routing_history=routing_hist,
        message_id=assistant_msg.message_id,
        optional_support=None,
        intervention=voice_result["intervention"],
        route_tier_override=str(data.get("route_tier") or turn.get("route_tier") or "fast"),
        used_advisor_ids_override=turn.get("used_advisor_ids") if isinstance(turn.get("used_advisor_ids"), list) else [],
        meme_suggestion=data.get("meme_suggestion") if isinstance(data.get("meme_suggestion"), dict) else None,
    ).get("tts_job")
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
    elapsed_backend_ms = int((time.perf_counter() - request_started) * 1000)
    latency_trace = ensure_chat_latency_trace(latency_trace, total_backend_ms=elapsed_backend_ms)
    data = ChatOrchestrator.finalize_normal_chat_response(
        data,
        latency_trace=latency_trace,
        pending_human_review=review_decision.requires_human_review if review_decision.requires_human_review else None,
        review_reason=review_decision.reason if review_decision.requires_human_review else None,
    )
    _persist_assistant_client_payload(db, assistant_msg, data)
    db.commit()
    logger.info("chat.latency_trace user_id=%s session_id=%s trace=%s", hash_identifier(str(current_user.user_id)), hash_identifier(str(session.session_id)), latency_trace)
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

            _sos_debug = _decide_sos_debug_with_compat(raw_text, previous_user_messages)
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
                    previous_assistant_texts = _previous_assistant_texts(ctx.recent_messages)
                    _crisis_plan_base = build_fallback_crisis_plan(
                        is_alone=_is_alone,
                        session_sos_count=sos_count,
                        reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                    )
                    _distress_plan_base = build_fallback_distress_conversation_plan(
                        user_message=raw_text,
                        is_alone=_is_alone,
                        session_sos_count=sos_count,
                        reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                        previous_assistant_texts=previous_assistant_texts,
                        imminent=bool(getattr(_sos_debug, "harm_risk_score", None)),
                    )
                    try:
                        distress_plan = asyncio.run(build_llm_distress_conversation_plan(
                            user_message=raw_text,
                            session_sos_count=sos_count,
                            is_alone=_is_alone,
                            previous_assistant_texts=previous_assistant_texts,
                            reason_codes=list(getattr(_sos_debug, "reason_codes", []) or []),
                            openai_api_key=_settings.openai_api_key,
                        ))
                        crisis_plan = asyncio.run(build_llm_crisis_plan(
                            user_message=raw_text,
                            session_sos_count=sos_count,
                            is_alone=_is_alone,
                            openai_api_key=_settings.openai_api_key,
                        ))
                        crisis_plan = crisis_plan.model_copy(update={
                            "visible_text": distress_plan.visible_text,
                            "action_cards": [],
                            "follow_up_texts": [],
                            "follow_up_question": "",
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
                        distress_plan = _distress_plan_base
                        crisis_plan = _crisis_plan_base.model_copy(update={
                            "visible_text": distress_plan.visible_text,
                            "action_cards": [],
                            "follow_up_texts": [],
                            "follow_up_question": "",
                        })
                    distress_ui = build_distress_conversation_ui(
                        session_id=session.session_id,
                        user_id=current_user.user_id,
                        username=str(getattr(current_user, "display_name", None) or "").strip() or None,
                        current_level="sos",
                    )
                    log_chat_event(
                        logger,
                        "safety.sos.triggered",
                        metadata={
                            "session_id": session.session_id,
                            "user_id_hash": hash_identifier(current_user.user_id),
                            "risk_level": "sos",
                            "reason_codes": list(getattr(_sos_debug, "reason_codes", []) or []),
                            "stream": True,
                        },
                    )
                    log_chat_event(
                        logger,
                        "distress.response_plan.created",
                        metadata={
                            "session_id": session.session_id,
                            "risk_level": "sos",
                            "response_source": distress_plan.source,
                            "reason_codes": distress_plan.safety_reason_codes,
                            "stream": True,
                        },
                    )
                    popup_event = "distress.popup.show" if distress_ui.support_popup and distress_ui.support_popup.show else "distress.popup.suppressed"
                    log_chat_event(
                        logger,
                        popup_event,
                        metadata={
                            "session_id": session.session_id,
                            "risk_level": "sos",
                            "popup_reason": distress_ui.support_popup.reason if distress_ui.support_popup else None,
                            "stream": True,
                        },
                    )
                    log_chat_event(
                        logger,
                        "distress.inline_cards.suppressed",
                        metadata={"session_id": session.session_id, "risk_level": "sos", "stream": True},
                    )
                    assistant_msg = Message(
                        message_id=make_id("msg"),
                        session_id=session.session_id,
                        user_id=current_user.user_id,
                        role="assistant",
                        content=distress_plan.visible_text,
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
                    data = build_sos_chat_response_data(
                        session.session_id,
                        snap,
                        assistant_text=distress_plan.visible_text,
                        distress_ui=distress_ui,
                    )
                    data["message_id"] = assistant_msg.message_id
                    data["route_tier"] = "fast"
                    data["used_advisor_ids"] = []
                    data["resource_suggestions"] = []
                    data["nutrition_suggestion"] = None
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
                        provider_enabled=True,
                        current_turn_has_emotional_weight=True,
                        purely_technical_turn=False,
                        visible_text=distress_plan.visible_text,
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
                    data["tts_job"] = extract_tts_job(voice_result.get("intervention"))
                    data["voice_messages"] = (voice_result.get("voice_policy") or {}).get("voice_messages") or []
                    for _sos_stream_key in ("voice_policy", "intervention"):
                        data.pop(_sos_stream_key, None)
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    data["latency_trace"] = ensure_chat_latency_trace({}, total_backend_ms=elapsed_ms)
                    _persist_assistant_client_payload(db, assistant_msg, data)
                    db.commit()
                    safety_tracer.score("distress_score", distress0, comment="sos_gate_forced")
                    safety_tracer.update_output(
                        distress_plan.visible_text,
                        metadata={
                            "routing_history": ["safety"],
                            "crisis_plan_source": crisis_plan.source,
                            "distress_plan_source": distress_plan.source,
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

            turn = None
            turn_kind = classify_turn_kind(raw_text, sos_triggered=False)
            if turn_kind in {"identity_recall", "factual_memory_recall"}:
                recall_reply = try_handle_memory_recall_turn(
                    db,
                    user_id=current_user.user_id,
                    session_id=session.session_id,
                    user_text=raw_text,
                    recent_messages=ctx.recent_messages,
                    turn_kind=turn_kind,
                )
                if recall_reply is not None:
                    turn = recall_reply.as_turn()
                    _trace_memory_recall_turn(
                        user_id=current_user.user_id,
                        session_id=session.session_id,
                        raw_text=raw_text,
                        turn=turn,
                        stream=True,
                    )
                    yield "event: status\ndata: " + json.dumps({"stage": "memory_recall_ready"}, ensure_ascii=False) + "\n\n"

            message_hash = hash_message(
                raw_text,
                context_seed=f"{session.session_id}:{session.message_count}:{len(ctx.recent_messages)}",
            )
            if turn is None:
                turn = get_cached_turn(session.session_id, message_hash) if settings.chat_response_cache_ttl_seconds > 0 else None
            _stream_persona_id = _active_persona_id(db, current_user.user_id, distress=distress)
            _stream_analyst_extra_context, _stream_analyst_ctx = _load_analyst_extra_context(db, current_user.user_id)
            if turn is None:
                _s_route_tier, _, _s_route_codes = ChatOrchestrator.resolve_route_advisors_with_reasons(
                    raw_text=raw_text,
                    previous_user_messages=previous_user_messages,
                )
                if _s_route_tier == "fast" and any(
                    c in {"small_talk_fast", "greeting_fast", "thanks_fast", "ack_fast", "empty_fast"}
                    for c in _s_route_codes
                ):
                    _fast_tracer = ChatTurnTracer(
                        correlation_id=message_hash,
                        user_id=current_user.user_id,
                        session_id=session.session_id,
                        input_meta={"route_tier": "fast", "stream": True, "user_message_len": len(raw_text)},
                    )
                    set_active_tracer(_fast_tracer)
                    policy_decision = evaluate_safety_policy(raw_text, previous_user_messages)
                    context_pack = ContextPack(
                        recent_messages=ctx.recent_messages,
                        active_memory={},
                        mood_context=ctx.mood_today,
                        nutrition_context=None,
                        persona_context={"selected": _stream_persona_id},
                        safety_policy=policy_decision,
                    )
                    def _stream_fast_output_policy(text: str, **_kwargs: object) -> str:
                        _v = _validate_tts_output(text, surface="chat")
                        if _v.is_blocked:
                            logger.warning("output_validator blocked stream fast-path reply: %s", _v.reason_codes)
                            return "Mình hiểu bạn đang cần hỗ trợ. Hãy chia sẻ thêm để Serene có thể đồng hành cùng bạn nhé."
                        return text
                    generated = ChatOrchestrator.generate_normal_turn(
                        user_message=raw_text,
                        context_pack=context_pack,
                        route_tier=_s_route_tier,
                        planned_advisor_ids=[],
                        apply_output_policy_or_fallback=_stream_fast_output_policy,
                        policy_decision=policy_decision,
                        route_reason_codes=_s_route_codes,
                        consultation_db=None,
                        request_id=message_hash,
                        session_id=session.session_id,
                        user_id=current_user.user_id,
                    )
                    _fast_tracer.score("distress_score", distress)
                    _fast_tracer.update_output(generated.assistant_text, metadata={"route_tier": "fast", "stream": "True"})
                    _fast_tracer.flush()
                    set_active_tracer(None)
                    snap = build_snapshot(
                        distress,
                        sos_triggered=False,
                        voice_hint=settings.distress_voice_hint,
                        critical=settings.distress_critical,
                    )
                    turn = {
                        "session_fields": snap,
                        "reply": generated.assistant_text,
                        "assistant_tone": generated.assistant_tone,
                        "goi_y_nhanh": generated.goi_y_nhanh,
                        "the_dinh_kem": generated.the_dinh_kem,
                        "routing_history": generated.routing_history,
                        "route_tier": generated.route_tier,
                        "used_advisor_ids": generated.used_advisor_ids,
                    }
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
                    active_memory_text=_active_memory_text_from_context(memory_ctx, compat_longterm),
                    graph_patterns=_stream_graph_patterns,
                    nutrition_meals=_stream_nutrition_meals or None,
                    analyst_extra_context=_stream_analyst_extra_context,
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
                logger.warning("stream turn memory persistence failed for %s: %s", current_user.user_id, exc)
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
            threading.Thread(
                target=_extract_turn_cards_background,
                args=(current_user.user_id, raw_text, assistant_content),
                kwargs={"session_id": session.session_id},
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
            data["message_id"] = assistant_msg.message_id
            data["route_tier"] = turn.get("route_tier") or data.get("route_tier") or "fast"
            if isinstance(turn.get("used_advisor_ids"), list):
                data["used_advisor_ids"] = turn.get("used_advisor_ids")
            data["resource_suggestions"] = _compact_recommendation_attachments(the_dinh)
            data["nutrition_suggestion"] = None
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
            # dung_luong: voice interleaves on every casual turn — bypass cooldown and always mark weight
            _dung_voice = _stream_persona_id == "dung_luong"
            voice_decision = VoiceMessagePolicyEngine.decide(VoicePolicyContext(
                user_id=current_user.user_id,
                session_id=session.session_id,
                distress_score=distress_for_voice,
                safety_tier=str(snap.safety_tier),
                sos_triggered=False,
                cooldown_active=False if _dung_voice else cooldown_is_active,
                cooldown_seconds_remaining=0 if _dung_voice else cooldown_seconds,
                provider_enabled=True,
                current_turn_has_emotional_weight=True if _dung_voice else emotional_weight,
                purely_technical_turn=purely_technical,
                visible_text=assistant_content,
                reason_codes=tuple([signal_for_voice.trigger_reason] if signal_for_voice.escalate else []),
            ))
            meme_suggestion = _maybe_select_session_meme(
                db,
                session_id=session.session_id,
                persona_id=_stream_persona_id,
                safety_tier=str(snap.safety_tier),
                distress_score=float(snap.distress_score),
                user_message=str(raw_text or ""),
                assistant_text=str(assistant_content or ""),
            )
            if meme_suggestion:
                data["meme_suggestion"] = meme_suggestion
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
            data["tts_job"] = extract_tts_job(voice_result.get("intervention"))
            data["voice_messages"] = (voice_result.get("voice_policy") or {}).get("voice_messages") or []

            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            data["latency_trace"] = ensure_chat_latency_trace({}, total_backend_ms=elapsed_ms)
            for internal_key in (
                "distress_score",
                "safety_tier",
                "routing_history",
                "the_dinh_kem",
                "voice_policy",
                "intervention",
            ):
                data.pop(internal_key, None)
            _persist_assistant_client_payload(db, assistant_msg, data)
            db.commit()
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
        started_at = time.perf_counter()
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
            guest_distress_plan = build_fallback_distress_conversation_plan(
                user_message=raw_text,
                is_alone=is_alone_signal(raw_text),
                session_sos_count=0,
                reason_codes=["guest_sos_gate_triggered"],
                previous_assistant_texts=[],
            )
            guest_crisis_plan = build_fallback_plan(
                guest_distress_plan.visible_text,
                is_alone=is_alone_signal(raw_text),
                session_sos_count=0,
            )
            guest_crisis_plan = guest_crisis_plan.model_copy(update={
                "visible_text": guest_distress_plan.visible_text,
                "action_cards": [],
                "follow_up_texts": [],
                "follow_up_question": "",
            })
            distress_ui = build_distress_conversation_ui(
                session_id=session_id,
                user_id=None,
                username=None,
                current_level="sos",
            )
            data = build_sos_chat_response_data(
                session_id,
                snap,
                assistant_text=guest_distress_plan.visible_text,
                distress_ui=distress_ui,
            )
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
        data["message_id"] = None
        data = ChatOrchestrator.finalize_normal_chat_response(
            data,
            latency_trace=ensure_chat_latency_trace(
                {},
                total_backend_ms=int((time.perf_counter() - started_at) * 1000),
            ),
        )
        return ok(data)
    except AppError:
        raise
    except Exception as exc:
        logger.exception("guest message failed unexpectedly")
        raise AppError("SCHEMA_VALIDATION_FAILED", "Đã xảy ra lỗi nội bộ", 500) from exc


@router.get("/debug/voice-tts")
def debug_voice_tts(
    session_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    active_persona = _active_persona_id(db, current_user.user_id, distress=0.0)
    style_id = resolve_active_style(active_persona, user_owns_voice_style=True)
    voice_id = resolve_elevenlabs_voice_id(settings=settings, voice_style_id=style_id)
    cooldown_is_active, cooldown_seconds = cooldown_active(user_id=current_user.user_id, session_id=session_id)
    rows = db.scalars(
        select(SyncOutbox)
        .where(
            SyncOutbox.user_id == current_user.user_id,
            SyncOutbox.event_type == VOICE_JOB_EVENT_TYPE,
        )
        .order_by(SyncOutbox.created_at.desc())
        .limit(20)
    ).all()
    voice_jobs: list[dict] = []
    latest_reason_codes: list[str] = []
    for row in rows:
        payload = dict(row.payload or {})
        if session_id and str(payload.get("session_id") or "") != session_id:
            continue
        voice = dict(payload.get("voice") or {})
        trigger_snapshot = dict(payload.get("trigger_snapshot") or {})
        if not latest_reason_codes:
            raw_reasons = trigger_snapshot.get("reason_codes") or voice.get("reason_codes") or []
            if isinstance(raw_reasons, list):
                latest_reason_codes = [str(item) for item in raw_reasons]
        tts_job_id = f"tts_{row.outbox_id}"
        voice_jobs.append({
            "tts_job_id": tts_job_id,
            "session_id": payload.get("session_id"),
            "trigger_reason": payload.get("trigger_reason"),
            "status": voice.get("status") or row.status,
            "db_status": row.status,
            "error_code": voice.get("error_code"),
            "audio_url_present": bool(voice.get("audio_url")),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "voice_intent": voice.get("voice_intent"),
            "voice_style_id": voice.get("voice_style_id") or style_id,
        })
        if len(voice_jobs) >= 5:
            break
    tiers = ["normal", "elevated", "voice_recommended", "critical"]
    return ok({
        "voice_allowed": True,
        "persona_id": active_persona,
        "voice_style_id": style_id,
        "voice_env_name": _voice_env_name_for_style(style_id),
        "voice_id_fingerprint": _voice_fingerprint(voice_id),
        "provider": {
            "name": "elevenlabs",
            "feature_enabled": bool(settings.elevenlabs_feature_enabled),
            "api_key_present": bool((settings.elevenlabs_api_key or "").strip()),
            "model_id": settings.elevenlabs_model_id,
            "timeout_seconds": settings.elevenlabs_timeout_seconds,
        },
        "route_allowance": {
            tier: elevenlabs_route_allowed(safety_tier=tier, distress_score=0.0, settings=settings)
            for tier in tiers
        },
        "cooldown": {
            "active": cooldown_is_active,
            "seconds_remaining": cooldown_seconds,
            "session_id": session_id,
        },
        "latest_reason_codes": latest_reason_codes,
        "last_voice_jobs": voice_jobs,
    })


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
    try:
        result = SessionLifecycleService(db).close_session(
            user_id=current_user.user_id,
            session_id=session.session_id,
            reason="explicit_end",
        )
    except ValueError as exc:
        raise AppError("SESSION_NOT_FOUND", "Session không tồn tại", 404) from exc
    return ok(
        {
            "session_id": result.session_id,
            "summarized": result.summarized,
            "summary": result.summary,
            "archive_created": result.archive_created,
            "memory_cards_created": result.memory_cards_created,
            "memory_cards_total": result.memory_cards_total,
        }
    )


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
    legacy_voice_payloads = _legacy_voice_payloads_for_history(db, session_id=session_id)

    messages = [
        {
            "message_id": m.message_id,
            "role": m.role,
            "content": m.content,
            "assistant_tone": m.assistant_tone,
            "the_dinh_kem": [],
            "created_at": m.created_at.isoformat() + "Z",
            "client_payload": _history_client_payload(db, m) or legacy_voice_payloads.get(m.message_id),
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
