"""Normalization and display helpers for atomic memory cards."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from app.services.db.models import MemoryCard


def normalize_memory_text(text: str) -> str:
    raw = unicodedata.normalize("NFD", str(text or "").lower())
    without_marks = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    asciiish = without_marks.replace("đ", "d")
    asciiish = re.sub(r"[^a-z0-9]+", " ", asciiish)
    return " ".join(asciiish.split()).strip()


def build_memory_canonical_key(
    *,
    user_id: str,
    memory_type: str,
    subject: str,
    predicate: str,
) -> str:
    normalized = "|".join(
        [
            normalize_memory_text(user_id),
            normalize_memory_text(memory_type),
            normalize_memory_text(subject),
            normalize_memory_text(predicate),
        ]
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"mem:{digest}"


def merge_evidence_message_ids(existing: Any, incoming: Any) -> list[str]:
    merged: list[str] = []
    for value in list(existing or []) + list(incoming or []):
        item = str(value or "").strip()
        if item and item not in merged:
            merged.append(item)
    return merged[:40]


def _phrase_after_that(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip().rstrip(".!?")
    prefixes = (
        "Bạn từng nói ",
        "Bạn đã chia sẻ rằng ",
        "Bạn có vẻ ",
        "Bạn thường ",
        "Serene có thể nhớ rằng ",
    )
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            return cleaned[len(prefix):].strip()
    return cleaned[:1].lower() + cleaned[1:] if cleaned else "điều này quan trọng với bạn"


def build_memory_display_text(card: MemoryCard) -> str:
    mention_count = int(getattr(card, "mention_count", 1) or 1)
    base = str(getattr(card, "content", "") or getattr(card, "normalized_text", "") or "").strip()
    subject = str(getattr(card, "subject", "") or "").replace("_", " ").strip()
    predicate = str(getattr(card, "predicate", "") or "").replace("_", " ").strip()
    phrase = _phrase_after_that(base)
    if mention_count >= 3:
        if subject:
            return f"Bạn thường nhắc đến {subject} như một điều đáng chú ý."
        return f"Bạn thường nhắc đến {phrase}."
    if mention_count == 2:
        return f"Bạn nhắc lại 2 lần rằng {phrase}."
    return base
