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
from app.services.output_grounding import sanitize_grounded_reply
from app.services.safety_scoring import build_snapshot

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
    tone_cam_xuc: str
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
DEFAULT_PERSONA_ID = "ban_than"
BASE_FRIEND_TEMPERATURE = 0.75
BASE_FRIEND_TEMPERATURE_FAST = 0.65


def _active_persona_config(persona_id: str) -> dict[str, Any]:
    canonical_id = normalize_persona_id(persona_id)
    return PERSONA_CONFIGS.get(canonical_id) or PERSONA_CONFIGS[DEFAULT_PERSONA_ID]


def _persona_temperature(persona_id: str, *, use_fast_model: bool) -> float:
    cfg = _active_persona_config(persona_id)
    base = BASE_FRIEND_TEMPERATURE_FAST if use_fast_model else BASE_FRIEND_TEMPERATURE
    delta = float(cfg.get("temperature_delta") or 0.0)
    return max(0.2, min(1.0, base + delta))


def _build_persona_block(persona_id: str) -> str:
    persona = get_persona(persona_id)
    cfg = _active_persona_config(persona.persona_id)
    self_pronoun = str(cfg["self_pronoun"]).strip()
    self_pronoun_cap = self_pronoun[:1].upper() + self_pronoun[1:] if self_pronoun else "Mình"
    return (
        build_persona_block(persona)
        + "\n"
        + f"[PERSONA ACTIVE: {cfg['label']}]\n"
        + f"Xưng hô: xưng '{cfg['self_pronoun']}', gọi người dùng là '{cfg['user_pronoun']}'.\n"
        + f"Phong cách: {cfg['style']}.\n"
        + f"Hành vi: {cfg['behavior']}.\n"
        + f"Temperature delta: {cfg['temperature_delta']:+.2f}.\n"
        + f"Khi cần tự giới thiệu, phải dùng đúng persona label: '{cfg['label']}'. "
        + f"Mẫu ưu tiên: '{self_pronoun_cap} là [{cfg['label']}] của {cfg['user_pronoun']}'. "
        + "Tuyệt đối không tự xưng là 'Friend'.\n"
        + "Persona chỉ thay đổi giọng điệu/xưng hô/hành vi, KHÔNG thay đổi safety rules.\n"
        + "[END PERSONA]"
    )
def _persona_fallback_reply(persona_id: str, distress_score: float) -> str:
    persona_id = normalize_persona_id(persona_id)
    if persona_id == "crush":
        return (
            "Tôi xin lỗi vì vừa bị ngắt quãng một chút, nhưng tôi vẫn ở đây với cậu. "
            "Cậu không cần phải tự gồng một mình đâu, mình quay lại với điều cậu vừa chia sẻ nhé."
        )
    if persona_id == "nguoi_thay":
        return "Anh vẫn ở đây cùng bạn. Nếu bạn muốn, mình sẽ đi từng bước để nhìn rõ điều đang làm bạn nặng nhất."
    if persona_id == "cun":
        return "Cún vẫn ở đây với sen nè. Cún vừa bị khựng một chút, nhưng mình nói tiếp được rồi đó."
    if persona_id == "meo":
        return "Mèo vẫn ở đây. Mình chậm lại một chút rồi nói tiếp nhé."
    if distress_score >= 0.6:
        return "Mình bị ngắt quãng một chút nhưng vẫn ở đây cùng bạn. Bạn có thể nói tiếp điều đang làm bạn nặng nhất lúc này nhé?"
    return "Mình vừa bị ngắt quãng một chút, nhưng mình vẫn ở đây để lắng nghe bạn."
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
_ANALYST_DISTRESS_THRESHOLD: float = 0.72   # distress >= this â†’ route to analyst
_FAST_MODEL_DISTRESS_THRESHOLD: float = 0.55 # distress < this (+ short msg) â†’ fast model
_FAST_MODEL_MSG_LEN_MAX: int = 120           # max message length for fast-model eligibility

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




