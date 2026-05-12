"""Conversation-quality and safety validation helpers for Serene output."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.services.microcopy_library import contains_generic_empathy
from app.services.sos_handler import _normalize_text


@dataclass(frozen=True)
class ResponseQualityVerdict:
    ok: bool
    reason_codes: list[str]


def count_questions(text: str) -> int:
    return text.count("?") + text.count("？")


_BANNED_NATURALNESS_PHRASES = (
    "một mẫu " + "cụ thể nhất",
    "một mẩu " + "cụ thể nhất",
    "mot mau cu the nhat",
    "mot mau cu the nhat",
    "mẫu cụ thể nhất",
    "mẩu cụ thể nhất",
    "mau cu the nhat",
    "tớ nghe chuyện",
    "to nghe chuyen",
    "không trôi " + "mất",
    "khong troi mat",
    "bạn có muốn chia sẻ thêm không",
    "ban co muon chia se them khong",
    "mọi chuyện rồi sẽ " + "ổn",
    "moi chuyen roi se on",
)

_DIAGNOSIS_LANGUAGE_RE = re.compile(
    r"\b(chẩn đoán|rối loạn|bệnh lý|diagnos|xác suất|tỉ lệ|khả năng cao|"
    r"trầm cảm|rối loạn lo âu|lưỡng cực|ptsd)\b",
    re.IGNORECASE,
)


def _fold_for_overlap(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", text or "")
    no_accent = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    no_accent = no_accent.replace("đ", "d").replace("Đ", "D").lower()
    return re.findall(r"[a-z0-9]+", no_accent)


def lexical_overlap(reply: str, user_message: str) -> float:
    """Return rough content-word overlap from the user's message into the reply."""
    user_tokens = {
        token
        for token in _fold_for_overlap(user_message)
        if len(token) >= 3
        and token
        not in {
            "minh",
            "ban",
            "cau",
            "toi",
            "cho",
            "voi",
            "nay",
            "kia",
            "qua",
            "that",
            "dang",
            "khong",
            "duoc",
        }
    }
    if not user_tokens:
        return 0.0
    reply_tokens = set(_fold_for_overlap(reply))
    return len(user_tokens & reply_tokens) / len(user_tokens)


def _meets_context_anchor(stripped: str) -> bool:
    """Heuristic for 'enough substance' without punishing normal short Vietnamese chat.

    A fixed 16-token minimum rejected most concise empathetic replies and forced
    deterministic fallbacks in ``build_response_plan``, making Serene feel templated.
    """
    if not stripped:
        return False
    if len(stripped) >= 40:
        return True
    return len(stripped.split()) >= 6


def count_sentences(text: str) -> int:
    parts = re.split(r"(?<=[.!?。！？])\s+", (text or "").strip())
    return len([part for part in parts if part.strip()])


def has_markdown(text: str) -> bool:
    return bool(re.search(r"(```|^\s*[-*+]\s+|[*_#>\[\]])", text or "", re.MULTILINE))


def validate_serene_response(
    text: str,
    *,
    user_message: str | None = None,
    require_context_anchor: bool = False,
    max_sentences: int | None = None,
    max_questions: int = 1,
    emotional_chat: bool = True,
) -> ResponseQualityVerdict:
    reasons: list[str] = []
    stripped = (text or "").strip()
    if not stripped:
        reasons.append("empty_response")
    if contains_generic_empathy(stripped):
        reasons.append("generic_empathy_loop")
    if contains_generic_empathy(_normalize_text(stripped)):
        reasons.append("generic_empathy_loop")
    lowered = stripped.lower()
    normalized = _normalize_text(stripped)
    if any(phrase in lowered or phrase in normalized for phrase in _BANNED_NATURALNESS_PHRASES):
        reasons.append("banned_naturalness_phrase")
    if count_questions(stripped) > max_questions:
        reasons.append("too_many_questions")
    if _DIAGNOSIS_LANGUAGE_RE.search(stripped) or _DIAGNOSIS_LANGUAGE_RE.search(normalized):
        reasons.append("diagnosis_language")
    if user_message and lexical_overlap(stripped, user_message) > 0.35:
        reasons.append("quote_overlap_too_high")
    if stripped.count("!") > 1:
        reasons.append("excessive_exclamation")
    if emotional_chat and has_markdown(stripped):
        reasons.append("markdown_in_emotional_chat")
    if max_sentences is not None and count_sentences(stripped) > max_sentences:
        reasons.append("too_many_sentences")
    if require_context_anchor and not _meets_context_anchor(stripped):
        reasons.append("missing_context_anchor")
    normalized_reasons = sorted(set(reasons))
    return ResponseQualityVerdict(ok=not normalized_reasons, reason_codes=normalized_reasons)
