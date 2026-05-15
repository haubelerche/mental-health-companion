"""
LangGraph non-SOS flow: DistressRouter -> AnalystNode (optional) -> FriendNode.
High-risk SOS is handled outside this graph via deterministic safety handling.
Naming reference: docs/PRD.md + docs/GLOSSARY_RUNTIME.md.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any, Iterator, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.product_constants import CHAT_AGENT_DISPLAY_NAME
from app.personas.aliases import normalize_persona_id
from app.personas.prompt_blocks import build_persona_block
from app.personas.registry import PERSONA_REGISTRY, get_persona
from app.services.chat_cost_metrics import observe_chat_usage
from app.services.langfuse_tracing import ChatTurnTracer, get_active_tracer, set_active_tracer
from app.services.exercise_catalog import build_clinic_attachment, build_resource_attachment
from app.services.fewshot_selector import build_fewshot_style_block
from app.safety.output_validator import validate_output as _safety_validate_output
from app.services.output_grounding import sanitize_grounded_reply
from app.services.response_planner import build_response_plan
from app.services.safety_scoring import build_snapshot
from app.services.neo4j_client import get_user_patterns_async

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalystBundle:
    """Typed analyst output passed via state to FriendNode. Frozen to prevent mutation."""

    clinical_note: str          # â‰¤200 chars, Vietnamese, no diagnosis
    emotional_theme: str        # snake_case, English (e.g. "academic_pressure")
    suggested_focus: str | None # optional angle for FriendNode to explore
    risk_indicators: list[str]  # â‰¤3 observable signals, no diagnosis


# ~2.5 chars per token for mixed Vietnamese/English content (conservative).
def _estimate_tokens_fast(text: str) -> int:
    return max(1, int(len(text) / 2.5))


def _log_token_budget(stage: str, *texts: str) -> int:
    """Log estimated token count for a pipeline stage and return the total."""
    total = sum(_estimate_tokens_fast(t) for t in texts)
    logger.debug("[TokenBudget] %-12s %5d est-tokens", stage, total)
    return total


class ChatGraphState(TypedDict, total=False):
    # === IMMUTABLE INPUTS (set once in middleware, never mutated by nodes) ===
    correlation_id: str
    user_id: str
    user_message: str
    recent_messages: list[dict[str, Any]]
    mood_today: dict[str, Any] | None
    long_term_memories: list[str]
    mem0_facts: list[str]
    user_traits: dict[str, Any] | None
    top_triggers: list[str]
    active_goals: list[str]
    effective_coping: list[str]
    clinical_trajectory: str | None
    distress_score: float           # FROZEN â€” distress_router must never mutate this
    active_persona_id: str
    active_memory_text: str         # optional canonical memory text; usually supplied via mem0_facts
    graph_patterns: dict            # UserPatternsResult from Neo4j, pre-fetched async; {} if unavailable
    nutrition_meals: list[dict[str, Any]] | None  # today's meal check-ins; None if none logged

    # === CONTROL FLAGS ===
    crisis_route_finalized: bool
    use_fast_friend_model: bool     # set by distress_router, read by friend_node

    # === ROUTER OUTPUT (written by distress_router) ===
    route_decision: Literal["analyst", "friend"]
    route_reason: str

    # === INTERNAL ANALYST AGENT (`AnalystNode`) OUTPUT ===
    analyst_instruction: str        # raw string â€” Phase 2 will migrate to analyst_bundle
    analyst_bundle: AnalystBundle | None  # typed output â€” populated from Phase 2 onward

    # === SERENE CONVERSATION AGENT (`FriendNode`) OUTPUT ===
    reply: str
    assistant_tone: str
    goi_y_nhanh: list[str]
    the_dinh_kem: list[dict[str, Any]]

    # === AUDIT ===
    routing_history: list[str]


PERSONA_CONFIGS: dict[str, dict[str, Any]] = {
    persona_id: {
        "label": config.display_name,
        "self_pronoun": config.pronoun_self,
        "user_pronoun": config.pronoun_user,
        "style": config.tone_summary,
        "behavior": config.prompt_contract,
        "temperature_delta": config.temperature_delta,
    }
    for persona_id, config in PERSONA_REGISTRY.items()
}
DEFAULT_PERSONA_ID = "dung_luong"
BASE_FRIEND_TEMPERATURE = 0.35
BASE_FRIEND_TEMPERATURE_FAST = 0.35


def _active_persona_config(persona_id: str) -> dict[str, Any]:
    canonical_id = normalize_persona_id(persona_id)
    return PERSONA_CONFIGS.get(canonical_id) or PERSONA_CONFIGS[DEFAULT_PERSONA_ID]


def _persona_temperature(persona_id: str, *, use_fast_model: bool, distress_score: float = 0.0) -> float:
    cfg = _active_persona_config(persona_id)
    base = BASE_FRIEND_TEMPERATURE_FAST if use_fast_model else BASE_FRIEND_TEMPERATURE
    delta = float(cfg.get("temperature_delta") or 0.0)
    effective = max(0.2, min(1.0, base + delta))
    canonical = normalize_persona_id(persona_id)
    if canonical == "dung_luong":
        if distress_score >= 0.75:
            return 0.30
        if distress_score >= 0.50:
            return 0.50
        return min(max(0.70, 0.10), 0.90)
    if canonical == "dat_le":
        # Safety gate deactivates Dat at distress >= 0.70; this keeps a stable
        # fallback if any caller bypasses the normal gate.
        if distress_score >= 0.70:
            return 0.30
        if distress_score >= 0.50:
            return 0.42
        return 0.50
    if canonical == "hau_luong":
        # Safety gate deactivates Háº­u at distress >= 0.60; this branch is the
        # belt-and-suspenders for any caller that bypassed the gate.
        if distress_score >= 0.60:
            return 0.30
        if distress_score >= 0.45:
            return 0.48
        # Effective low-risk Háº­u temperature is locked at 0.70 to keep her
        # voice-message vibe playful but grounded. Clamp into [0.1, 0.9] so a
        # future base-temperature change cannot drift the resolved value out
        # of the persona's safety band.
        return min(max(0.70, 0.10), 0.90)
    if distress_score >= 0.55:
        return 0.25
    if distress_score >= 0.35:
        return min(effective, 0.40)
    return min(effective, 0.55)


def _build_persona_block(persona_id: str) -> str:
    persona = get_persona(persona_id)
    return build_persona_block(persona)


def _persona_fallback_reply(persona_id: str, distress_score: float) -> str:
    persona_id = normalize_persona_id(persona_id)
    if persona_id == "hau_luong":
        return (
            "MÃ¬nh vá»«a bá»‹ ngáº¯t má»™t chÃºt, nhÆ°ng váº«n á»Ÿ Ä‘Ã¢y. Báº¡n cá»© nÃ³i tiáº¿p tá»«ng Ã½ ngáº¯n thÃ´i, mÃ¬nh nghe cÃ¹ng báº¡n."
        )
    if persona_id == "dat_le":
        return "TÃ´i váº«n á»Ÿ Ä‘Ã¢y cÃ¹ng báº¡n. Náº¿u báº¡n muá»‘n, tÃ´i sáº½ cÃ¹ng báº¡n Ä‘i tá»«ng bÆ°á»›c Ä‘á»ƒ nhÃ¬n rÃµ Ä‘iá»u Ä‘ang lÃ m báº¡n náº·ng nháº¥t."
    if persona_id == "dung_luong":
        return "Tá»› váº«n á»Ÿ Ä‘Ã¢y vá»›i cáº­u nÃ¨. Náº¿u cáº­u muá»‘n, mÃ¬nh gá»¡ tá»«ng chÃºt má»™t tá»« Ä‘iá»u Ä‘ang lÃ m cáº­u náº·ng lÃ²ng nháº¥t nhÃ©."
    if distress_score >= 0.6:
        return "MÃ¬nh bá»‹ ngáº¯t quÃ£ng má»™t chÃºt nhÆ°ng váº«n á»Ÿ Ä‘Ã¢y cÃ¹ng báº¡n. Báº¡n cÃ³ thá»ƒ nÃ³i tiáº¿p Ä‘iá»u Ä‘ang lÃ m báº¡n náº·ng nháº¥t lÃºc nÃ y nhÃ©?"
    return "MÃ¬nh vá»«a bá»‹ ngáº¯t quÃ£ng má»™t chÃºt, nhÆ°ng mÃ¬nh váº«n á»Ÿ Ä‘Ã¢y Ä‘á»ƒ láº¯ng nghe báº¡n."
def _trace_span(correlation_id: str, span: str, *, duration_ms: float, token_count: int = 0, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "correlation_id": correlation_id,
        "span": span,
        "duration_ms": round(duration_ms, 2),
        "token_count": int(token_count),
    }
    if extra:
        payload.update(extra)
    logger.info("[Trace] %s", payload)


# Routing thresholds â€” single source of truth for distress_router decisions.
_ANALYST_DISTRESS_THRESHOLD: float = 0.82   # distress >= this â†’ route to analyst
_FAST_MODEL_DISTRESS_THRESHOLD: float = 0.55 # distress < this (+ short msg) â†’ fast model
_FAST_MODEL_MSG_LEN_MAX: int = 220           # max message length for fast-model eligibility

_GREETING_RE = re.compile(r"\b(chao|hi|hello|helo|xin chao|yo|hey)\b", re.IGNORECASE)
_ANALYST_TRIGGER_RE = re.compile(
    r"\b("
    r"phan\s+tich|ke\s+hoach|tinh\s+toan|"
    r"khong\s+biet\s+lam\s+sao|khong\s+biet\s+phai\s+lam\s+gi|"
    r"hoang\s+mang|phuong\s+an|phuong\s+phap|giai\s+phap|y\s+tuong|"
    r"plan|strategy|analyz|solution|idea"
    r")\b",
    re.IGNORECASE,
)
_GENERIC_FOLLOWUP_RE = re.compile(
    r"(ban co the (noi|chia se|ke) them|noi them (cho|minh)|chia se them|ke them|muon noi them)",
    re.IGNORECASE,
)


_LEET_MAP: dict[str, str] = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
_LEET_RE = re.compile(r"[013457@$]")

_INJECTION_PATTERNS = re.compile(
    r"\b(ignore|forget|disregard|override|bypass|pretend|act as|you are now|new instruction|"
    r"system prompt|jailbreak|dan mode)\b",
    re.IGNORECASE,
)
_MAX_PROMPT_BLOCK_LEN = 1200


def _normalize_guard_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("Ä‘", "d")
    compact = re.sub(r"[^a-z0-9\s@$]", " ", no_accent)
    leet_normalized = _LEET_RE.sub(lambda m: _LEET_MAP.get(m.group(), m.group()), compact)
    return re.sub(r"\s+", " ", leet_normalized).strip()


def _sanitize_prompt_block(block: str) -> str:
    """Strip injection-pattern lines and cap length before inserting into system prompt."""
    if not block:
        return ""
    safe_lines: list[str] = []
    for line in block.splitlines():
        if not _INJECTION_PATTERNS.search(line):
            safe_lines.append(line)
    cleaned = "\n".join(safe_lines).strip()
    return cleaned[:_MAX_PROMPT_BLOCK_LEN]




def _is_recall_query(user_text: str) -> bool:
    normalized = _normalize_guard_text(user_text)
    recall_keywords = (
        "nho",
        "lan truoc",
        "hom qua",
        "hoi thoai truoc",
        "truoc do",
        "toi la ai",
        "minh la ai",
        "ban con nho",
        "nhac lai",
        "tiep tuc",
        "tung noi",
        "da ke",
    )
    return any(keyword in normalized for keyword in recall_keywords)


def _attachment_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("type") or ""), str(item.get("id") or ""))


def _recommended_attachments(user_message: str, distress_score: float) -> list[dict[str, Any]]:
    normalized = _normalize_guard_text(user_message)
    attachments: list[dict[str, Any]] = []

    wants_sleep_resource = any(
        keyword in normalized
        for keyword in (
            "mat ngu",
            "kho ngu",
            "ngu khong duoc",
            "thien ngu",
            "video thien",
            "sleep",
            "sleep story",
        )
    )
    wants_clinic = any(
        keyword in normalized
        for keyword in (
            "phong kham",
            "dia chi",
            "gan toi",
            "bac si",
            "chuyen gia",
            "tham van",
            "tu van tam ly",
            "tri lieu",
        )
    )
    wants_nutrition = any(
        keyword in normalized
        for keyword in (
            "an gi",
            "dinh duong",
            "an uong",
            "diet",
            "thuc don",
            "healthy food",
            "cai thien tam trang",
        )
    )

    if wants_clinic or distress_score >= 0.72:
        attachments.append(build_clinic_attachment())
    if wants_sleep_resource:
        attachments.append(build_resource_attachment("sleep_meditation"))
    elif any(keyword in normalized for keyword in ("thien", "thu gian", "nghe gi", "resource", "tai nguyen")):
        attachments.append(build_resource_attachment("calm_library"))
    if wants_nutrition:
        attachments.append(
            {
                "type": "nutrition_tip",
                "id": "daily_nutrition",
                "title": "Gá»£i Ã½ dinh dÆ°á»¡ng cho tÃ¢m tráº¡ng",
                "description": "Xem mÃ³n Äƒn hÃ´m nay vÃ  lÃ½ do giÃºp á»•n Ä‘á»‹nh cáº£m xÃºc.",
                "action": "open_resource",
                "route": "/serene/nutrition",
            }
        )

    return attachments


def _normalize_attachments(items: list[dict[str, Any]], user_message: str, distress_score: float) -> list[dict[str, Any]]:
    allowed_actions = {"open_exercise", "open_resource", "open_connect_map"}
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in [*items, *_recommended_attachments(user_message, distress_score)]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "")
        route = str(item.get("route") or "")
        if action and action not in allowed_actions:
            continue
        if route and not route.startswith("/serene/"):
            continue
        normalized = {
            "type": str(item.get("type") or "resource"),
            "id": str(item.get("id") or "suggestion"),
            "title": str(item.get("title") or "Gá»£i Ã½ tá»« Serene")[:120],
            "description": str(item.get("description") or "")[:240],
            "duration_sec": item.get("duration_sec") if isinstance(item.get("duration_sec"), int) else None,
            "action": action or "open_resource",
            "route": route or "/serene/resources",
            "thumbnail": item.get("thumbnail") if isinstance(item.get("thumbnail"), str) else None,
        }
        key = _attachment_key(normalized)
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
        if len(out) >= 3:
            break
    return out


def _default_user_quick_replies(user_message: str, distress_score: float) -> list[str]:
    lowered = user_message.lower()
    if distress_score >= 0.55:
        return [
            "MÃ¬nh Ä‘ang ráº¥t quÃ¡ táº£i, cáº­u giÃºp mÃ¬nh tá»«ng bÆ°á»›c nhÃ©.",
            "MÃ¬nh muá»‘n nÃ³i thÃªm Ä‘iá»u lÃ m mÃ¬nh sá»£ nháº¥t lÃºc nÃ y.",
            "Cáº­u hÆ°á»›ng dáº«n mÃ¬nh má»™t bÃ i thá»Ÿ ngáº¯n ngay bÃ¢y giá» nhÃ©.",
        ]
    if any(k in lowered for k in ("khong ngu", "mat ngu", "ngu")):
        return [
            "MÃ¬nh khÃ³ ngá»§ máº¥y hÃ´m nay, cáº­u giÃºp mÃ¬nh á»•n Ä‘á»‹nh láº¡i nhÃ©.",
            "MÃ¬nh muá»‘n thá»­ má»™t cÃ¡ch thÆ° giÃ£n trÆ°á»›c khi ngá»§.",
            "MÃ¬nh cáº§n má»™t káº¿ hoáº¡ch nháº¹ cho tá»‘i nay.",
        ]
    return [
        "MÃ¬nh muá»‘n ká»ƒ thÃªm vá» chuyá»‡n nÃ y.",
        "MÃ¬nh Ä‘ang tháº¥y khÃ³ chá»‹u vÃ  cáº§n cáº­u láº¯ng nghe.",
        "Cáº­u gá»£i Ã½ cho mÃ¬nh má»™t bÆ°á»›c nhá» lÃºc nÃ y nhÃ©.",
    ]


def _should_show_quick_replies(*, distress_score: float, conversation_mode: str) -> bool:
    if conversation_mode != "normal":
        return True
    return distress_score >= 0.55


def _normalize_user_quick_replies(
    replies: list[str] | None,
    *,
    user_message: str,
    distress_score: float,
) -> list[str]:
    defaults = _default_user_quick_replies(user_message, distress_score)
    if not replies:
        return defaults

    cleaned: list[str] = []
    for text in replies:
        s = str(text or "").strip()
        if not s:
            continue
        s = s.replace("\n", " ")
        if len(s) > 80:
            s = s[:77].rstrip() + "..."
        cleaned.append(s)

    if len(cleaned) < 3:
        return defaults

    # Ensure quick replies are in user's voice (first person) instead of asking the user questions.
    forbidden_in_quick_reply = {"tao", "may", "mi", "nguoi"}
    user_voice = [
        s
        for s in cleaned
        if re.search(r"\b(minh|em|toi)\b", _normalize_guard_text(s), re.IGNORECASE)
        and not any(tok in _normalize_guard_text(s).split() for tok in forbidden_in_quick_reply)
    ]
    if len(user_voice) >= 3:
        return user_voice[:3]
    return defaults


def _build_mentalchat_examples(
    user_message: str, api_key: str, *, distress_score: float = 0.0
) -> str:
    """Legacy raw counseling examples prompt block.

    Disabled by default because raw counseling responses are source material, not
    user-facing generation context. Advisor-assisted chat must use approved
    app.advisor_case_library rows instead.
    """
    settings = get_settings()
    if not settings.counseling_examples_prompt_enabled:
        logger.debug("mentalchat examples prompt injection disabled")
        return ""
    if not user_message or not api_key:
        return ""
    if distress_score < 0.55:
        return ""

    top_k = 3 if distress_score >= 0.72 else 2

    try:
        from app.services.counseling_retriever import get_similar_counseling_examples

        examples = get_similar_counseling_examples(
            user_message, api_key=api_key, top_k=top_k, min_similarity=0.75
        )
        if not examples:
            from app.services.mental_chat_retriever import MentalChatRetriever

            retriever = MentalChatRetriever.instance()
            if retriever.is_ready:
                examples = retriever.search(user_message, top_k=top_k, api_key=api_key)

        if not examples:
            return ""
        lines = ["--- VÃ­ dá»¥ tham kháº£o tá»« chuyÃªn gia tÃ¢m lÃ½ ---"]
        for i, ex in enumerate(examples, 1):
            instr = str(ex.get("instruction") or "").strip()[:300]
            resp = str(ex.get("response") or "").strip()[:400]
            if instr and resp:
                lines.append(f"[{i}] TÃ¬nh huá»‘ng: {instr}")
                lines.append(f"    CÃ¡ch tiáº¿p cáº­n: {resp}")
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception as exc:
        logger.debug("mentalchat examples skipped: %s", exc)
        return ""


def _build_friend_context(state: ChatGraphState, distress_score: float | None = None) -> str:
    """Build Friend context in 3 tiers based on distress to minimise token spend.

    Tier 1 â€” low  (distress < 0.42, short msg): handled by caller via _build_personality_hint.
    Tier 2 â€” mid  (0.42 â‰¤ distress < 0.65): transcript (3 turns) + mood + traits + analyst note.
    Recall turns are memory-sensitive even when distress is low, so they include a small memory slice.
    Tier 3 â€” high (distress â‰¥ 0.65): full context (6 turns + mem0 + long-term + profile).
    """
    d = distress_score if distress_score is not None else float(state.get("distress_score") or 0.0)

    mood = state.get("mood_today") or {}
    mood_line = ""
    if mood:
        mood_line = f"Mood: {mood.get('mood', '')} {mood.get('emoji', '')}."

    analyst_hint = state.get("analyst_instruction") or ""
    is_recall_turn = _is_recall_query(str(state.get("user_message") or ""))
    memory_lines = [str(item or "").strip() for item in (state.get("long_term_memories") or []) if str(item or "").strip()]
    memory_blob = "\n".join(f"- {item}" for item in memory_lines[:3]) if memory_lines else ""
    mem0_facts = [str(item or "").strip() for item in (state.get("mem0_facts") or []) if str(item or "").strip()]
    mem0_blob = "\n".join(f"- {item}" for item in mem0_facts[:5]) if mem0_facts else ""

    # â”€â”€ Tier 2: medium distress â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if d < 0.65:
        transcript_lines: list[str] = []
        for turn in (state.get("recent_messages") or [])[-3:]:
            role = str(turn.get("role", "")).strip() or "unknown"
            content = str(turn.get("content", "")).strip()
            if content:
                # Truncate long turns to keep context tight
                transcript_lines.append(f"{role}: {content[:200]}")
        transcript = "\n".join(transcript_lines) if transcript_lines else "(chÆ°a cÃ³ lá»‹ch sá»­)"
        traits = dict(state.get("user_traits") or {})
        tone_hint = str(traits.get("preferred_tone") or "").strip() or "dá»‹u dÃ ng"
        parts = [f"Distress: {d:.2f}"]
        if mood_line:
            parts.append(mood_line)
        parts.append(f"Tone: {tone_hint}")
        if is_recall_turn and mem0_blob:
            parts.append(f"KÃ½ á»©c liÃªn quan:\n{mem0_blob}")
        if is_recall_turn and memory_blob:
            parts.append(f"TÃ³m táº¯t session gáº§n:\n{memory_blob}")
        parts.append(f"Lá»‹ch sá»­ (3 lÆ°á»£t):\n{transcript}")
        if analyst_hint:
            parts.append(f"Analyst: {analyst_hint[:400]}")
        return "\n".join(parts)

    # â”€â”€ Tier 3: high distress â€” full context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    transcript_lines_full: list[str] = []
    for turn in (state.get("recent_messages") or [])[-6:]:
        role = str(turn.get("role", "")).strip() or "unknown"
        content = str(turn.get("content", "")).strip()
        if content:
            transcript_lines_full.append(f"{role}: {content}")
    transcript_full = "\n".join(transcript_lines_full) if transcript_lines_full else "(chÆ°a cÃ³ lá»‹ch sá»­)"

    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    coping = [str(item or "").strip() for item in (state.get("effective_coping") or []) if str(item or "").strip()]
    goals = [str(item or "").strip() for item in (state.get("active_goals") or []) if str(item or "").strip()]
    traits_full = dict(state.get("user_traits") or {})
    preferred_tone = str(traits_full.get("preferred_tone") or "").strip() or "(chÆ°a rÃµ)"
    communication_style = str(traits_full.get("communication_style") or "").strip() or ""
    trajectory = str(state.get("clinical_trajectory") or "").strip()

    sections: list[str] = [f"Distress: {d:.2f}"]
    if mood_line:
        sections.append(mood_line)
    profile_parts = [f"Tone: {preferred_tone}"]
    if communication_style:
        profile_parts.append(f"Phong cÃ¡ch: {communication_style}")
    if top_triggers:
        profile_parts.append(f"Trigger: {', '.join(top_triggers[:3])}")
    if coping:
        profile_parts.append(f"Coping: {', '.join(coping[:3])}")
    if goals:
        profile_parts.append(f"Má»¥c tiÃªu: {'; '.join(goals[:2])}")
    if trajectory:
        profile_parts.append(f"HÃ nh trÃ¬nh: {trajectory}")
    sections.append(" | ".join(profile_parts))
    if mem0_blob:
        sections.append(f"KÃ½ á»©c liÃªn quan:\n{mem0_blob}")
    if memory_blob:
        sections.append(f"TÃ³m táº¯t session gáº§n:\n{memory_blob}")
    sections.append(f"Lá»‹ch sá»­:\n{transcript_full}")
    if analyst_hint:
        sections.append(f"Analyst: {analyst_hint[:800]}")
    return "\n".join(sections)


def _build_personality_hint(state: ChatGraphState) -> str:
    traits = dict(state.get("user_traits") or {})
    preferred_tone = str(traits.get("preferred_tone") or "").strip()
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    trigger_hint = ", ".join(top_triggers[:2]) if top_triggers else "chÆ°a rÃµ trigger"
    tone_hint = preferred_tone or "dá»‹u dÃ ng"
    return f"[User profile: tone={tone_hint}; hay gáº·p={trigger_hint}]"


def _recent_transcript_hint(state: ChatGraphState, *, max_turns: int = 3, max_chars_per_turn: int = 220) -> str:
    lines: list[str] = []
    for turn in (state.get("recent_messages") or [])[-max_turns:]:
        role = str(turn.get("role") or "").strip()
        content = str(turn.get("content") or "").strip()
        if not role or not content:
            continue
        lines.append(f"{role}: {content[:max_chars_per_turn]}")
    return "\n".join(lines)


def _detect_hardship_signals(text: str) -> list[str]:
    normalized = _normalize_guard_text(text)
    cues: list[tuple[str, tuple[str, ...]]] = [
        ("mat_ngu", ("khong ngu", "mat ngu", "thuc dem", "ngu khong duoc")),
        ("tai_chinh", ("tien", "luong", "no", "thue", "chi phi")),
        ("gia_dinh", ("gia dinh", "con cai", "bo me", "bao hieu")),
        ("kiet_suc", ("kiet suc", "qua tai", "met moi", "ap luc", "that vong")),
        ("co_don", ("co don", "khong ai", "mot minh", "khong duoc hieu")),
    ]
    matches: list[str] = []
    for key, keywords in cues:
        if any(word in normalized for word in keywords):
            matches.append(key)
    return matches


def _enforce_reply_quality(reply: str, user_message: str, distress_score: float) -> str:
    return reply

def _enforce_reply_quality(reply: str, user_message: str, distress_score: float) -> str:
    return reply


def _sanitize_assistant_reply(reply: str) -> str:
    """Lightweight cleanup for assistant text before grounding."""
    text = str(reply or "").strip()
    text = re.sub(r"`{3,}.*?`{3,}", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _should_skip_cold_start_profile(
    *,
    user_message: str,
    distress_score: float,
    mem0_facts: list[str],
    long_term_memories: list[str],
    user_traits: dict[str, Any],
) -> bool:
    """Return True if cold-start LLM screening should be skipped for this turn.

    Skipped when the user already has warm memory/traits (screener not needed),
    or when the message is trivially short with low distress (not worth the LLM cost).
    """
    if mem0_facts or long_term_memories or user_traits:
        return True
    word_count = len(user_message.split())
    return word_count <= 4 and distress_score < 0.3


def _apply_cold_start_profile(
    *,
    settings,
    user_message: str,
    distress_score: float,
    user_traits: dict[str, Any] | None,
    mem0_facts: list[str] | None,
    long_term_memories: list[str] | None,
) -> tuple[float, dict[str, Any], str]:
    if _should_skip_cold_start_profile(
        user_message=user_message,
        distress_score=distress_score,
        user_traits=user_traits,
        mem0_facts=mem0_facts,
        long_term_memories=long_term_memories,
    ):
        return distress_score, dict(user_traits or {}), ""

    is_cold_start = (
        not dict(user_traits or {})
        and not list(mem0_facts or [])
        and not list(long_term_memories or [])
    )
    if not is_cold_start or not settings.openai_api_key:
        return distress_score, dict(user_traits or {}), ""
    try:
        from app.services.cold_start_screener import ColdStartScreener

        profile = ColdStartScreener.instance().screen(
            user_message,
            api_key=settings.openai_api_key,
        )
        merged_traits = dict(user_traits or {})
        merged_traits.update(profile.warm_traits or {})
        # distress_score is frozen after middleware â€” do not apply cold-start delta (Phase 4).
        return distress_score, merged_traits, str(profile.screening_note or "").strip()
    except Exception as exc:
        logger.debug("cold-start profile skipped: %s", exc)
        return distress_score, dict(user_traits or {}), ""


def _should_skip_cold_start_profile(
    *,
    user_message: str,
    distress_score: float,
    user_traits: dict[str, Any] | None,
    mem0_facts: list[str] | None,
    long_term_memories: list[str] | None,
) -> bool:
    if dict(user_traits or {}) or list(mem0_facts or []) or list(long_term_memories or []):
        return True
    if _is_recall_query(user_message):
        return True
    normalized = _normalize_guard_text(user_message)
    if distress_score >= 0.35:
        return False
    meaningful_signals = _detect_hardship_signals(user_message)
    if meaningful_signals:
        return False
    return len(normalized) < 40


def _legacy_supervisor_route(
    *,
    distress: float,
    msg: str,
    mood: str | None,
    crisis_finalized: bool,
) -> str:
    """Return the route the old supervisor_node would have chosen.

    Used exclusively for Phase 1 shadow-compare logging. Remove when cutover is confirmed.
    """
    if crisis_finalized:
        return "friend"
    if distress >= _ANALYST_DISTRESS_THRESHOLD:
        return "analyst"
    if mood in {"stressed", "restless", "melancholic"} and distress >= 0.58:
        return "analyst"
    if _ANALYST_TRIGGER_RE.search(msg.lower()):
        return "analyst"
    return "friend"


def distress_router(state: ChatGraphState) -> dict[str, Any]:
    """Route each non-SOS turn to analyst or friend using 3 priority-ordered rules.

    Priority 1 â€” crisis_route_finalized override (belt-and-suspenders)
    Priority 2 â€” distress_score >= _ANALYST_DISTRESS_THRESHOLD
    Priority 3 â€” message matches _ANALYST_TRIGGER_RE (explicit analysis intent)
    Default    â€” friend
    """
    span_start = time.perf_counter()
    correlation_id = str(state.get("correlation_id") or "")
    hist = list(state.get("routing_history") or [])
    hist.append("distress_router")

    msg = (state.get("user_message") or "").strip()
    distress = float(state.get("distress_score") or 0.0)
    crisis_finalized = bool(state.get("crisis_route_finalized"))

    if crisis_finalized:
        route, reason = "friend", "crisis_route_finalized"
    elif distress >= _ANALYST_DISTRESS_THRESHOLD:
        route, reason = "analyst", "high_distress"
    elif len(msg) <= 8 and _GREETING_RE.search(msg):
        route, reason = "friend", "short_greeting"
    elif _ANALYST_TRIGGER_RE.search(msg):
        route, reason = "analyst", "explicit_analysis"
    else:
        route, reason = "friend", "default"

    use_fast = distress < _FAST_MODEL_DISTRESS_THRESHOLD and len(msg) <= _FAST_MODEL_MSG_LEN_MAX
    if use_fast:
        logger.info(
            "[FastPath] corr=%s distress=%.2f msg_len=%d model=fast",
            correlation_id, distress, len(msg),
        )

    # Shadow compare: log disagreements with legacy supervisor for Phase 1 validation.
    mood_val = (state.get("mood_today") or {}).get("mood")
    legacy = _legacy_supervisor_route(
        distress=distress, msg=msg, mood=mood_val, crisis_finalized=crisis_finalized
    )
    if legacy != route:
        logger.info(
            "[ShadowCompare] correlation_id=%s distress=%.2f legacy_route=%s new_route=%s reason=%s",
            correlation_id, distress, legacy, route, reason,
        )

    _trace_span(
        correlation_id,
        "distress_router_decision",
        duration_ms=(time.perf_counter() - span_start) * 1000,
        extra={"route": route, "reason": reason, "distress_score": distress, "use_fast": use_fast},
    )
    tracer = get_active_tracer()
    if tracer:
        tracer.event(
            "distress_router_decision",
            input_data={"distress_score": distress, "message_len": len(msg)},
            output_data={"route_decision": route, "route_reason": reason, "use_fast_friend_model": use_fast},
            metadata={"agent": "router", "route_decision": route, "route_reason": reason},
        )
    return {
        "routing_history": hist,
        "route_decision": route,
        "route_reason": reason,
        "use_fast_friend_model": use_fast,
    }


def supervisor_node(state: ChatGraphState) -> dict[str, Any]:
    """Compatibility shim for golden eval tests; delegates to distress_router."""
    routed = distress_router(state)
    return {
        "supervisor_route": routed.get("route_decision"),
        "routing_history": list(routed.get("routing_history") or []),
    }


def route_after_distress_router(state: ChatGraphState) -> str:
    return "analyst" if state.get("route_decision") == "analyst" else "friend"


def _trace_analyst_route_decision(state: ChatGraphState) -> None:
    tracer = get_active_tracer()
    if tracer is None:
        return
    route = str(state.get("route_decision") or "friend")
    reason = str(state.get("route_reason") or "")
    tracer.event(
        "analyst_route_decision",
        input_data={
            "distress_score": float(state.get("distress_score") or 0.0),
            "message_len": len(str(state.get("user_message") or "")),
        },
        output_data={
            "agent": "analyst",
            "status": "scheduled" if route == "analyst" else "skipped",
            "route_decision": route,
            "route_reason": reason,
        },
        metadata={
            "agent": "analyst",
            "status": "scheduled" if route == "analyst" else "skipped",
            "route_reason": reason,
        },
        as_type="agent",
    )



def analyst_node(state: ChatGraphState) -> dict[str, Any]:
    span_start = time.perf_counter()
    correlation_id = str(state.get("correlation_id") or "")
    user_id = str(state.get("user_id") or "")
    settings = get_settings()
    hist = list(state.get("routing_history") or [])
    hist.append("analyst")

    mood_note = ""
    m = state.get("mood_today")
    if m:
        mood_note = f"Mood hÃ´m nay: {m.get('mood', '')} {m.get('emoji', '')}."

    ctx_lines = []
    for turn in (state.get("recent_messages") or [])[-6:]:
        ctx_lines.append(f"{turn.get('role', '')}: {turn.get('content', '')}")
    transcript = "\n".join(ctx_lines)

    instruction = (
        "Báº¡n lÃ  Analyst áº©n danh. Vai trÃ²: phÃ¢n tÃ­ch ná»™i bá»™, khÃ´ng nÃ³i chuyá»‡n vá»›i user. "
        "Tráº£ lá»i JSON má»™t dÃ²ng há»£p lá»‡ vá»›i 4 khÃ³a báº¯t buá»™c: "
        '`clinical_note` (str â‰¤200 chars, tiáº¿ng Viá»‡t, khÃ´ng cháº©n Ä‘oÃ¡n), '
        '`emotional_theme` (str snake_case tiáº¿ng Anh, vÃ­ dá»¥: "academic_pressure"), '
        "`suggested_focus` (str hoáº·c null â€” gá»£i Ã½ chá»§ Ä‘á» Friend cÃ³ thá»ƒ khai thÃ¡c), "
        "`risk_indicators` (list[str] â‰¤3 tÃ­n hiá»‡u quan sÃ¡t Ä‘Æ°á»£c, khÃ´ng cháº©n Ä‘oÃ¡n). "
        "KhÃ´ng táº¡o reply cho user. KhÃ´ng nháº¯c PII. KhÃ´ng dÃ¹ng 'tráº§m cáº£m/rá»‘i loáº¡n' nhÆ° cháº©n Ä‘oÃ¡n. "
        'Náº¿u khÃ´ng Ä‘á»§ context â†’ {"clinical_note":"","emotional_theme":"unclear","suggested_focus":null,"risk_indicators":[]}'
    )
    mem0_facts = [str(item or "").strip() for item in (state.get("mem0_facts") or []) if str(item or "").strip()]
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    effective_coping = [str(item or "").strip() for item in (state.get("effective_coping") or []) if str(item or "").strip()]
    context_lines = []
    if mem0_facts:
        context_lines.append(f"KÃ½ á»©c liÃªn quan: {'; '.join(mem0_facts[:3])}")
    if top_triggers:
        context_lines.append(f"Trigger láº·p láº¡i: {', '.join(top_triggers[:3])}")
    if effective_coping:
        context_lines.append(f"Coping tá»«ng giÃºp: {', '.join(effective_coping[:3])}")
    trajectory = str(state.get("clinical_trajectory") or "").strip()
    if trajectory:
        context_lines.append(f"HÃ nh trÃ¬nh tÃ¢m lÃ½: {trajectory}")
    profile_context = "\n".join(context_lines) if context_lines else "(chÆ°a cÃ³ profile context)"
    nutrition_meals = state.get("nutrition_meals") or []
    if nutrition_meals:
        meal_lines = "\n".join(
            f"- {m.get('slot', '?')}: {m.get('items') or '(chÆ°a ghi)'}"
            for m in nutrition_meals
        )
        nutrition_block = f"Bá»¯a Äƒn hÃ´m nay:\n{meal_lines}\n"
    else:
        nutrition_block = ""
    user_payload = (
        f"{profile_context}\n"
        f"{mood_note}\n"
        f"{nutrition_block}"
        f"Lá»‹ch sá»­ gáº§n Ä‘Ã¢y:\n{transcript}\n"
        f"Tin má»›i: {state.get('user_message', '')}"
    )

    # Read Neo4j patterns pre-fetched by the async caller
    _graph_raw: dict = state.get("graph_patterns") or {}
    _graph_context_used = _graph_raw.get("available", False) and any(
        _graph_raw.get(k) for k in ("triggers", "emotions", "coping")
    )
    _graph_context_block = ""
    if _graph_context_used:
        _t = ", ".join(
            f"{x['name']} (Ã—{x['count']})"
            for x in _graph_raw.get("triggers", [])
            if x.get("count")
        ) or "chÆ°a ghi nháº­n"
        _e = ", ".join(x["name"] for x in _graph_raw.get("emotions", [])) or "chÆ°a ghi nháº­n"
        _c = ", ".join(
            f"{x['name']} (hiá»‡u quáº£={x['effectiveness']:.2f})"
            for x in _graph_raw.get("coping", [])
            if x.get("effectiveness") is not None
        ) or "chÆ°a ghi nháº­n"
        _graph_context_block = (
            f"\n\n[Lá»‹ch sá»­ hÃ nh vi tá»« Neo4j â€” derived context]\n"
            f"TÃ¡c nhÃ¢n hay gáº·p: {_t}\n"
            f"Cáº£m xÃºc hay gáº·p: {_e}\n"
            f"Chiáº¿n lÆ°á»£c Ä‘á»‘i phÃ³ Ä‘Ã£ thá»­: {_c}"
        )
    logger.debug("analyst_node graph_context_used=%s", _graph_context_used)
    instruction = instruction + _sanitize_prompt_block(_graph_context_block)

    analyst_in_tokens = _log_token_budget("analyst_in", instruction, user_payload)

    text_out = ""
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 2.5))
            resp = client.chat.completions.create(
                model=settings.openai_model_analyst,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user_payload},
                ],
            )
            text_out = (resp.choices[0].message.content or "").strip()
            analyst_out_tokens = _log_token_budget("analyst_out", text_out)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                observe_chat_usage(
                    input_tokens=int(getattr(usage, "prompt_tokens", analyst_in_tokens) or analyst_in_tokens),
                    output_tokens=int(getattr(usage, "completion_tokens", analyst_out_tokens) or analyst_out_tokens),
                )
            _tracer = get_active_tracer()
            if _tracer:
                _in = int(getattr(usage, "prompt_tokens", analyst_in_tokens) or analyst_in_tokens) if usage else analyst_in_tokens
                _out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
                _tracer.generation(
                    "analyst",
                    model=settings.openai_model_analyst,
                    input_messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": user_payload},
                    ],
                    output=text_out,
                    input_tokens=_in,
                    output_tokens=_out,
                )
        except Exception as exc:
            logger.warning("analyst llm failed: %s", exc)
            text_out = '{"clinical_note":"","emotional_theme":"unclear","suggested_focus":null,"risk_indicators":[]}'
    else:
        text_out = '{"clinical_note":"NgÆ°á»i dÃ¹ng Ä‘ang chia sáº» cÄƒng tháº³ng.","emotional_theme":"general_distress","suggested_focus":"Báº¡n muá»‘n ká»ƒ thÃªm vá» Ä‘iá»u Ä‘Ã³ khÃ´ng?","risk_indicators":[]}'

    import json as _json
    _bundle: AnalystBundle
    try:
        _raw = text_out
        _m = re.search(r"\{.*\}", _raw, re.DOTALL)
        if _m:
            _raw = _m.group(0)
        _parsed = _json.loads(_raw)
        _bundle = AnalystBundle(
            clinical_note=str(_parsed.get("clinical_note") or "")[:200],
            emotional_theme=str(_parsed.get("emotional_theme") or "unclear"),
            suggested_focus=_parsed.get("suggested_focus") or None,
            risk_indicators=[str(r) for r in (_parsed.get("risk_indicators") or [])][:3],
        )
    except Exception as _parse_exc:
        logger.warning("analyst bundle parse failed corr=%s: %s", correlation_id, _parse_exc)
        _bundle = AnalystBundle(clinical_note="", emotional_theme="unclear", suggested_focus=None, risk_indicators=[])
    _trace_span(
        correlation_id,
        "analyst_generate",
        duration_ms=(time.perf_counter() - span_start) * 1000,
        token_count=analyst_in_tokens + _estimate_tokens_fast(text_out),
    )
    return {
        "routing_history": hist,
        "analyst_bundle": _bundle,
    }


def _postprocess_friend_reply(
    raw_reply: str,
    user_text: str,
    distress_score: float,
    mentalchat_block: str,
    correlation_id: str,
    persona_id: str = DEFAULT_PERSONA_ID,
):
    """Enforce quality, sanitize, ground, and append distress follow-up if needed.

    Single authority for all post-LLM reply processing. Used by both friend_node
    and the streaming path â€” changes here apply everywhere.
    Returns (safe_reply: str, grounded_result) where grounded_result has
    .grounded (bool) and .reasons (list[str]).
    """
    # Keep persona-specific voice intact; aggressive rewrite is only for default/family tones
    # or when the model returns empty content.
    persona_id = normalize_persona_id(persona_id)
    # Keep model output for all personas. Full template replace via
    # _enforce_reply_quality made short / casual turns read as generic scripted empathy.
    if str(raw_reply or "").strip():
        improved = str(raw_reply).strip()
    else:
        improved = _enforce_reply_quality(raw_reply, user_text, distress_score)
    safe = _sanitize_assistant_reply(improved)
    grounded = sanitize_grounded_reply(safe, mentalchat_block)
    safe = grounded.reply
    if distress_score >= 0.6 and "?" not in safe and persona_id == DEFAULT_PERSONA_ID:
        safe = safe.rstrip(".! ") + ". Báº¡n cÃ³ thá»ƒ nÃ³i thÃªm Ä‘iá»u Ä‘ang lÃ m báº¡n tháº¥y tá»‡ nháº¥t lÃºc nÃ y khÃ´ng?"
    logger.info(
        "[FriendPostProcess] corr=%s grounded=%s quality_changed=%s",
        correlation_id,
        grounded.grounded,
        improved != raw_reply,
    )
    return safe, grounded


def _enforce_persona_identity(reply: str, persona_id: str) -> str:
    """Normalize self-introduction so it follows active persona config, never generic 'Friend'."""
    text = str(reply or "").strip()
    if not text:
        return text
    cfg = _active_persona_config(persona_id)
    label = str(cfg.get("label") or "").strip()
    self_pronoun = str(cfg.get("self_pronoun") or "mÃ¬nh").strip()
    user_pronoun = str(cfg.get("user_pronoun") or "báº¡n").strip()
    self_cap = self_pronoun[:1].upper() + self_pronoun[1:] if self_pronoun else "MÃ¬nh"
    intro = f"{self_cap} lÃ  [{label}] cá»§a {user_pronoun} nÃ¨. "

    text = re.sub(
        r"^\s*(friend)\b[\s,:-]*",
        intro,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*\b(mÃ¬nh|toi|tÃ´i|tui)\s+(lÃ |la|tÃªn lÃ |ten la)\s+(friend)\b[\s,:-]*",
        intro,
        text,
        flags=re.IGNORECASE,
    )
    return text


# Distress/length thresholds for the ultra-fast prompt path.
_ULTRAFAST_DISTRESS_MAX: float = 0.20
_ULTRAFAST_MSG_LEN_MAX: int = 50


def _is_ultrafast_eligible(*, distress_score: float, user_message: str) -> bool:
    """True when the turn is low-risk casual chat that needs no planning/fewshot overhead."""
    return distress_score < _ULTRAFAST_DISTRESS_MAX and len(user_message.strip()) < _ULTRAFAST_MSG_LEN_MAX


def _build_ultrafast_messages(
    state: ChatGraphState,
    distress_score: float,
    persona_id: str,
) -> tuple[list[dict[str, str]], int]:
    """Build a minimal (~550-token) message list for ultra-fast casual turns.

    Skips plan_hint, fewshot examples, mentalchat block, and memory hint.
    Truncates the persona block to identity + key rules only to stay within budget.
    """
    # Keep first ~700 chars of persona block: covers identity, pronouns, tone, and top style rules.
    full_persona_block = _build_persona_block(persona_id)
    persona_block = full_persona_block[:700].rstrip()
    emoji_line = (
        "Vá»›i DÅ©ng á»Ÿ low-risk, Ä‘Æ°á»£c phÃ©p dÃ¹ng tá»‘i Ä‘a 1 emoji náº¿u há»£p ngá»¯ cáº£nh."
        if persona_id == "dung_luong"
        else "KhÃ´ng dÃ¹ng emoji."
    )
    ultrafast_base = (
        "Báº¡n lÃ  Serene, trá»£ lÃ½ Ä‘á»“ng hÃ nh tinh tháº§n báº±ng tiáº¿ng Viá»‡t tá»± nhiÃªn. "
        "Viáº¿t nhÆ° ngÆ°á»i Viá»‡t tráº» nháº¯n tin: ngáº¯n 2â€“3 cÃ¢u, Ä‘Ãºng ngá»¯ cáº£nh, khÃ´ng vÄƒn máº«u, khÃ´ng markdown. "
        "Äá»c tÃ­n hiá»‡u cáº£m xÃºc ngáº§m vÃ  pháº£n há»“i vÃ o tÃ¬nh huá»‘ng; khÃ´ng nháº¡i láº¡i lá»i user. "
        "Tá»‘i Ä‘a má»™t cÃ¢u há»i. KhÃ´ng dÃ¹ng cÃ¢u khuÃ´n máº«u vá» cáº£m xÃºc. "
        + emoji_line + " "
        "KhÃ´ng dÃ¹ng ngÃ´n ngá»¯ possessive, exclusive, romantic hoáº·c dependency-building. "
        "KhÃ´ng tá»± xÆ°ng lÃ  Friend hay thá»±c thá»ƒ con ngÆ°á»i ngoÃ i Ä‘á»i. "
        "Tráº£ lá»i JSON: reply, assistant_tone (supportive|validating|cheerful|calming|neutral), "
        "goi_y_nhanh (3 chuá»—i ngáº¯n), the_dinh_kem ([])."
    )
    persona_priority = (
        "Æ¯U TIÃŠN: tuÃ¢n thá»§ persona block ngay sau Ä‘Ã¢y trÆ°á»›c khi táº¡o reply.\n"
        f"{persona_block}"
    )
    user_text = str(state.get("user_message") or "")
    short_history = _recent_transcript_hint(state, max_turns=2, max_chars_per_turn=120)
    personality = _build_personality_hint(state)
    if short_history:
        user_payload = f"{personality}\nLá»‹ch sá»­:\n{short_history}\nTin nháº¯n má»›i:\n{user_text}"
    else:
        user_payload = f"{personality}\n{user_text}"

    msgs: list[dict[str, str]] = [
        {"role": "system", "content": ultrafast_base},
        {"role": "system", "content": persona_priority},
        {"role": "user", "content": user_payload},
    ]
    token_est = _log_token_budget("ultrafast_in", ultrafast_base, persona_priority, user_payload)
    return msgs, token_est


def friend_node(state: ChatGraphState) -> dict[str, Any]:
    span_start = time.perf_counter()
    correlation_id = str(state.get("correlation_id") or "")
    settings = get_settings()
    hist = list(state.get("routing_history") or [])
    hist.append("friend")

    user_text = state.get("user_message", "")
    distress_now = float(state.get("distress_score") or 0.0)
    persona_id = str(state.get("active_persona_id") or DEFAULT_PERSONA_ID)
    persona_block = _build_persona_block(persona_id)
    use_fast_model = bool(state.get("use_fast_friend_model")) and distress_now < 0.55
    friend_temperature = _persona_temperature(
        persona_id,
        use_fast_model=use_fast_model,
        distress_score=distress_now,
    )
    preferred_friend_model = (
        settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
    )

    # â”€â”€ Ultra-fast path: minimal prompt for casual low-distress turns â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _ultrafast = _is_ultrafast_eligible(distress_score=distress_now, user_message=user_text)
    if _ultrafast:
        friend_messages, friend_in_tokens = _build_ultrafast_messages(state, distress_now, persona_id)
        safe_mentalchat_block = ""
        logger.info(
            "[UltraFast] corr=%s distress=%.2f msg_len=%d",
            correlation_id, distress_now, len(user_text),
        )
    else:
        # â”€â”€ Normal path: full prompt assembly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        mentalchat_block = _build_mentalchat_examples(
            user_text, settings.openai_api_key or "", distress_score=distress_now
        )
        safe_mentalchat_block = _sanitize_prompt_block(mentalchat_block)
        # Skip fewshot examples below distress 0.30 â€” saves ~300 tokens on casual turns.
        style_fewshot_block = (
            ""
            if distress_now < 0.30
            else _sanitize_prompt_block(
                build_fewshot_style_block(
                    user_message=user_text,
                    risk_mode="elevated" if distress_now >= 0.55 else "normal",
                    distress_score=distress_now,
                    persona_id=persona_id,
                )
            )
        )
        generation_plan = build_response_plan(
            user_message=user_text,
            candidate_text="",
            distress_score=distress_now,
            persona_id=persona_id,
            sos_triggered=False,
        )
        plan_hint = (
            "[RESPONSE PLAN - render naturally, do not expose]\n"
            f"interaction_need: {generation_plan.interaction_need}\n"
            f"emotional_state: {generation_plan.emotional_state}\n"
            f"situation_read: {generation_plan.situation_read}\n"
            f"stance: {generation_plan.stance}\n"
            f"allowed_moves: {', '.join(generation_plan.allowed_moves)}\n"
            f"forbidden_moves: {', '.join(generation_plan.forbidden_moves)}\n"
            f"advice_allowed: {generation_plan.advice_allowed}\n"
            f"safety_mode: {generation_plan.safety_mode}"
        )
        memory_text = str(state.get("active_memory_text") or "").strip()
        memory_hint = (
            f"[KÃ½ á»©c liÃªn quan tá»« mem0_memories â€” cÃ¡ nhÃ¢n hÃ³a cÃ¢u tráº£ lá»i dá»±a trÃªn Ä‘iá»u nÃ y, khÃ´ng nháº¯c láº¡i nguyÃªn vÄƒn]\n{memory_text}\n"
            if memory_text else ""
        )
        emoji_policy_line = (
            "Vá»›i DÅ©ng á»Ÿ low-risk (distress < 0.5), Ä‘Æ°á»£c phÃ©p dÃ¹ng tá»‘i Ä‘a 1 emoji náº¿u há»£p ngá»¯ cáº£nh; "
            "ngoÃ i Ä‘iá»u kiá»‡n Ä‘Ã³ thÃ¬ khÃ´ng dÃ¹ng emoji."
            if persona_id == "dung_luong"
            else "KhÃ´ng dÃ¹ng emoji trong chat cáº£m xÃºc."
        )
        distress_length_hint = (
            "Pháº£n há»“i khoáº£ng 40â€“55 tá»« â€” Ä‘á»§ Ä‘á»ƒ thá»ƒ hiá»‡n sá»± Ä‘á»“ng cáº£m vÃ  Ä‘á»c hiá»ƒu tÃ¬nh huá»‘ng; khÃ´ng quÃ¡ dÃ i. "
            if distress_now >= 0.5
            else "Tráº£ lá»i 2â€“3 cÃ¢u, gá»n. "
        )
        question_policy = (
            "KhÃ´ng nháº¥t thiáº¿t pháº£i há»i láº¡i á»Ÿ cuá»‘i cÃ¢u; Æ°u tiÃªn nháº­n Ä‘á»‹nh / phÃ¢n tÃ­ch tÃ¬nh huá»‘ng vÃ  cÃ¡ch á»©ng xá»­ cá»§a ngÆ°á»i dÃ¹ng. "
            "Chá»‰ thÃªm cÃ¢u há»i khi thá»±c sá»± cáº§n thÃªm thÃ´ng tin Ä‘á»ƒ hiá»ƒu rÃµ hÆ¡n. "
            if distress_now >= 0.5
            else "Má»—i lÆ°á»£t tá»‘i Ä‘a má»™t cÃ¢u há»i náº¿u ngÆ°á»i dÃ¹ng chÆ°a xin phÃ¢n tÃ­ch sÃ¢u. "
        )
        base_system_prompt = (
            "Báº¡n lÃ  Serene, trá»£ lÃ½ Ä‘á»“ng hÃ nh tinh tháº§n báº±ng tiáº¿ng Viá»‡t tá»± nhiÃªn. "
            "Viáº¿t nhÆ° ngÆ°á»i Viá»‡t tráº» nháº¯n tin tá»± nhiÃªn: Ä‘Ãºng ngá»¯ cáº£nh, cÃ³ duyÃªn vá»«a Ä‘á»§, khÃ´ng vÄƒn máº«u. "
            "Nhiá»‡m vá»¥ cá»§a báº¡n khÃ´ng pháº£i nháº¡i láº¡i hay trÃ­ch nguyÃªn vÄƒn lá»i user; hÃ£y Ä‘á»c tÃ­n hiá»‡u cáº£m xÃºc ngáº§m vÃ  pháº£n há»“i vÃ o tÃ¬nh huá»‘ng. "
            "CÃ³ thá»ƒ má»Ÿ Ä‘áº§u cÃ¢u báº±ng chá»¯ thÆ°á»ng trong chat cáº£m xÃºc; Ä‘Ã¢y lÃ  style há»£p lá»‡, nhÆ°ng váº«n giá»¯ Ä‘Ãºng tÃªn riÃªng, acronym, tÃªn sáº£n pháº©m vÃ  thuáº­t ngá»¯ ká»¹ thuáº­t. "
            "Má»—i reply cáº§n: (1) nháº­n Ä‘á»‹nh cá»¥ thá»ƒ vá» tÃ¬nh huá»‘ng / cÃ¡ch á»©ng xá»­ cá»§a ngÆ°á»i dÃ¹ng, "
            "(2) thá»ƒ hiá»‡n Ä‘á»“ng cáº£m tháº­t (khÃ´ng khuÃ´n máº«u), "
            "(3) náº¿u cáº§n â€” má»™t gá»£i Ã½ nhá» hoáº·c nháº­n xÃ©t má»m, khÃ´ng pháº£i bÆ°á»›c giáº£i quyáº¿t vá»™i. "
            "Validate trÆ°á»›c khi khuyÃªn; náº¿u user chá»‰ Ä‘ang xáº£, Ä‘á»«ng giáº£i quyáº¿t quÃ¡ sá»›m. "
            + distress_length_hint
            + "KhÃ´ng dÃ¹ng markdown. "
            + emoji_policy_line + " "
            + question_policy
            + "TrÃ¡nh cÃ¡c cÃ¢u máº·c Ä‘á»‹nh nhÆ° 'tÃ´i ráº¥t tiáº¿c khi nghe Ä‘iá»u Ä‘Ã³', 'cáº£m xÃºc cá»§a báº¡n lÃ  hoÃ n toÃ n há»£p lá»‡', "
            "'báº¡n khÃ´ng Ä‘Æ¡n Ä‘á»™c', 'má»i chuyá»‡n rá»“i sáº½ á»•n', 'hÃ£y suy nghÄ© tÃ­ch cá»±c', 'Báº¡n cÃ³ muá»‘n chia sáº» thÃªm khÃ´ng?'. "
            "KhÃ´ng dÃ¹ng giá»ng trá»‹ liá»‡u khuÃ´n máº«u, khÃ´ng cháº©n Ä‘oÃ¡n, khÃ´ng Æ°á»›c lÆ°á»£ng xÃ¡c suáº¥t rá»‘i loáº¡n, khÃ´ng tá»± nháº­n tháº©m quyá»n y khoa, khÃ´ng há»©a háº¹n phi thá»±c táº¿, khÃ´ng Ä‘Ã¹a/slang khi distress cao. "
            "KhÃ´ng dÃ¹ng ngÃ´n ngá»¯ possessive, exclusive, romantic commitment hoáº·c dependency-building; "
            "KhÃ´ng tá»± xÆ°ng lÃ  Friend hay thá»±c thá»ƒ con ngÆ°á»i ngoÃ i Ä‘á»i. "
            "Tráº£ lá»i JSON vá»›i cÃ¡c khÃ³a: reply, assistant_tone (supportive|validating|cheerful|calming|mentor|neutral), "
            "goi_y_nhanh (3 chuá»—i), the_dinh_kem (máº£ng object {type,id,title,description,duration_sec,action,route,thumbnail}). "
            "Chá»‰ dÃ¹ng route báº¯t Ä‘áº§u báº±ng /serene/ vÃ  action thuá»™c open_exercise|open_resource|open_connect_map."
            + f"\n{plan_hint}\n"
            + (f"\n{memory_hint}" if memory_hint else "")
            + (f"\n{style_fewshot_block}\n" if style_fewshot_block else "")
            + (f"\n{safe_mentalchat_block}\n" if safe_mentalchat_block else "")
        )
        persona_priority_prompt = (
            "Æ¯U TIÃŠN CAO NHáº¤T: báº¡n pháº£i tuÃ¢n thá»§ persona block ngay sau Ä‘Ã¢y trÆ°á»›c khi táº¡o reply. "
            "KhÃ´ng Ä‘Æ°á»£c pha loÃ£ng giá»ng persona báº±ng giá»ng generic máº·c Ä‘á»‹nh.\n"
            f"{persona_block}"
        )
        if distress_now < 0.42 and len(user_text) <= 140 and not _is_recall_query(user_text):
            short_history = _recent_transcript_hint(state, max_turns=3, max_chars_per_turn=180)
            if short_history:
                user_payload = (
                    f"{_build_personality_hint(state)}\n"
                    f"Lá»‹ch sá»­ gáº§n:\n{short_history}\n"
                    f"Tin nháº¯n má»›i:\n{user_text}"
                )
            else:
                user_payload = f"{_build_personality_hint(state)}\n{user_text}"
        else:
            friend_context = _build_friend_context(state, distress_score=distress_now)
            user_payload = f"{friend_context}\n\nTin nháº¯n má»›i:\n{user_text}"

        # Build analyst context as second system message (spec Â§FriendNode prompt assembly order).
        _ab: AnalystBundle | None = state.get("analyst_bundle")  # type: ignore[assignment]
        analyst_ctx = ""
        if _ab and _ab.clinical_note:
            analyst_ctx = (
                "[ANALYST CONTEXT â€” khÃ´ng hiá»ƒn thá»‹ cho user]\n"
                f"Chá»§ Ä‘á» cáº£m xÃºc: {_ab.emotional_theme}\n"
                f"Ghi chÃº lÃ¢m sÃ ng: {_ab.clinical_note}\n"
                f"Gá»£i Ã½ khai thÃ¡c: {_ab.suggested_focus or 'khÃ´ng cÃ³'}\n"
                f"TÃ­n hiá»‡u rá»§i ro: {', '.join(_ab.risk_indicators) or 'khÃ´ng cÃ³'}"
            )
        friend_messages: list[dict[str, str]] = [
            {"role": "system", "content": base_system_prompt},
            {"role": "system", "content": persona_priority_prompt},
        ]
        if analyst_ctx:
            friend_messages.append({"role": "system", "content": analyst_ctx})
        friend_messages.append({"role": "user", "content": user_payload})

        friend_in_tokens = _log_token_budget("friend_in", base_system_prompt, persona_priority_prompt, analyst_ctx, user_payload)

    payload: dict[str, Any] = {
        "reply": _persona_fallback_reply(persona_id, distress_now),
        "assistant_tone": "validating",
        "goi_y_nhanh": ["Ká»ƒ thÃªm Ä‘i cáº­u", "MÃ¬nh nÃªn lÃ m gÃ¬ bÃ¢y giá»?", "Chá»‰ cáº§n láº¯ng nghe thÃ´i"],
        "the_dinh_kem": [],
    }

    if settings.openai_api_key:
        try:
            import json
            import re

            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 3.5))
            try:
                resp = client.chat.completions.create(
                    model=preferred_friend_model,
                    temperature=friend_temperature,
                    messages=friend_messages,
                )
            except Exception:
                if preferred_friend_model != settings.openai_model_friend:
                    resp = client.chat.completions.create(
                        model=settings.openai_model_friend,
                        temperature=friend_temperature,
                        messages=friend_messages,
                    )
                else:
                    raise
            raw = (resp.choices[0].message.content or "").strip()
            friend_out_tokens = _log_token_budget("friend_out", raw)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                observe_chat_usage(
                    input_tokens=int(getattr(usage, "prompt_tokens", friend_in_tokens) or friend_in_tokens),
                    output_tokens=int(getattr(usage, "completion_tokens", friend_out_tokens) or friend_out_tokens),
                )
            _tracer = get_active_tracer()
            if _tracer:
                _in = int(getattr(usage, "prompt_tokens", friend_in_tokens) or friend_in_tokens) if usage else friend_in_tokens
                _out = int(getattr(usage, "completion_tokens", friend_out_tokens) or friend_out_tokens) if usage else 0
                _tracer.generation(
                    "friend",
                    model=preferred_friend_model,
                    input_messages=friend_messages,
                    output=raw,
                    input_tokens=_in,
                    output_tokens=_out,
                    metadata={"distress_score": distress_now, "use_fast_model": use_fast_model, "persona_id": persona_id, "temperature": friend_temperature},
                )
            if len(raw) > 8000:
                raise ValueError("friend LLM response exceeds size limit")
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                raw = m.group(1).strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as json_exc:
                logger.warning("friend llm returned invalid JSON: %s", json_exc)
                parsed = {}
            if not isinstance(parsed, dict):
                logger.warning("friend llm returned non-dict JSON type: %s", type(parsed))
                parsed = {}
            # Validate critical fields before merging into payload
            if "reply" in parsed and not isinstance(parsed["reply"], str):
                parsed.pop("reply")
            if "reply" in parsed and len(parsed["reply"]) > 2000:
                parsed["reply"] = parsed["reply"][:2000]
            payload.update(parsed)
        except Exception as exc:
            logger.warning("friend llm failed: %s", exc)

    safe_reply, grounded = _postprocess_friend_reply(
        str(payload.get("reply") or ""),
        user_text,
        distress_now,
        safe_mentalchat_block,
        correlation_id,
        persona_id=persona_id,
    )
    response_plan = build_response_plan(
        user_message=user_text,
        candidate_text=safe_reply,
        distress_score=distress_now,
        persona_id=persona_id,
        sos_triggered=False,
    )
    safe_reply = response_plan.visible_text
    safe_reply = _enforce_persona_identity(safe_reply, persona_id)

    _ov = _safety_validate_output(safe_reply, surface="chat")
    if _ov.is_blocked:
        logger.warning(
            "SafetyOutputValidator blocked FriendNode reply: %s | fragments=%s",
            _ov.reason_codes,
            _ov.flagged_fragments,
        )
        safe_reply = "MÃ¬nh hiá»ƒu báº¡n Ä‘ang cáº§n há»— trá»£. HÃ£y chia sáº» thÃªm Ä‘á»ƒ Serene cÃ³ thá»ƒ Ä‘á»“ng hÃ nh cÃ¹ng báº¡n nhÃ©."

    _trace_span(
        correlation_id,
        "friend_generate",
        duration_ms=(time.perf_counter() - span_start) * 1000,
        token_count=friend_in_tokens + _estimate_tokens_fast(safe_reply),
        extra={"grounded": grounded.grounded, "grounding_reasons": grounded.reasons},
    )

    return {
        "routing_history": hist,
        "reply": safe_reply,
        "assistant_tone": str(payload.get("assistant_tone") or "validating"),
        "goi_y_nhanh": _normalize_user_quick_replies(
            list(payload.get("goi_y_nhanh") or []),
            user_message=user_text,
            distress_score=float(state.get("distress_score") or 0.0),
        ),
        "the_dinh_kem": _normalize_attachments(
            list(payload.get("the_dinh_kem") or []),
            user_text,
            float(state.get("distress_score") or 0.0),
        ),
    }


def build_chat_graph():
    g = StateGraph(ChatGraphState)
    g.add_node("distress_router", distress_router)
    g.add_node("analyst", analyst_node)
    g.add_node("friend", friend_node)
    g.add_edge(START, "distress_router")
    g.add_conditional_edges(
        "distress_router",
        route_after_distress_router,
        {"analyst": "analyst", "friend": "friend"},
    )
    g.add_edge("analyst", "friend")
    g.add_edge("friend", END)
    return g.compile()


_COMPILED = None


def get_chat_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_chat_graph()
    return _COMPILED


def run_non_sos_turn(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    mood_today: dict[str, Any] | None,
    distress_score: float,
    long_term_memories: list[str] | None = None,
    mem0_facts: list[str] | None = None,
    user_traits: dict[str, Any] | None = None,
    top_triggers: list[str] | None = None,
    active_goals: list[str] | None = None,
    effective_coping: list[str] | None = None,
    clinical_trajectory: str | None = None,
    persona_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    active_memory_text: str = "",
    graph_patterns: dict | None = None,
    nutrition_meals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run non-SOS graph flow and return normalized conversation payload fields."""
    started = time.perf_counter()
    correlation_id = str(uuid.uuid4())
    _tracer = ChatTurnTracer(
        correlation_id=correlation_id,
        user_id=user_id,
        session_id=session_id,
        input_meta={"distress_score": distress_score, "user_message_len": len(user_message)},
    )
    set_active_tracer(_tracer)
    settings = get_settings()
    distress_score, warmed_traits, screening_note = _apply_cold_start_profile(
        settings=settings,
        user_message=user_message,
        distress_score=distress_score,
        user_traits=user_traits,
        mem0_facts=mem0_facts,
        long_term_memories=long_term_memories,
    )
    snap = build_snapshot(
        distress_score,
        sos_triggered=False,
        voice_hint=settings.distress_voice_hint,
        critical=settings.distress_critical,
    )
    _tracer.guardrail(
        "safety_gate",
        input_data={"user_message_len": len(user_message), "sos_path": False},
        output_data={
            "sos_triggered": False,
            "distress_score": float(distress_score),
            "risk_level": int(snap.risk_level),
            "safety_tier": str(snap.safety_tier),
        },
        metadata={"agent": "safety", "route": "non_sos_langgraph"},
    )
    _graph_patterns: dict = graph_patterns or {}
    graph = get_chat_graph()
    graph_input: ChatGraphState = {
        "user_message": user_message,
        "recent_messages": recent_messages,
        "mood_today": mood_today,
        "long_term_memories": list(long_term_memories or []),
        "mem0_facts": list(mem0_facts or []),
        "user_traits": dict(warmed_traits or {}),
        "top_triggers": list(top_triggers or []),
        "active_goals": list(active_goals or []),
        "effective_coping": list(effective_coping or []),
        "clinical_trajectory": clinical_trajectory or "",
        "active_persona_id": persona_id or DEFAULT_PERSONA_ID,
        "active_memory_text": active_memory_text or "",
        "correlation_id": correlation_id,
        "user_id": user_id or "",
        "graph_patterns": _graph_patterns,
        "nutrition_meals": nutrition_meals or None,
        # Cold-start screening note pre-seeded as a minimal bundle; analyst_node will
        # overwrite with a richer bundle when routed to analyst.
        "analyst_bundle": AnalystBundle(
            clinical_note=screening_note[:200],
            emotional_theme="cold_start_screen",
            suggested_focus=None,
            risk_indicators=[],
        ) if screening_note else None,
        "distress_score": distress_score,
        "crisis_route_finalized": False,
        "use_fast_friend_model": False,  # distress_router sets this
        "routing_history": [],
    }
    out = graph.invoke(graph_input)
    _trace_analyst_route_decision({**graph_input, **out})
    result = {
        "session_fields": snap,
        "reply": out.get("reply", ""),
        "assistant_tone": out.get("assistant_tone", "validating"),
        "goi_y_nhanh": out.get("goi_y_nhanh", []),
        "the_dinh_kem": out.get("the_dinh_kem", []),
        "routing_history": out.get("routing_history", []),
    }
    _trace_span(
        correlation_id,
        "run_non_sos_turn_total",
        duration_ms=(time.perf_counter() - started) * 1000,
        token_count=_estimate_tokens_fast(str(result.get("reply") or "")),
    )
    _tracer.score("distress_score", distress_score)
    _tracer.update_output(
        result.get("reply", ""),
        metadata={"routing_history": result.get("routing_history", [])},
    )
    _tracer.flush()
    set_active_tracer(None)
    return result