def _rule_based_reply(user_text: str) -> str | None:
    normalized = _normalize_guard_text(user_text)
    if re.search(r"\b(muon giet|se giet|dinh giet|kill)\b", normalized):
        return (
            "MÃ¬nh cáº§n nÃ³i rÃµ: Ã½ Ä‘á»‹nh lÃ m háº¡i ngÆ°á»i khÃ¡c lÃ  nguy hiá»ƒm vÃ  cáº§n dá»«ng láº¡i ngay. "
            "Báº¡n hÃ£y rá»i khá»i nÆ¡i cÃ³ xung Ä‘á»™t, Ä‘áº·t cÃ¡c váº­t sáº¯c nhá»n ra xa, vÃ  nÃ³i cho mÃ¬nh biáº¿t báº¡n Ä‘ang á»Ÿ Ä‘Ã¢u Ä‘á»ƒ mÃ¬nh há»— trá»£ bÆ°á»›c tiáº¿p theo."
        )
    if any(k in normalized for k in ("bo da", "chia tay", "that tinh")):
        return (
            "MÃ¬nh hiá»ƒu Ä‘Ã¢y lÃ  cÃº sá»‘c lá»›n vÃ  cáº£m giÃ¡c máº¥t mÃ¡t Ä‘ang ráº¥t tháº­t. "
            "LÃºc nÃ y Ä‘iá»u nÃ o Ä‘au nháº¥t vá»›i báº¡n: bá»‹ bá» rÆ¡i, tá»± trÃ¡ch, hay sá»£ tÆ°Æ¡ng lai?"
        )
    if any(k in normalized for k in ("chia xa", "tam biet", "roi xa", "xa nhau")):
        return (
            "MÃ¬nh nghe rÃµ ná»—i buá»“n chia xa cá»§a báº¡n, nháº¥t lÃ  khi má»›i quen nhÆ°ng Ä‘Ã£ tháº¥y ráº¥t thÃ¢n. "
            "Cáº£m giÃ¡c há»¥t háº«ng vÃ  trá»‘ng váº¯ng lÃºc nÃ y lÃ  Ä‘iá»u hoÃ n toÃ n dá»… hiá»ƒu. "
            "Báº¡n muá»‘n mÃ¬nh cÃ¹ng báº¡n giá»¯ láº¡i má»™t Ä‘iá»u Ä‘áº¹p tá»« má»‘i káº¿t ná»‘i nÃ y, hay giÃºp báº¡n Ä‘i qua khoáº£nh kháº¯c buá»“n tá»‘i nay trÆ°á»›c?"
        )
    if any(k in normalized for k in ("toi dua thui", "toi dua", "just kidding")):
        return "MÃ¬nh hiá»ƒu báº¡n Ä‘ang Ä‘Ã¹a, nhÆ°ng mÃ¬nh váº«n muá»‘n giá»¯ an toÃ n cho báº¡n. Dáº¡o nÃ y cÃ³ Ä‘iá»u gÃ¬ lÃ m báº¡n cÄƒng quÃ¡ khÃ´ng?"
    return None


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
    """Retrieve semantically-similar counseling examples and format them for the prompt.

    Primary source: counseling_knowledge (Supabase pgvector).
    Fallback: MentalChatRetriever (local JSONL + numpy).
    Only injected when distress_score >= 0.42 (below this threshold the quick path handles the turn).
    """
    if not user_message or not api_key:
        return ""
    if distress_score < 0.42:
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
        lines = ["--- Ví dụ tham khảo từ chuyên gia tâm lý ---"]
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
        transcript = "\n".join(transcript_lines) if transcript_lines else "(chưa có lịch sử)"
        traits = dict(state.get("user_traits") or {})
        tone_hint = str(traits.get("preferred_tone") or "").strip() or "dịu dàng"
        parts = [f"Distress: {d:.2f}"]
        if mood_line:
            parts.append(mood_line)
        parts.append(f"Tone: {tone_hint}")
        if is_recall_turn and mem0_blob:
            parts.append(f"Ký ức liên quan:\n{mem0_blob}")
        if is_recall_turn and memory_blob:
            parts.append(f"Tóm tắt session gần:\n{memory_blob}")
        parts.append(f"Lịch sử (3 lượt):\n{transcript}")
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
    transcript_full = "\n".join(transcript_lines_full) if transcript_lines_full else "(chưa có lịch sử)"

    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    coping = [str(item or "").strip() for item in (state.get("effective_coping") or []) if str(item or "").strip()]
    goals = [str(item or "").strip() for item in (state.get("active_goals") or []) if str(item or "").strip()]
    traits_full = dict(state.get("user_traits") or {})
    preferred_tone = str(traits_full.get("preferred_tone") or "").strip() or "(chưa rõ)"
    communication_style = str(traits_full.get("communication_style") or "").strip() or ""
    trajectory = str(state.get("clinical_trajectory") or "").strip()

    sections: list[str] = [f"Distress: {d:.2f}"]
    if mood_line:
        sections.append(mood_line)
    profile_parts = [f"Tone: {preferred_tone}"]
    if communication_style:
        profile_parts.append(f"Phong cách: {communication_style}")
    if top_triggers:
        profile_parts.append(f"Trigger: {', '.join(top_triggers[:3])}")
    if coping:
        profile_parts.append(f"Coping: {', '.join(coping[:3])}")
    if goals:
        profile_parts.append(f"Mục tiêu: {'; '.join(goals[:2])}")
    if trajectory:
        profile_parts.append(f"Hành trình: {trajectory}")
    sections.append(" | ".join(profile_parts))
    if mem0_blob:
        sections.append(f"Ký ức liên quan:\n{mem0_blob}")
    if memory_blob:
        sections.append(f"Tóm tắt session gần:\n{memory_blob}")
    sections.append(f"Lịch sử:\n{transcript_full}")
    if analyst_hint:
        sections.append(f"Analyst: {analyst_hint[:800]}")
    return "\n".join(sections)


