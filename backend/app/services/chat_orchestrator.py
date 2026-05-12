from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from app.advisors import (
    AdvisorPool,
    CBTPatternAdvisor,
    EmpathyAdvisor,
    NutritionSupportAdvisor,
    ReflectionAdvisor,
    StrategyResourceAdvisor,
)
from app.services.advisor_selector import AdvisorSelector
from app.services.counseling_advisor_service import CounselingAdvisorService
from app.services.fast_need_router import FastNeedRouter
from app.services.friend_agent import FriendAgent
from app.services.interaction_need_classifier import classify_interaction_need
from app.services.async_outbox import enqueue_worker_job
from app.services.langgraph_chat import build_normal_envelope
from app.services.langfuse_tracing import get_active_tracer
from app.services.observability import record_event, record_metric, start_span
from app.services.schemas.contracts import AdvisorAdvice, WorkerJob


def _extract_tts_job(intervention: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(intervention, dict):
        return None
    voice = intervention.get("voice")
    if not isinstance(voice, dict):
        return None
    tts_job_id = voice.get("tts_job_id")
    if not tts_job_id:
        return None
    return {
        "tts_job_id": tts_job_id,
        "status": voice.get("status"),
    }


def _normalize_route_tier(route_tier: str | None) -> str:
    if route_tier in {"fast", "service_only", "advisor_assisted"}:
        return route_tier
    return "fast"


def _sanitize_advisor_ids(advisor_ids: list[str] | None) -> list[str]:
    out: list[str] = []
    for item in advisor_ids or []:
        token = str(item or "").strip()
        if not token or token in out:
            continue
        out.append(token)
        if len(out) >= 2:
            break
    return out


def _sanitize_resource_suggestions(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        cleaned = {
            "id": item.get("id"),
            "type": item.get("type"),
            "title": item.get("title"),
            "description": item.get("description"),
            "duration_sec": item.get("duration_sec"),
            "action": item.get("action"),
            "route": item.get("route"),
            "thumbnail": item.get("thumbnail"),
        }
        out.append({k: v for k, v in cleaned.items() if v is not None})
        if len(out) >= 5:
            break
    return out


_NORMAL_CHAT_PUBLIC_KEYS = {
    "session_id",
    "message_id",
    "assistant_text",
    "reply",
    "sos_triggered",
    "route_tier",
    "used_advisor_ids",
    "persona_id",
    "resource_suggestions",
    "nutrition_suggestion",
    "optional_support",
    "tts_job",
    "latency_trace",
    "pending_human_review",
    "review_reason",
    "session_rotation_summary",
    "meme_suggestion",
}


class ChatOrchestrator:
    """Own the normal non-SOS chat runtime sequence and public response shaping."""

    @staticmethod
    def resolve_route_and_advisors(
        *,
        raw_text: str,
        previous_user_messages: list[str] | None,
    ) -> tuple[str, list[str]]:
        routing = FastNeedRouter().route(
            user_message=raw_text,
            recent_user_messages=previous_user_messages or [],
        )
        advisors = AdvisorSelector().select(
            routing=routing,
            user_message=raw_text,
            recent_user_messages=previous_user_messages or [],
        )
        return routing.route_tier, list(advisors.advisor_ids)

    @staticmethod
    def resolve_route_advisors_with_reasons(
        *,
        raw_text: str,
        previous_user_messages: list[str] | None,
    ) -> tuple[str, list[str], list[str]]:
        routing = FastNeedRouter().route(
            user_message=raw_text,
            recent_user_messages=previous_user_messages or [],
        )
        advisors = AdvisorSelector().select(
            routing=routing,
            user_message=raw_text,
            recent_user_messages=previous_user_messages or [],
        )
        return routing.route_tier, list(advisors.advisor_ids), list(routing.reason_codes or [])

    @staticmethod
    def _previous_user_messages(recent_messages: list[dict[str, Any]], stored_user_content: str) -> list[str]:
        previous_user_messages = [str(m.get("content") or "") for m in recent_messages if m.get("role") == "user"]
        if previous_user_messages and previous_user_messages[-1] == stored_user_content:
            previous_user_messages = previous_user_messages[:-1]
        return previous_user_messages

    @staticmethod
    def is_short_low_risk_turn(raw_text: str, distress_score: float, *, max_message_len: int) -> bool:
        return len(raw_text.strip()) <= max_message_len and float(distress_score) < 0.5

    @staticmethod
    def prepare_request_context(
        *,
        db,
        session_id: str,
        user_id: str,
        raw_text: str,
        stored_user_content: str,
        default_message_limit: int,
        default_token_budget: int,
        fast_message_limit: int,
        fast_token_budget: int,
        fastpath_max_message_len: int,
        load_chat_context,
        evaluate_policy,
        score_sos_debug,
    ) -> "PreparedChatTurn":
        ctx = load_chat_context(
            db,
            session_id=session_id,
            user_id=user_id,
            message_limit=default_message_limit,
            message_token_budget=default_token_budget,
        )
        previous_user_messages = ChatOrchestrator._previous_user_messages(ctx.recent_messages, stored_user_content)
        policy_decision = evaluate_policy(raw_text, previous_user_messages)
        sos_debug = score_sos_debug(raw_text, recent_user_messages=previous_user_messages)

        if ChatOrchestrator.is_short_low_risk_turn(
            raw_text,
            sos_debug.distress_score,
            max_message_len=fastpath_max_message_len,
        ):
            ctx = load_chat_context(
                db,
                session_id=session_id,
                user_id=user_id,
                message_limit=fast_message_limit,
                message_token_budget=fast_token_budget,
            )
            previous_user_messages = ChatOrchestrator._previous_user_messages(ctx.recent_messages, stored_user_content)
            policy_decision = evaluate_policy(raw_text, previous_user_messages)
            sos_debug = score_sos_debug(raw_text, recent_user_messages=previous_user_messages)

        return PreparedChatTurn(
            ctx=ctx,
            previous_user_messages=previous_user_messages,
            policy_decision=policy_decision,
            sos_debug=sos_debug,
            sos_triggered=bool(sos_debug.sos_triggered),
            distress_score=float(sos_debug.distress_score),
        )

    @staticmethod
    def build_normal_response(
        *,
        session_id: str,
        snap,
        assistant_text: str,
        assistant_tone: str,
        goi_y_nhanh: list[str],
        the_dinh_kem: list[dict[str, Any]],
        voice_hint: str | None,
        routing_history: list[str] | None,
        message_id: str | None,
        optional_support: dict[str, Any] | None,
        intervention: dict[str, Any] | None = None,
        rotated_summary: str | None = None,
        route_tier_override: str | None = None,
        used_advisor_ids_override: list[str] | None = None,
        nutrition_suggestion_override: dict[str, Any] | None = None,
        meme_suggestion: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = build_normal_envelope(
            session_id,
            snap=snap,
            reply=assistant_text,
            assistant_tone=assistant_tone,
            goi_y_nhanh=goi_y_nhanh,
            the_dinh_kem=the_dinh_kem,
            voice_hint=voice_hint,
            routing_history=routing_history,
        )
        final_route_tier = _normalize_route_tier(route_tier_override or str(data.get("route_tier") or "fast"))
        final_advisor_ids = _sanitize_advisor_ids(
            used_advisor_ids_override if used_advisor_ids_override is not None else list(data.get("used_advisor_ids") or [])
        )
        final_resources = _sanitize_resource_suggestions(list(data.get("the_dinh_kem") or []))

        # Canonical chat surface fields
        data["message_id"] = message_id
        data["assistant_text"] = str(assistant_text or "")
        data["route_tier"] = final_route_tier
        data["used_advisor_ids"] = final_advisor_ids
        data["resource_suggestions"] = final_resources
        data["nutrition_suggestion"] = nutrition_suggestion_override if isinstance(nutrition_suggestion_override, dict) else None
        data["optional_support"] = optional_support if isinstance(optional_support, dict) else None
        data["tts_job"] = _extract_tts_job(intervention)
        data["meme_suggestion"] = meme_suggestion if isinstance(meme_suggestion, dict) else None
        if rotated_summary:
            data["session_rotation_summary"] = rotated_summary
        return data

    @staticmethod
    def finalize_normal_chat_response(
        data: dict[str, Any],
        *,
        latency_trace: dict[str, Any] | None = None,
        pending_human_review: bool | None = None,
        review_reason: str | None = None,
    ) -> dict[str, Any]:
        """Return the public normal-chat API shape.

        LangGraph still emits a broad legacy envelope internally. The transport
        boundary exposes only the canonical fields plus stable compatibility
        aliases required by existing clients.
        """
        public = {key: data.get(key) for key in _NORMAL_CHAT_PUBLIC_KEYS if key in data}
        assistant_text = str(public.get("assistant_text") or data.get("reply") or "")
        public["assistant_text"] = assistant_text
        public["reply"] = assistant_text
        public["route_tier"] = _normalize_route_tier(str(public.get("route_tier") or data.get("route_tier") or "fast"))
        public["used_advisor_ids"] = _sanitize_advisor_ids(
            public.get("used_advisor_ids") if isinstance(public.get("used_advisor_ids"), list) else []
        )
        if "persona_id" in data:
            public["persona_id"] = str(data.get("persona_id") or "")
        public["resource_suggestions"] = _sanitize_resource_suggestions(
            public.get("resource_suggestions") if isinstance(public.get("resource_suggestions"), list) else []
        )
        if not isinstance(public.get("nutrition_suggestion"), dict):
            public["nutrition_suggestion"] = None
        if not isinstance(public.get("optional_support"), dict):
            public["optional_support"] = None
        if not isinstance(public.get("tts_job"), dict):
            public["tts_job"] = None
        if not isinstance(public.get("meme_suggestion"), dict):
            public["meme_suggestion"] = None
        if pending_human_review is not None:
            public["pending_human_review"] = bool(pending_human_review)
        if review_reason:
            public["review_reason"] = str(review_reason)
        if latency_trace is not None:
            public["latency_trace"] = dict(latency_trace)
        elif "latency_trace" not in public:
            public["latency_trace"] = {}
        return public

    @staticmethod
    def run_non_sos_generation_handoff(
        *,
        db,
        user_id: str,
        session_id: str,
        raw_text: str,
        ctx,
        distress: float,
        policy_decision,
        fastpath_max_message_len: int,
        load_memory_context_for_turn,
        is_short_low_risk_turn,
        fetch_graph_patterns,
        load_today_meals,
        run_non_sos_turn,
        resolve_persona_id,
        policy_distress_for_persona,
        on_graph_patterns_error,
    ) -> "NonSosGenerationHandoff":
        # Legacy compatibility path only. Production normal chat should call
        # generate_normal_turn() directly via the router-owned orchestrator flow.
        memory_started = time.perf_counter()
        memory_ctx, compat_longterm = load_memory_context_for_turn(
            db,
            user_id=user_id,
            raw_text=raw_text,
            recent_messages=ctx.recent_messages,
            distress_score=distress,
        )
        memory_load_ms = int((time.perf_counter() - memory_started) * 1000)

        llm_started = time.perf_counter()
        # Neo4j is out of MVP request path. Keep patterns empty in online chat flow.
        graph_patterns: dict[str, Any] = {}
        nutrition_meals = load_today_meals(db, user_id)
        base_traits = dict(memory_ctx.traits if memory_ctx else {})
        if memory_ctx and memory_ctx.onboarding:
            base_traits.setdefault("onboarding", memory_ctx.onboarding)

        turn = run_non_sos_turn(
            user_message=raw_text,
            recent_messages=ctx.recent_messages,
            mood_today=ctx.mood_today,
            distress_score=distress,
            long_term_memories=(memory_ctx.recent_summaries if memory_ctx else compat_longterm),
            mem0_facts=(memory_ctx.mem0_facts if memory_ctx else []),
            user_traits=base_traits,
            top_triggers=(memory_ctx.top_triggers if memory_ctx else []),
            active_goals=(memory_ctx.active_goals if memory_ctx else []),
            effective_coping=(memory_ctx.effective_coping if memory_ctx else []),
            clinical_trajectory=(memory_ctx.clinical_trajectory if memory_ctx else ""),
            persona_id=resolve_persona_id(
                db,
                user_id,
                distress=policy_distress_for_persona(policy_decision, distress),
            ),
            user_id=user_id,
            session_id=session_id,
            active_memory_text="",
            graph_patterns=graph_patterns,
            nutrition_meals=nutrition_meals or None,
        )
        friend_llm_call_ms = int((time.perf_counter() - llm_started) * 1000)
        return NonSosGenerationHandoff(
            turn=turn,
            memory_load_ms=memory_load_ms,
            friend_llm_call_ms=friend_llm_call_ms,
        )

    @staticmethod
    def _advisor_registry() -> dict[str, Any]:
        return {
            "empathy_advisor": EmpathyAdvisor,
            "cbt_pattern_advisor": CBTPatternAdvisor,
            "reflection_advisor": ReflectionAdvisor,
            "strategy_resource_advisor": StrategyResourceAdvisor,
            "nutrition_support_advisor": NutritionSupportAdvisor,
        }

    @staticmethod
    def consult_advisors(
        *,
        advisor_ids: list[str],
        user_message: str,
        context_summary: str,
        timeout_ms: int = 1200,
    ) -> list[AdvisorAdvice]:
        if not advisor_ids:
            return []
        registry = ChatOrchestrator._advisor_registry()
        advisors = []
        for advisor_id in advisor_ids[:2]:
            cls = registry.get(str(advisor_id))
            if cls is None:
                continue
            advisors.append(cls())
        if not advisors:
            return []
        return AdvisorPool(advisors, timeout_ms=timeout_ms).run(
            user_message=user_message,
            context_summary=context_summary,
        )

    @staticmethod
    def compose_friend_final_text(
        *,
        user_message: str,
        context_pack,
        advisor_advice: list[AdvisorAdvice] | None = None,
    ) -> "FriendComposerResult":
        output = FriendAgent().compose(
            user_message=user_message,
            context_pack=context_pack,
            advisor_advice=advisor_advice or [],
        )
        return FriendComposerResult(
            final_text=output.final_text,
            used_advisor_ids=list(output.used_advisor_ids or []),
        )

    @staticmethod
    def _routing_history_for(route_tier: str) -> list[str]:
        if route_tier == "advisor_assisted":
            return ["advisor_pool", "friend"]
        if route_tier == "service_only":
            return ["service_only", "friend"]
        return ["friend"]

    @staticmethod
    def _assistant_tone_for(policy_decision, route_tier: str) -> str:
        action = str(getattr(policy_decision, "policy_action", "allow") or "allow")
        if action in {"supportive_continuation", "constrain_response"}:
            return "calming"
        if route_tier == "advisor_assisted":
            return "mentor"
        return "validating"

    @staticmethod
    def _attachments_from_context_pack(context_pack) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in list(getattr(context_pack, "resource_candidates", []) or []):
            if not isinstance(item, dict):
                continue
            resource_id = str(item.get("resource_id") or item.get("id") or "").strip()
            title = str(item.get("title") or "").strip()
            if not resource_id or not title:
                continue
            out.append(
                {
                    "type": "resource",
                    "id": resource_id,
                    "title": title,
                    "description": str(item.get("why_this") or item.get("description") or "").strip() or None,
                    "action": "open_resource",
                    "route": "/serene/resources",
                }
            )
            if len(out) >= 3:
                break
        return out

    @staticmethod
    def generate_normal_turn(
        *,
        user_message: str,
        context_pack,
        route_tier: str,
        planned_advisor_ids: list[str],
        apply_output_policy_or_fallback,
        policy_decision,
        route_reason_codes: list[str] | None = None,
    ) -> "GeneratedNormalTurn":
        selected_advisor_ids = planned_advisor_ids if route_tier == "advisor_assisted" else []
        interaction_need = classify_interaction_need(
            user_message,
            distress_score=float(getattr(policy_decision, "distress_score", 0.0) or 0.0),
            sos_triggered=False,
        )
        tracer = get_active_tracer()
        if tracer is not None:
            persona_context = context_pack.persona_context if isinstance(context_pack.persona_context, dict) else {}
            tracer.routing_decision(
                route_tier=route_tier,
                reason_codes=list(route_reason_codes or []),
                planned_advisor_ids=planned_advisor_ids,
                selected_advisor_ids=selected_advisor_ids,
                interaction_need=interaction_need,
                persona_id=str(persona_context.get("selected") or ""),
            )
        with start_span("advisor_selector.select", metadata={"route_tier": route_tier, "advisor_count": len(selected_advisor_ids)}):
            pass
        advisor_advice: list[AdvisorAdvice] = []
        counseling_guidance = None
        counseling_case_count = 0
        if route_tier == "advisor_assisted":
            with start_span("counseling_advisor.build", metadata={"interaction_need": interaction_need}):
                counseling_service = CounselingAdvisorService()
                counseling_guidance = counseling_service.build_guidance(
                    user_message=user_message,
                    interaction_need=interaction_need,
                    top_k=4,
                )
                counseling_case_count = int(counseling_guidance.metadata.get("case_count") or len(counseling_guidance.case_refs))
                counseling_advice = counseling_service.as_advisor_advice(guidance=counseling_guidance)
                advisor_advice.append(counseling_advice)
                if tracer is not None:
                    tracer.advisor_result(
                        advisor_id=counseling_advice.advisor_id,
                        status=str(counseling_guidance.metadata.get("source") or "used"),
                        should_use=bool(counseling_advice.should_use),
                        confidence=float(counseling_advice.confidence or 0.0),
                        evidence_count=len(counseling_advice.evidence_refs or []),
                        move_count=len(counseling_advice.suggested_response_moves or []),
                    )
                record_metric(
                    "advisor_case_retrieval_count",
                    counseling_case_count,
                    labels={"interaction_need": interaction_need, "status": str(counseling_guidance.metadata.get("source") or "unknown")},
                )
        if selected_advisor_ids:
            for advisor_id in selected_advisor_ids[:2]:
                with start_span(f"advisor.{advisor_id}.run", metadata={"advisor_id": advisor_id}):
                    advice = ChatOrchestrator.consult_advisors(
                        advisor_ids=[advisor_id],
                        user_message=user_message,
                        context_summary=str(user_message or "")[:500],
                        timeout_ms=1200,
                    )
                    advisor_advice.extend(advice)
                    if not advice:
                        record_event("advisor.timeout", metadata={"advisor_id": advisor_id, "reason_code": "empty_or_timeout"})
                        if tracer is not None:
                            tracer.advisor_result(advisor_id=advisor_id, status="empty_or_timeout")
                    else:
                        record_metric("advisor_schema_validity", 1, labels={"worker_type": "advisor", "status": "valid"})
                        if tracer is not None:
                            for item in advice:
                                tracer.advisor_result(
                                    advisor_id=item.advisor_id,
                                    status="valid",
                                    should_use=bool(item.should_use),
                                    confidence=float(item.confidence or 0.0),
                                    evidence_count=len(item.evidence_refs or []),
                                    move_count=len(item.suggested_response_moves or []),
                                )
        validator_audit: dict[str, Any] = {}
        with start_span("friend_node.respond", metadata={"route_tier": route_tier, "advisor_count": len(advisor_advice)}):
            with start_span("agent.friend.compose", metadata={"agent": "friend", "route_tier": route_tier, "advisor_count": len(advisor_advice)}):
                friend_result = ChatOrchestrator.compose_friend_final_text(
                    user_message=user_message,
                    context_pack=context_pack,
                    advisor_advice=advisor_advice,
                )
        if tracer is not None:
            tracer.event(
                "agent.friend.compose",
                output_data={
                    "used_advisor_ids": list(friend_result.used_advisor_ids or []),
                    "response_intent": "reflect",
                    "final_text_chars": len(friend_result.final_text or ""),
                },
                metadata={"route_tier": route_tier, "advisor_count": len(friend_result.used_advisor_ids or [])},
            )
        with start_span("output_validator.run"):
            assistant_text = apply_output_policy_or_fallback(
                friend_result.final_text,
                policy_decision=policy_decision,
                audit=validator_audit,
            )
        return GeneratedNormalTurn(
            assistant_text=assistant_text,
            assistant_tone=ChatOrchestrator._assistant_tone_for(policy_decision, route_tier),
            goi_y_nhanh=[],
            the_dinh_kem=ChatOrchestrator._attachments_from_context_pack(context_pack),
            route_tier=route_tier,
            used_advisor_ids=list(friend_result.used_advisor_ids if route_tier == "advisor_assisted" else []),
            routing_history=ChatOrchestrator._routing_history_for(route_tier),
            advisor_advice=advisor_advice,
            validator_audit=validator_audit,
            counseling_guidance_used=bool(counseling_guidance),
            counseling_case_count=counseling_case_count,
            interaction_need=interaction_need,
        )

    @staticmethod
    def enqueue_async_side_effects(
        *,
        db,
        user_id: str,
        session_id: str,
        assistant_message_id: str,
        tts_job_id: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, str]:
        jobs = [
            WorkerJob(
                job_id=f"mem_{assistant_message_id}",
                job_type="memory_extraction",
                user_id=user_id,
                session_id=session_id,
                payload_ref=f"messages:{assistant_message_id}",
                idempotency_key=f"memory_extraction:{assistant_message_id}",
                status="queued",
                attempt_count=0,
                trace_id=trace_id,
                request_id=request_id,
            ),
            WorkerJob(
                job_id=f"dash_{assistant_message_id}",
                job_type="dashboard_insight",
                user_id=user_id,
                session_id=session_id,
                payload_ref=f"messages:{assistant_message_id}",
                idempotency_key=f"dashboard_insight:{assistant_message_id}",
                status="queued",
                attempt_count=0,
                trace_id=trace_id,
                request_id=request_id,
            ),
            WorkerJob(
                job_id=f"analyst_{assistant_message_id}",
                job_type="analyst_event",
                user_id=user_id,
                session_id=session_id,
                payload_ref=f"messages:{assistant_message_id}",
                idempotency_key=f"analyst_event:{assistant_message_id}",
                status="queued",
                attempt_count=0,
                trace_id=trace_id,
                request_id=request_id,
            ),
        ]
        if tts_job_id:
            jobs.append(
                WorkerJob(
                    job_id=f"tts_{assistant_message_id}",
                    job_type="tts_render",
                    user_id=user_id,
                    session_id=session_id,
                    payload_ref=f"tts_job:{tts_job_id}",
                    idempotency_key=f"tts_render:{tts_job_id}",
                    status="queued",
                    attempt_count=0,
                    trace_id=trace_id,
                    request_id=request_id,
                )
            )

        outcomes: dict[str, str] = {}
        for job in jobs:
            try:
                enqueue_worker_job(db, job)
                outcomes[job.job_type] = "queued"
            except Exception:
                outcomes[job.job_type] = "enqueue_failed"
        return outcomes

    @staticmethod
    def prepare_stream_non_sos_handoff(
        *,
        db,
        user_id: str,
        raw_text: str,
        ctx,
        distress: float,
        policy_decision,
        fastpath_max_message_len: int,
        load_memory_context_for_turn,
        is_short_low_risk_turn,
        fetch_graph_patterns,
        load_today_meals,
        resolve_persona_id,
        policy_distress_for_persona,
        on_graph_patterns_error,
    ) -> "StreamNonSosHandoff":
        memory_ctx, compat_longterm = load_memory_context_for_turn(
            db,
            user_id=user_id,
            raw_text=raw_text,
            recent_messages=ctx.recent_messages,
            distress_score=distress,
        )
        # Neo4j is out of MVP request path. Keep patterns empty in online chat flow.
        graph_patterns: dict[str, Any] = {}
        nutrition_meals = load_today_meals(db, user_id)
        base_traits = dict(memory_ctx.traits if memory_ctx else {})
        if memory_ctx and memory_ctx.onboarding:
            base_traits.setdefault("onboarding", memory_ctx.onboarding)
        persona_id = resolve_persona_id(
            db,
            user_id,
            distress=policy_distress_for_persona(policy_decision, distress),
        )
        return StreamNonSosHandoff(
            memory_ctx=memory_ctx,
            compat_longterm=compat_longterm,
            graph_patterns=graph_patterns,
            nutrition_meals=nutrition_meals,
            base_traits=base_traits,
            persona_id=persona_id,
        )


@dataclass(frozen=True)
class PreparedChatTurn:
    ctx: Any
    previous_user_messages: list[str]
    policy_decision: Any
    sos_debug: Any
    sos_triggered: bool
    distress_score: float


@dataclass(frozen=True)
class NonSosGenerationHandoff:
    turn: dict[str, Any]
    memory_load_ms: int
    friend_llm_call_ms: int


@dataclass(frozen=True)
class StreamNonSosHandoff:
    memory_ctx: Any
    compat_longterm: list[str]
    graph_patterns: dict[str, Any]
    nutrition_meals: list[dict[str, Any]]
    base_traits: dict[str, Any]
    persona_id: str


@dataclass(frozen=True)
class FriendComposerResult:
    final_text: str
    used_advisor_ids: list[str]


@dataclass(frozen=True)
class GeneratedNormalTurn:
    assistant_text: str
    assistant_tone: str
    goi_y_nhanh: list[str]
    the_dinh_kem: list[dict[str, Any]]
    route_tier: str
    used_advisor_ids: list[str]
    routing_history: list[str]
    advisor_advice: list[AdvisorAdvice]
    validator_audit: dict[str, Any]
    counseling_guidance_used: bool = False
    counseling_case_count: int = 0
    interaction_need: str = "venting"