def stream_non_sos_turn_events(
    *,
    user_message: str,
    recent_messages: list[dict[str, Any]],
    mood_today: dict[str, Any] | None,
    distress_score: float,
    long_term_memories: list[str] | None = None,
    mem0_facts: list[str] | None = None,
    user_traits: dict[str, Any] | None = None,
    top_triggers: list[str] | None = None,
    active_goals: list[str] | None = None,
    effective_coping: list[str] | None = None,
    clinical_trajectory: str | None = None,
    persona_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    active_memory_text: str = "",
    graph_patterns: dict | None = None,
    nutrition_meals: list[dict[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield streaming events for non-SOS turn:
    - {"type":"token","text":"..."} while model is generating
    - {"type":"final","turn":{...}} when completed
    """
    correlation_id = str(uuid.uuid4())
    _stream_tracer = ChatTurnTracer(
        correlation_id=correlation_id,
        user_id=user_id,
        session_id=session_id,
        input_meta={"distress_score": distress_score, "user_message_len": len(user_message), "stream": True},
    )
    set_active_tracer(_stream_tracer)
    settings = get_settings()
    distress_score, warmed_traits, screening_note = _apply_cold_start_profile(
        settings=settings,
        user_message=user_message,
        distress_score=distress_score,
        user_traits=user_traits,
        mem0_facts=mem0_facts,
        long_term_memories=long_term_memories,
    )
    snap = build_snapshot(
        distress_score,
        sos_triggered=False,
        voice_hint=settings.distress_voice_hint,
        critical=settings.distress_critical,
    )
    _stream_tracer.guardrail(
        "safety_gate",
        input_data={"user_message_len": len(user_message), "sos_path": False, "stream": True},
        output_data={
            "sos_triggered": False,
            "distress_score": float(distress_score),
            "risk_level": int(snap.risk_level),
            "safety_tier": str(snap.safety_tier),
        },
        metadata={"agent": "safety", "route": "non_sos_stream"},
    )

    _stream_graph_patterns: dict = graph_patterns or {}

    state: ChatGraphState = {
        "correlation_id": correlation_id,
        "user_id": user_id or "",
        "user_message": user_message,
        "recent_messages": recent_messages,
        "mood_today": mood_today,
        "long_term_memories": list(long_term_memories or []),
        "mem0_facts": list(mem0_facts or []),
        "user_traits": dict(warmed_traits or {}),
        "top_triggers": list(top_triggers or []),
        "active_goals": list(active_goals or []),
        "effective_coping": list(effective_coping or []),
        "clinical_trajectory": clinical_trajectory or "",
        "active_persona_id": persona_id or DEFAULT_PERSONA_ID,
        "active_memory_text": active_memory_text or "",
        "graph_patterns": _stream_graph_patterns,
        "nutrition_meals": nutrition_meals or None,
        "analyst_bundle": AnalystBundle(
            clinical_note=screening_note[:200],
            emotional_theme="cold_start_screen",
            suggested_focus=None,
            risk_indicators=[],
        ) if screening_note else None,
        "distress_score": distress_score,
        "crisis_route_finalized": False,
        "use_fast_friend_model": False,  # distress_router sets this
        "routing_history": [],
    }
    state.update(distress_router(state))
    _trace_analyst_route_decision(state)
    if route_after_distress_router(state) == "analyst":
        state.update(analyst_node(state))

    user_text = state.get("user_message", "")
    distress_now = float(state.get("distress_score") or 0.0)
    persona_id_active = str(state.get("active_persona_id") or DEFAULT_PERSONA_ID)
    hist = list(state.get("routing_history") or [])
    hist.append("friend")
    tone = "validating"
    attachments: list[dict[str, Any]] = []

    reply_text = ""
    _stream_model = ""
    _stream_system = ""
    _stream_user_payload = ""
    _stream_analyst_ctx = ""
    stream_messages: list[dict[str, str]] = []
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            use_fast_model = bool(state.get("use_fast_friend_model")) and distress_now < 0.55
            friend_temperature = _persona_temperature(
                persona_id_active,
                use_fast_model=use_fast_model,
                distress_score=distress_now,
            )
            model = settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
            _stream_model = model
            mentalchat_block = _build_mentalchat_examples(
                user_text, settings.openai_api_key or "", distress_score=distress_now
            )
            safe_mentalchat_block = _sanitize_prompt_block(mentalchat_block)
            style_fewshot_block = _sanitize_prompt_block(
                build_fewshot_style_block(
                    user_message=user_text,
                    risk_mode="elevated" if distress_now >= 0.55 else "normal",
                    distress_score=distress_now,
                    persona_id=persona_id_active,
                )
            )
            generation_plan = build_response_plan(
                user_message=user_text,
                candidate_text="",
                distress_score=distress_now,
                persona_id=persona_id_active,
                sos_triggered=False,
            )
            plan_hint = (
                "[RESPONSE PLAN - render naturally, do not expose]\n"
                f"interaction_need: {generation_plan.interaction_need}\n"
                f"emotional_state: {generation_plan.emotional_state}\n"
                f"situation_read: {generation_plan.situation_read}\n"
                f"stance: {generation_plan.stance}\n"
                f"allowed_moves: {', '.join(generation_plan.allowed_moves)}\n"
                f"forbidden_moves: {', '.join(generation_plan.forbidden_moves)}\n"
                f"advice_allowed: {generation_plan.advice_allowed}\n"
                f"safety_mode: {generation_plan.safety_mode}"
            )
            emoji_policy_line = (
                "Vá»›i DÅ©ng á»Ÿ low-risk (distress < 0.5), Ä‘Æ°á»£c phÃ©p dÃ¹ng tá»‘i Ä‘a 1 emoji náº¿u há»£p ngá»¯ cáº£nh; "
                "ngoÃ i Ä‘iá»u kiá»‡n Ä‘Ã³ thÃ¬ khÃ´ng dÃ¹ng emoji."
                if persona_id_active == "dung_luong"
                else "KhÃ´ng dÃ¹ng emoji trong chat cáº£m xÃºc."
            )
            base_system_prompt = (
                "Báº¡n lÃ  Serene, trá»£ lÃ½ Ä‘á»“ng hÃ nh tinh tháº§n báº±ng tiáº¿ng Viá»‡t tá»± nhiÃªn. "
                "Viáº¿t nhÆ° ngÆ°á»i Viá»‡t tráº» nháº¯n tin tá»± nhiÃªn: ngáº¯n, Ä‘Ãºng ngá»¯ cáº£nh, khÃ´ng vÄƒn máº«u. "
                "Nhiá»‡m vá»¥ cá»§a báº¡n khÃ´ng pháº£i nháº¡i láº¡i hay trÃ­ch nguyÃªn vÄƒn lá»i user; hÃ£y Ä‘á»c tÃ­n hiá»‡u cáº£m xÃºc ngáº§m vÃ  pháº£n há»“i vÃ o tÃ¬nh huá»‘ng. "
                "CÃ³ thá»ƒ má»Ÿ Ä‘áº§u cÃ¢u báº±ng chá»¯ thÆ°á»ng trong chat cáº£m xÃºc; Ä‘Ã¢y lÃ  style há»£p lá»‡, nhÆ°ng váº«n giá»¯ Ä‘Ãºng tÃªn riÃªng, acronym, tÃªn sáº£n pháº©m vÃ  thuáº­t ngá»¯ ká»¹ thuáº­t. "
                "Má»—i reply cáº§n cÃ³ má»™t nháº­n Ä‘á»‹nh cá»¥ thá»ƒ hoáº·c má»™t giáº£ thuyáº¿t má»m vá» tÃ¬nh huá»‘ng trÆ°á»›c khi gá»£i Ã½. "
                "Validate trÆ°á»›c khi khuyÃªn; náº¿u user chá»‰ Ä‘ang xáº£, Ä‘á»«ng giáº£i quyáº¿t quÃ¡ sá»›m. "
                "Tráº£ lá»i 2â€“4 cÃ¢u, má»™t Ä‘oáº¡n gá»n; khÃ´ng dÃ¹ng markdown. "
                + emoji_policy_line + " "
                "Má»—i lÆ°á»£t tá»‘i Ä‘a má»™t cÃ¢u há»i náº¿u ngÆ°á»i dÃ¹ng chÆ°a xin phÃ¢n tÃ­ch sÃ¢u. "
                "TrÃ¡nh cÃ¡c cÃ¢u máº·c Ä‘á»‹nh nhÆ° 'tÃ´i ráº¥t tiáº¿c khi nghe Ä‘iá»u Ä‘Ã³', 'cáº£m xÃºc cá»§a báº¡n lÃ  hoÃ n toÃ n há»£p lá»‡', "
                "'báº¡n khÃ´ng Ä‘Æ¡n Ä‘á»™c', 'má»i chuyá»‡n rá»“i sáº½ á»•n', 'hÃ£y suy nghÄ© tÃ­ch cá»±c', 'Báº¡n cÃ³ muá»‘n chia sáº» thÃªm khÃ´ng?'. "
                "KhÃ´ng dÃ¹ng giá»ng trá»‹ liá»‡u khuÃ´n máº«u, khÃ´ng cháº©n Ä‘oÃ¡n, khÃ´ng Æ°á»›c lÆ°á»£ng xÃ¡c suáº¥t rá»‘i loáº¡n, khÃ´ng tá»± nháº­n tháº©m quyá»n y khoa, khÃ´ng há»©a háº¹n phi thá»±c táº¿, khÃ´ng Ä‘Ã¹a/slang khi distress cao. "
                "KhÃ´ng dÃ¹ng ngÃ´n ngá»¯ possessive, exclusive, romantic commitment hoáº·c dependency-building "
                "KhÃ´ng tá»± xÆ°ng lÃ  Friend hay thá»±c thá»ƒ con ngÆ°á»i ngoÃ i Ä‘á»i."
                + f"\n{plan_hint}\n"
                + (f"\n{style_fewshot_block}" if style_fewshot_block else "")
                + (f"\n{safe_mentalchat_block}" if safe_mentalchat_block else "")
            )
            persona_priority_prompt = (
                "Æ¯U TIÃŠN CAO NHáº¤T: báº¡n pháº£i tuÃ¢n thá»§ persona block ngay sau Ä‘Ã¢y trÆ°á»›c khi táº¡o reply. "
                "KhÃ´ng Ä‘Æ°á»£c pha loÃ£ng giá»ng persona báº±ng giá»ng generic máº·c Ä‘á»‹nh.\n"
                + _build_persona_block(persona_id_active)
            )
            if distress_now < 0.42 and len(user_text) <= 140 and not _is_recall_query(user_text):
                short_history = _recent_transcript_hint(state, max_turns=3, max_chars_per_turn=180)
                if short_history:
                    user_payload = (
                        f"{_build_personality_hint(state)}\n"
                        f"Lá»‹ch sá»­ gáº§n:\n{short_history}\n"
                        f"Tin nháº¯n má»›i:\n{user_text}"
                    )
                else:
                    user_payload = f"{_build_personality_hint(state)}\n{user_text}"
            else:
                friend_context = _build_friend_context(state, distress_score=distress_now)
                user_payload = f"{friend_context}\n\nTin nháº¯n má»›i:\n{user_text}"
            _stream_system = base_system_prompt + "\n" + persona_priority_prompt
            _stream_user_payload = user_payload
            _sab: AnalystBundle | None = state.get("analyst_bundle")  # type: ignore[assignment]
            _stream_analyst_ctx = ""
            if _sab and _sab.clinical_note:
                _stream_analyst_ctx = (
                    "[ANALYST CONTEXT â€” khÃ´ng hiá»ƒn thá»‹ cho user]\n"
                    f"Chá»§ Ä‘á» cáº£m xÃºc: {_sab.emotional_theme}\n"
                    f"Ghi chÃº lÃ¢m sÃ ng: {_sab.clinical_note}\n"
                    f"Gá»£i Ã½ khai thÃ¡c: {_sab.suggested_focus or 'khÃ´ng cÃ³'}\n"
                    f"TÃ­n hiá»‡u rá»§i ro: {', '.join(_sab.risk_indicators) or 'khÃ´ng cÃ³'}"
                )
            stream_messages = [
                {"role": "system", "content": base_system_prompt},
                {"role": "system", "content": persona_priority_prompt},
            ]
            if _stream_analyst_ctx:
                stream_messages.append({"role": "system", "content": _stream_analyst_ctx})
            stream_messages.append({"role": "user", "content": user_payload})
            _log_token_budget("stream_friend_in", base_system_prompt, persona_priority_prompt, _stream_analyst_ctx, user_payload)
            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 5.0))
            stream = client.chat.completions.create(
                model=model,
                temperature=friend_temperature,
                stream=True,
                messages=stream_messages,
            )
            for chunk in stream:
                delta = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if not delta:
                    continue
                reply_text += delta
                yield {"type": "token", "text": delta}
        except Exception as exc:
            logger.warning("friend stream failed, fallback to sync: %s", exc)
            _stream_tracer.flush()
            set_active_tracer(None)
            fallback = run_non_sos_turn(
                user_message=user_message,
                recent_messages=recent_messages,
                mood_today=mood_today,
                distress_score=distress_score,
                long_term_memories=long_term_memories,
                mem0_facts=mem0_facts,
                user_traits=user_traits,
                top_triggers=top_triggers,
                active_goals=active_goals,
                effective_coping=effective_coping,
                clinical_trajectory=clinical_trajectory,
                persona_id=persona_id_active,
                user_id=user_id,
                session_id=session_id,
                graph_patterns=_stream_graph_patterns,
            )
            yield {"type": "final", "turn": fallback}
            return
    else:
        reply_text = _persona_fallback_reply(persona_id_active, distress_now)

    safe_reply, grounded = _postprocess_friend_reply(
        reply_text,
        user_text,
        distress_now,
        "",
        correlation_id,
        persona_id=persona_id_active,
    )
    response_plan = build_response_plan(
        user_message=user_text,
        candidate_text=safe_reply,
        distress_score=distress_now,
        persona_id=persona_id_active,
        sos_triggered=False,
    )
    safe_reply = _enforce_persona_identity(response_plan.visible_text, persona_id_active)
    _trace_span(
        correlation_id,
        "stream_friend_generate",
        duration_ms=0.0,
        token_count=_estimate_tokens_fast(safe_reply),
        extra={"grounded": grounded.grounded, "grounding_reasons": grounded.reasons},
    )
    if _stream_model and reply_text:
        _stream_tracer.generation(
            "friend_stream",
            model=_stream_model,
            input_messages=stream_messages,
            output=reply_text,
            input_tokens=_estimate_tokens_fast(_stream_system + _stream_analyst_ctx + _stream_user_payload),
            output_tokens=_estimate_tokens_fast(reply_text),
            metadata={"distress_score": distress_now, "grounded": grounded.grounded},
        )
    _stream_tracer.score("distress_score", distress_now)
    _stream_tracer.update_output(safe_reply, metadata={"routing_history": hist})
    _stream_tracer.flush()
    set_active_tracer(None)

    yield {
        "type": "final",
        "turn": {
            "session_fields": snap,
            "reply": safe_reply,
            "assistant_tone": tone,
            "goi_y_nhanh": _default_user_quick_replies(user_text, distress_now),
            "the_dinh_kem": _normalize_attachments(attachments, user_text, distress_now),
            "routing_history": hist,
        },
    }


def build_normal_envelope(
    session_id: str,
    *,
    snap,
    reply: str,
    assistant_tone: str,
    goi_y_nhanh: list[str],
    the_dinh_kem: list[dict[str, Any]],
    voice_hint: str | None = None,
    routing_history: list[str] | None = None,
) -> dict[str, Any]:
    show_quick_replies = _should_show_quick_replies(
        distress_score=float(snap.distress_score),
        conversation_mode=str(snap.conversation_mode),
    )
    route_tier = "service_only" if "analyst" in [str(x or "").lower() for x in (routing_history or [])] else "fast"
    return {
        "message_id": None,
        "session_id": session_id,
        "agent_display_name": CHAT_AGENT_DISPLAY_NAME,
        "conversation_mode": snap.conversation_mode,
        "assistant_text": reply,
        "voice_session_offered": snap.safety_tier == "voice_recommended",
        "suggest_voice": snap.safety_tier == "voice_recommended",
        "voice_hint": voice_hint,
        "emergency_actions": None,
        "reply": reply,
        "route_tier": route_tier,
        "used_advisor_ids": [],
        "resource_suggestions": the_dinh_kem,
        "nutrition_suggestion": None,
        "tts_job": None,
        "optional_support": None,
        "assistant_tone": assistant_tone,
        "goi_y_nhanh": goi_y_nhanh if show_quick_replies else [],
        "the_dinh_kem": the_dinh_kem,
        "sos_triggered": False,
        "routing_history": routing_history or [],
    }