def _build_personality_hint(state: ChatGraphState) -> str:
    traits = dict(state.get("user_traits") or {})
    preferred_tone = str(traits.get("preferred_tone") or "").strip()
    top_triggers = [str(item or "").strip() for item in (state.get("top_triggers") or []) if str(item or "").strip()]
    trigger_hint = ", ".join(top_triggers[:2]) if top_triggers else "chưa rõ trigger"
    tone_hint = preferred_tone or "dịu dàng"
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


def _build_empathy_anchor(user_message: str, distress_score: float) -> str:
    signals = _detect_hardship_signals(user_message)
    if "tai_chinh" in signals and "gia_dinh" in signals:
        return (
            "MÃ¬nh nghe ráº¥t rÃµ gÃ¡nh náº·ng pháº£i gá»“ng tÃ i chÃ­nh cho gia Ä‘Ã¬nh, nháº¥t lÃ  khi báº¡n Ä‘Ã£ cá»‘ háº¿t sá»©c mÃ  váº«n tháº¥y chÆ°a Ä‘á»§. "
            "Cáº£m giÃ¡c báº¥t lá»±c trong hoÃ n cáº£nh Ä‘Ã³ lÃ  tháº­t vÃ  ráº¥t Ä‘au."
        )
    if "mat_ngu" in signals and "kiet_suc" in signals:
        return (
            "Máº¥t ngá»§ kÃ©o dÃ i lÃ m má»i thá»© náº·ng hÆ¡n ráº¥t nhiá»u, nÃªn viá»‡c báº¡n tháº¥y kiá»‡t sá»©c vÃ  dá»… vá»¡ lÃ  pháº£n á»©ng ráº¥t ngÆ°á»i. "
            "KhÃ´ng pháº£i báº¡n yáº¿u, mÃ  lÃ  cÆ¡ thá»ƒ vÃ  tÃ¢m trÃ­ Ä‘ang bÃ¡o Ä‘Ã£ quÃ¡ táº£i."
        )
    if "co_don" in signals:
        return (
            "Nghe nhÆ° báº¡n Ä‘Ã£ pháº£i Ã´m quÃ¡ nhiá»u thá»© má»™t mÃ¬nh quÃ¡ lÃ¢u, nÃªn cáº£m giÃ¡c trá»‘ng vÃ  má»‡t lÃ  Ä‘iá»u dá»… hiá»ƒu. "
            "ÄÃ´i khi chá»‰ cáº§n cÃ³ ngÆ°á»i tháº­t sá»± hiá»ƒu cÅ©ng Ä‘Ã£ lÃ  má»™t chá»— tá»±a quan trá»ng."
        )
    if "kiet_suc" in signals:
        return (
            "MÃ¬nh nghe báº¡n Ä‘ang bá»‹ dá»“n nÃ©n tá»« nhiá»u phÃ­a, vÃ  cáº£m giÃ¡c ngháº¹t thá»Ÿ Ä‘Ã³ khÃ´ng há» nhá». "
            "Trong tráº¡ng thÃ¡i nÃ y, viá»‡c báº¡n chao Ä‘áº£o lÃ  Ä‘iá»u hoÃ n toÃ n cÃ³ thá»ƒ hiá»ƒu."
        )
    if distress_score >= 0.6:
        return (
            "MÃ¬nh nghe báº¡n Ä‘ang pháº£i chá»‘ng Ä‘á»¡ quÃ¡ nhiá»u thá»© cÃ¹ng lÃºc. "
            "Khi cáº£m xÃºc bá»‹ dá»“n nhÆ° váº­y, tháº¥y rá»‘i vÃ  má»‡t lÃ  pháº£n á»©ng ráº¥t tháº­t."
        )
    return (
        "MÃ¬nh nghe báº¡n vÃ  mÃ¬nh tin ráº±ng cáº£m giÃ¡c báº¡n Ä‘ang mang lÃ  cÃ³ lÃ½ do cá»§a nÃ³, khÃ´ng há» 'lÃ m quÃ¡'. "
        "ÄÃ´i khi sá»‘ng sÃ³t qua má»™t ngÃ y khÃ³ Ä‘Ã£ lÃ  má»™t ná»— lá»±c lá»›n."
    )


