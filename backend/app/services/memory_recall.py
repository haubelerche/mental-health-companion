"""Deterministic memory-recall handling for factual chat turns."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.memory.service import get_user_cards
from app.services.db.models import UserProfile
from app.services.longterm_memory import build_user_memory_context
from app.services.pii_mask import mask_pii
from app.services.safety_scoring import build_snapshot

TurnKind = Literal["normal_conversation", "factual_memory_recall", "identity_recall", "greeting", "safety"]

_IDENTITY_RE = re.compile(
    r"\b("
    r"(toi|tui|minh|tao)\s+la\s+ai|"
    r"(ban|cau|serene).{0,24}(nho|biet).{0,24}(toi|tui|minh|tao)\s+la\s+ai|"
    r"(nho|biet).{0,24}(toi|tui|minh|tao)\s+la\s+ai"
    r")\b"
)
_RECALL_RE = re.compile(
    r"\b(nho|lan truoc|hom qua|hoi thoai truoc|truoc do|ban con nho|nhac lai|tiep tuc|tung noi|da ke)\b"
)
_GREETING_RE = re.compile(r"^\s*(chao|hello|hi|hey|alo|yo|xin chao|ê|e)\b[\s!.?]*$")
_PROMPT_EXTRACTION_RE = re.compile(
    r"\b(system prompt|developer prompt|prompt|instruction|chi dan|system|jailbreak|hidden prompt)\b"
)


@dataclass(frozen=True)
class RecallReply:
    turn_kind: TurnKind
    reply: str
    memory_source_counts: dict[str, int] = field(default_factory=dict)
    active_memory_text: str = ""
    refused_prompt_extraction: bool = False

    def as_turn(self) -> dict[str, Any]:
        settings = get_settings()
        snap = build_snapshot(
            0.12,
            sos_triggered=False,
            voice_hint=settings.distress_voice_hint,
            critical=settings.distress_critical,
        )
        return {
            "session_fields": snap,
            "reply": self.reply,
            "assistant_tone": "neutral",
            "goi_y_nhanh": [],
            "the_dinh_kem": [],
            "routing_history": ["memory_recall"],
            "turn_kind": self.turn_kind,
            "memory_source_counts": dict(self.memory_source_counts),
            "active_memory_text_len": len(self.active_memory_text),
            "recall_handler_hit": True,
        }


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", text.lower()).strip()


def classify_turn_kind(user_text: str, *, sos_triggered: bool = False) -> TurnKind:
    if sos_triggered:
        return "safety"
    normalized = _normalize_text(user_text)
    if _IDENTITY_RE.search(normalized):
        return "identity_recall"
    if _RECALL_RE.search(normalized):
        return "factual_memory_recall"
    if _GREETING_RE.search(normalized):
        return "greeting"
    return "normal_conversation"


def _is_prompt_extraction_attempt(user_text: str) -> bool:
    normalized = _normalize_text(user_text)
    return bool(_PROMPT_EXTRACTION_RE.search(normalized) and _RECALL_RE.search(normalized))


def _safe_fact(text: str) -> str:
    fact = " ".join(mask_pii(str(text or "")).split()).strip()
    fact = re.sub(r"^(bạn|ban|người dùng|nguoi dung|user)\s+(đã|da)\s+", "", fact, flags=re.IGNORECASE).strip()
    return fact[:220].rstrip(" ,.;")


def _collect_profile_facts(db: Session, *, user_id: str) -> tuple[list[str], dict[str, int]]:
    facts: list[str] = []
    counts: dict[str, int] = {"profile": 0}
    try:
        row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    except Exception:
        row = None
    data = dict(getattr(row, "profile", None) or {}) if row else {}
    onboarding = dict(data.get("onboarding") or {})
    for key in ("primary_concern", "emotional_state", "support_level"):
        value = str(onboarding.get(key) or "").strip()
        if value:
            facts.append(f"{key}: {value}")
    traits = dict(data.get("traits") or {})
    for key in ("preferred_tone", "communication_style"):
        value = str(traits.get(key) or "").strip()
        if value:
            facts.append(f"{key}: {value}")
    counts["profile"] = len(facts)
    return facts, counts


def _collect_memory_facts(db: Session, *, user_id: str, user_text: str) -> tuple[list[str], dict[str, int]]:
    counts = {"visible_memories": 0, "mem0_facts": 0, "profile": 0, "recent_summaries": 0}
    facts: list[str] = []

    try:
        visible_cards = get_user_cards(db, user_id=user_id)
    except Exception:
        visible_cards = []
    visible_cards = [
        item
        for item in visible_cards
        if item.status in {"active", "edited_by_user", "pending_user_review"}
        and not bool(item.personalization_disabled)
    ][:6]
    counts["visible_memories"] = len(visible_cards)
    facts.extend(_safe_fact(item.content) for item in visible_cards if _safe_fact(item.content))

    memory_ctx = None
    try:
        memory_ctx = build_user_memory_context(db, user_id=user_id, current_query=user_text)
    except Exception:
        memory_ctx = None
    if memory_ctx is not None:
        mem0_facts = [_safe_fact(item) for item in list(memory_ctx.mem0_facts or []) if _safe_fact(item)]
        summaries = [_safe_fact(item) for item in list(memory_ctx.recent_summaries or []) if _safe_fact(item)]
        counts["mem0_facts"] = len(mem0_facts)
        counts["recent_summaries"] = len(summaries)
        facts.extend(mem0_facts)
        facts.extend(summaries)
        for value in list((memory_ctx.onboarding or {}).values())[:3]:
            fact = _safe_fact(value)
            if fact:
                facts.append(fact)

    profile_facts, profile_counts = _collect_profile_facts(db, user_id=user_id)
    counts["profile"] = profile_counts.get("profile", 0)
    facts.extend(_safe_fact(item) for item in profile_facts if _safe_fact(item))

    deduped: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        key = _normalize_text(fact)
        if not key or key in seen:
            continue
        if _PROMPT_EXTRACTION_RE.search(key):
            continue
        seen.add(key)
        deduped.append(fact)
    return deduped, counts


def try_handle_memory_recall_turn(
    db: Session,
    *,
    user_id: str,
    session_id: str,
    user_text: str,
    recent_messages: list[dict[str, Any]] | None = None,
    turn_kind: TurnKind | None = None,
) -> RecallReply | None:
    _ = session_id, recent_messages
    kind = turn_kind or classify_turn_kind(user_text)
    if kind not in {"identity_recall", "factual_memory_recall"}:
        return None

    if _is_prompt_extraction_attempt(user_text):
        return RecallReply(
            turn_kind=kind,
            reply="Mình không thể nhắc lại system prompt hay chỉ dẫn nội bộ. Mình chỉ có thể nhắc những ký ức người dùng đã chia sẻ và được lưu lại.",
            refused_prompt_extraction=True,
        )

    facts, counts = _collect_memory_facts(db, user_id=user_id, user_text=user_text)
    active_memory_text = "\n".join(f"- {fact}" for fact in facts[:3])
    if not facts:
        return RecallReply(
            turn_kind=kind,
            reply=(
                "Mình chưa có đủ ký ức đã lưu để nói chắc cậu là ai. "
                "Cậu có thể kể lại một chút; nếu cậu muốn, mình sẽ ghi nhớ điều đó cho những lần sau."
            ),
            memory_source_counts=counts,
            active_memory_text="",
        )

    fact = facts[0]
    if kind == "identity_recall":
        reply = (
            f"Có. Mình nhớ một điều cậu từng chia sẻ: {fact}. "
            "Mình chỉ dựa trên ký ức đã lưu, nên nếu chỗ nào chưa đúng cậu có thể chỉnh trong tab Ký ức."
        )
    else:
        reply = f"Mình nhớ điều này từ ký ức đã lưu: {fact}. Nếu cậu muốn, mình có thể nối tiếp từ chi tiết đó."
    return RecallReply(
        turn_kind=kind,
        reply=reply,
        memory_source_counts=counts,
        active_memory_text=active_memory_text,
    )