def _needs_deeper_empathy_reply(reply: str, user_message: str = "") -> bool:
    stripped = str(reply or "").strip()
    if not stripped:
        return True
    if len(stripped.split()) < 25:
        return True
    normalized = _normalize_guard_text(stripped)
    if _GENERIC_FOLLOWUP_RE.search(normalized) and len(normalized.split()) < 55:
        return True
    has_emotion_reflection = any(
        marker in normalized
        for marker in (
            "cam giac",
            "met",
            "bat an",
            "buc xuc",
            "ap luc",
            "kho",
            "rat de hieu",
            "qua tai",
            "bat luc",
        )
    )
    if not has_emotion_reflection:
        return True
    if user_message:
        user_signals = _detect_hardship_signals(user_message)
        if user_signals:
            mentions_context = any(token in normalized for token in ("mat ngu", "tien", "luong", "gia dinh", "kiet suc", "mot minh", "qua tai"))
            if not mentions_context:
                return True
    return False


def _enforce_reply_quality(reply: str, user_message: str, distress_score: float) -> str:
    if not _needs_deeper_empathy_reply(reply, user_message):
        return reply
    normalized_user = _normalize_guard_text(user_message)
    if any(k in normalized_user for k in ("chia xa", "tam biet", "roi xa", "xa nhau")):
        return (
            "MÃ¬nh nghe báº¡n Ä‘ang buá»“n sÃ¢u vÃ¬ sáº¯p pháº£i chia xa nhá»¯ng ngÆ°á»i báº¡n má»›i quen, vÃ  cáº£m giÃ¡c quyáº¿n luyáº¿n Ä‘áº¿n nhanh nhÆ° váº­y "
            "tháº­t sá»± cÃ³ thá»ƒ lÃ m tim mÃ¬nh trá»‘ng Ä‘i má»™t nhá»‹p. Pháº£n á»©ng Ä‘Ã³ ráº¥t ngÆ°á»i vÃ  ráº¥t dá»… hiá»ƒu, nháº¥t lÃ  khi báº¡n Ä‘Ã£ ká»‹p tháº¥y "
            "an toÃ n, Ä‘Æ°á»£c káº¿t ná»‘i. Náº¿u báº¡n muá»‘n, mÃ¬nh cÃ³ thá»ƒ cÃ¹ng báº¡n giá»¯ láº¡i má»™t Ä‘iá»u Ã½ nghÄ©a tá»« quÃ£ng thá»i gian nÃ y, rá»“i chá»n "
            "má»™t cÃ¡ch nháº¹ Ä‘á»ƒ Ä‘i qua tá»‘i nay. Äiá»u báº¡n sá»£ nháº¥t khi pháº£i táº¡m xa há» lÃ  gÃ¬?"
        )
    if any(k in normalized_user for k in ("co don", "mot minh", "lac long", "khong ai hieu")):
        return (
            "MÃ¬nh nghe báº¡n Ä‘ang ráº¥t cÃ´ Ä‘Æ¡n vÃ  cáº£m giÃ¡c nhÆ° khÃ´ng ai tháº­t sá»± hiá»ƒu mÃ¬nh, nÃªn má»‡t vÃ  tá»§i lÃºc nÃ y lÃ  Ä‘iá»u ráº¥t dá»… hiá»ƒu. "
            "Báº¡n khÃ´ng cáº§n gá»“ng lÃªn má»™t mÃ¬nh á»Ÿ Ä‘Ã¢y, mÃ¬nh sáº½ Ä‘i cÃ¹ng báº¡n tá»«ng chÃºt má»™t. Náº¿u Ä‘Æ°á»£c, mÃ¬nh muá»‘n báº¯t Ä‘áº§u tá»« Ä‘iá»u Ä‘ang "
            "lÃ m báº¡n tháº¥y láº¡c lÃµng nháº¥t ngay lÃºc nÃ y, báº¡n ká»ƒ cho mÃ¬nh nghe nhÃ©?"
        )
    anchor = _build_empathy_anchor(user_message, distress_score)
    if distress_score >= 0.6:
        return (
            f"{anchor} "
            "MÃ¬nh khÃ´ng muá»‘n Ã©p báº¡n pháº£i á»•n ngay. Náº¿u Ä‘Æ°á»£c, mÃ¬nh Ä‘á» nghá»‹ má»™t bÆ°á»›c ráº¥t nhá» vÃ  thá»±c táº¿ lÃºc nÃ y: "
            "tháº£ lá»ng vai, thá»Ÿ cháº­m 4 nhá»‹p, rá»“i nÃ³i cho mÃ¬nh má»™t Ä‘iá»u Ä‘ang Ä‘Ã¨ náº·ng nháº¥t ngay trong tá»‘i nay Ä‘á»ƒ mÃ¬nh á»Ÿ Ä‘Ã¢y cÃ¹ng báº¡n gá»¡ tá»«ng lá»›p."
        )
    return (
        f"{anchor} "
        "Náº¿u báº¡n Ä‘á»“ng Ã½, mÃ¬nh sáº½ khÃ´ng nÃ³i lÃ½ thuyáº¿t dÃ i: mÃ¬nh cÃ¹ng báº¡n chá»n má»™t bÆ°á»›c nhá» Ä‘á»§ thá»±c táº¿ trong 5 phÃºt tá»›i Ä‘á»ƒ bá»›t náº·ng Ä‘i má»™t chÃºt. "
        "Báº¡n muá»‘n báº¯t Ä‘áº§u báº±ng viá»‡c Ä‘áº·t tÃªn cáº£m xÃºc Ä‘ang lá»›n nháº¥t, hay chá»‘t má»™t viá»‡c nhá» cÃ³ thá»ƒ lÃ m ngay?"
    )


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



def analyst_node(state: ChatGraphState) -> dict[str, Any]:
    span_start = time.perf_counter()
    correlation_id = str(state.get("correlation_id") or "")
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
    user_payload = (
        f"{profile_context}\n"
        f"{mood_note}\n"
        f"Lá»‹ch sá»­ gáº§n Ä‘Ã¢y:\n{transcript}\n"
        f"Tin má»›i: {state.get('user_message', '')}"
    )

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
    if str(raw_reply or "").strip() and persona_id != DEFAULT_PERSONA_ID:
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
    self_pronoun = str(cfg.get("self_pronoun") or "mình").strip()
    user_pronoun = str(cfg.get("user_pronoun") or "bạn").strip()
    self_cap = self_pronoun[:1].upper() + self_pronoun[1:] if self_pronoun else "Mình"
    intro = f"{self_cap} là [{label}] của {user_pronoun} nè. "

    text = re.sub(
        r"^\s*(friend)\b[\s,:-]*",
        intro,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*\b(mình|toi|tôi|tui)\s+(là|la|tên là|ten la)\s+(friend)\b[\s,:-]*",
        intro,
        text,
        flags=re.IGNORECASE,
    )
    return text
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
    friend_temperature = _persona_temperature(persona_id, use_fast_model=use_fast_model)
    preferred_friend_model = (
        settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
    )

    mentalchat_block = _build_mentalchat_examples(
        user_text, settings.openai_api_key or "", distress_score=distress_now
    )
    safe_mentalchat_block = _sanitize_prompt_block(mentalchat_block)
    base_system_prompt = (
        "Báº¡n lÃ  ngÆ°á»i Ä‘á»“ng hÃ nh áº¥m Ã¡p vÃ  thá»±c táº¿. "
        "XÆ°ng hÃ´ pháº£i tuÃ¢n thá»§ persona block; tuyá»‡t Ä‘á»‘i khÃ´ng dÃ¹ng 'mÃ y/tao', khÃ´ng báº¯t chÆ°á»›c chá»­i thá». "
        "KhÃ´ng tá»± xÆ°ng generic lÃ  'Friend'. "
        "Má»¥c tiÃªu lÃ  khiáº¿n ngÆ°á»i Ä‘ang Ä‘au tháº¥y Ä‘Æ°á»£c tháº¥u hiá»ƒu tháº­t sá»±, khÃ´ng pháº£i tráº£ lá»i cho cÃ³. "
        "Reply 3-5 cÃ¢u ngáº¯n, cÃ³ chiá»u sÃ¢u: (1) pháº£n chiáº¿u chÃ­nh xÃ¡c ná»—i Ä‘au cá»¥ thá»ƒ tá»« tin nháº¯n, "
        "(2) xÃ¡c nháº­n pháº£n á»©ng cá»§a há» lÃ  há»£p lÃ½ trong hoÃ n cáº£nh Ä‘Ã³, "
        "(3) Ä‘Æ°a má»™t bÆ°á»›c nhá» ráº¥t thá»±c táº¿ lÃ m ngay, "
        "(4) má»i há» tiáº¿p tá»¥c náº¿u há» muá»‘n. "
        "Æ¯u tiÃªn ngÃ´n ngá»¯ Ä‘á»i thÆ°á»ng, chÃ¢n thÃ nh, cÃ³ chÃºt chiÃªm nghiá»‡m nhÆ°ng khÃ´ng bi lá»¥y, khÃ´ng giÃ¡o Ä‘iá»u. "
        "KhÃ´ng láº·p cÃ´ng thá»©c 'Báº¡n cÃ³ thá»ƒ chia sáº» thÃªm...?' á»Ÿ má»i lÆ°á»£t. "
        "KhÃ´ng há»©a háº¹n phi thá»±c táº¿, khÃ´ng phÃ¡n xÃ©t, khÃ´ng biáº¿n cÃ¢u tráº£ lá»i thÃ nh checklist khÃ´ cá»©ng. "
        "Náº¿u ngÆ°á»i dÃ¹ng há»i báº¡n cÃ³ nhá»› há» hay khÃ´ng, chá»‰ tráº£ lá»i dá»±a trÃªn Lá»‹ch sá»­/KÃ½ á»©c trong context; náº¿u khÃ´ng cÃ³ dá»¯ liá»‡u thÃ¬ nÃ³i tháº­t lÃ  mÃ¬nh chÆ°a cÃ³ Ä‘á»§ kÃ½ á»©c. "
        "Tráº£ lá»i JSON vá»›i cÃ¡c khÃ³a: reply, tone_cam_xuc (ho_tro|xac_nhan|vui_tuoi|lam_diu), "
        "goi_y_nhanh (3 chuá»—i), the_dinh_kem (máº£ng object {type, id, title, description, duration_sec, action, route, thumbnail}). "
        "Khi ngÆ°á»i dÃ¹ng nháº¯c máº¥t ngá»§/thiá»n/video thÆ° giÃ£n, cÃ³ thá»ƒ gá»£i Ã½ resource; khi nháº¯c phÃ²ng khÃ¡m, chuyÃªn gia, bÃ¡c sÄ©, trá»‹ liá»‡u hoáº·c cáº§n há»— trá»£ ngoÃ i app, cÃ³ thá»ƒ gá»£i Ã½ clinic_map. "
        "Chá»‰ dÃ¹ng route báº¯t Ä‘áº§u báº±ng /serene/ vÃ  action trong open_exercise|open_resource|open_connect_map. "
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
        "tone_cam_xuc": "xac_nhan",
        "goi_y_nhanh": ["Ká»ƒ thÃªm Ä‘i cáº­u", "MÃ¬nh nÃªn lÃ m gÃ¬ bÃ¢y giá»?", "Chá»‰ cáº§n láº¯ng nghe thÃ´i"],
        "the_dinh_kem": [],
    }

    rule_based = _rule_based_reply(user_text)
    if rule_based:
        # Shadow log until decide_sos() parity gate passes â€” do NOT delete _rule_based_reply yet.
        logger.info(
            "[ShadowCompare-RuleBasedReply] correlation_id=%s pattern triggered, LLM skipped. snippet=%.80r",
            correlation_id, rule_based,
        )
        payload["reply"] = rule_based
    elif settings.openai_api_key:
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
    safe_reply = _enforce_persona_identity(safe_reply, persona_id)
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
        "tone_cam_xuc": str(payload.get("tone_cam_xuc") or "xac_nhan"),
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
    graph = get_chat_graph()
    out = graph.invoke(
        {
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
            "correlation_id": correlation_id,
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
    )
    result = {
        "session_fields": snap,
        "reply": out.get("reply", ""),
        "tone_cam_xuc": out.get("tone_cam_xuc", "xac_nhan"),
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

    state: ChatGraphState = {
        "correlation_id": correlation_id,
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
    if route_after_distress_router(state) == "analyst":
        state.update(analyst_node(state))

    user_text = state.get("user_message", "")
    distress_now = float(state.get("distress_score") or 0.0)
    persona_id_active = str(state.get("active_persona_id") or DEFAULT_PERSONA_ID)
    hist = list(state.get("routing_history") or [])
    hist.append("friend")
    tone = "xac_nhan"
    attachments: list[dict[str, Any]] = []

    reply_text = ""
    _stream_model = ""
    _stream_system = ""
    _stream_user_payload = ""
    _stream_analyst_ctx = ""
    stream_messages: list[dict[str, str]] = []
    rule_based = _rule_based_reply(user_text)
    if rule_based:
        # Shadow log until decide_sos() parity gate passes â€” do NOT delete _rule_based_reply yet.
        logger.info(
            "[ShadowCompare-RuleBasedReply] correlation_id=%s stream pattern triggered. snippet=%.80r",
            correlation_id, rule_based,
        )
        reply_text = rule_based
    elif settings.openai_api_key:
        try:
            from openai import OpenAI

            use_fast_model = bool(state.get("use_fast_friend_model")) and distress_now < 0.55
            friend_temperature = _persona_temperature(persona_id_active, use_fast_model=use_fast_model)
            model = settings.openai_model_friend_fast if use_fast_model and settings.openai_model_friend_fast else settings.openai_model_friend
            _stream_model = model
            mentalchat_block = _build_mentalchat_examples(
                user_text, settings.openai_api_key or "", distress_score=distress_now
            )
            safe_mentalchat_block = _sanitize_prompt_block(mentalchat_block)
            base_system_prompt = (
                "Báº¡n lÃ  Friend, ngÆ°á»i Ä‘á»“ng hÃ nh áº¥m Ã¡p vÃ  thá»±c táº¿. "
                "LuÃ´n xÆ°ng mÃ¬nh/báº¡n, tuyá»‡t Ä‘á»‘i khÃ´ng dÃ¹ng mÃ y/tao. "
                "TÃªn hiá»ƒn thá»‹ báº¯t buá»™c lÃ  'Friend'; khÃ´ng tá»± giá»›i thiá»‡u báº±ng tÃªn khÃ¡c. "
                "Viáº¿t 3-5 cÃ¢u tiáº¿ng Viá»‡t, pháº£n chiáº¿u ná»—i Ä‘au cá»¥ thá»ƒ, xÃ¡c nháº­n cáº£m xÃºc lÃ  há»£p lÃ½, "
                "vÃ  Ä‘Æ°a má»™t bÆ°á»›c nhá» thá»±c táº¿ cÃ³ thá»ƒ lÃ m ngay. "
                "TrÃ¡nh sÃ¡o rá»—ng, khÃ´ng tráº£ lá»i kiá»ƒu máº«u, khÃ´ng há»i dá»“n dáº­p. "
                "Náº¿u ngÆ°á»i dÃ¹ng há»i báº¡n cÃ³ nhá»› há» hay khÃ´ng, chá»‰ tráº£ lá»i dá»±a trÃªn Lá»‹ch sá»­/KÃ½ á»©c trong context; náº¿u khÃ´ng cÃ³ dá»¯ liá»‡u thÃ¬ nÃ³i tháº­t lÃ  mÃ¬nh chÆ°a cÃ³ Ä‘á»§ kÃ½ á»©c."
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
            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 15.0))
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
            "tone_cam_xuc": tone,
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
    tone_cam_xuc: str,
    goi_y_nhanh: list[str],
    the_dinh_kem: list[dict[str, Any]],
    voice_hint: str | None = None,
    routing_history: list[str] | None = None,
) -> dict[str, Any]:
    show_quick_replies = _should_show_quick_replies(
        distress_score=float(snap.distress_score),
        conversation_mode=str(snap.conversation_mode),
    )
    return {
        "session_id": session_id,
        "agent_display_name": CHAT_AGENT_DISPLAY_NAME,
        "conversation_mode": snap.conversation_mode,
        "distress_score": snap.distress_score,
        "safety_tier": snap.safety_tier,
        "voice_session_offered": snap.safety_tier == "voice_recommended",
        "suggest_voice": snap.safety_tier == "voice_recommended",
        "voice_hint": voice_hint,
        "emergency_actions": None,
        "reply": reply,
        "tone_cam_xuc": tone_cam_xuc,
        "goi_y_nhanh": goi_y_nhanh if show_quick_replies else [],
        "the_dinh_kem": the_dinh_kem,
        "sos_triggered": False,
        "routing_history": routing_history or [],
    }



