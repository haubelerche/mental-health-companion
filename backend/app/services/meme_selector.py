from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import TypedDict


class MemeSuggestion(TypedDict, total=False):
    id: str
    image_path: str
    alt: str
    trigger_reason: str


_EMOTION_MEMES: tuple[str, ...] = (
    "agree.jpg",
    "at-least-you-tried.jpg",
    "brilliant.jpg",
    "burnt-out.jpg",
    "cheer-up.jpg",
    "clown.jpg",
    "confusion.jpg",
    "disappointed.jpg",
    "disbelieve.jpg",
    "embarrasing.jpg",
    "get-well-soon.jpg",
    "good-morning-user.jpg",
    "good-morning.jpg",
    "good-night-2.jpg",
    "good-night.jpg",
    "good_job.jpg",
    "happy.jpg",
    "i-love-you.jpg",
    "im-listening-to-you.jpg",
    "knowledgeable.jpg",
    "sad.jpg",
    "shocked.jpg",
    "silent.jpg",
    "stop-it-get-some-help.jpg",
    "stop-user-from-negativity.jpg",
    "try-hard.jpg",
    "user-is-tired.jpg",
    "very-sad.jpg",
    "you-can-do-it.jpg",
    "you-need-therapy.jpg",
    "you-should-go-outside.jpg",
    "your-doing-amazing.jpg",
)

_CONTEXTUAL_MEMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("good-morning-user.jpg", ("chao buoi sang", "sang nay", "morning")),
    ("good-night.jpg", ("ngu ngon", "toi roi", "khuya", "dem")),
    ("burnt-out.jpg", ("deadline", "han nop", "qua tai", "kiet suc", "burnout", "met qua")),
    ("user-is-tired.jpg", ("met", "duoi", "het pin", "khong con suc")),
    ("im-listening-to-you.jpg", ("chi can lang nghe", "chi muon ke", "nghe minh", "tam su")),
    ("you-can-do-it.jpg", ("co len", "thi", "on thi", "hoc tiep", "lam tiep")),
    ("good_job.jpg", ("xong roi", "lam duoc", "nop bai", "qua mon", "hoan thanh")),
    ("confusion.jpg", ("roi", "khong hieu", "bi dung hinh", "khong biet bat dau")),
    ("cheer-up.jpg", ("buon", "that vong", "te qua")),
    ("agree.jpg", ("dung vay", "that", "qua chuan")),
    ("happy.jpg", ("vui", "nhe long", "on hon")),
)

_HOLD_MEME_HINTS = (
    "tuyet vong",
    "bien mat",
    "khong muon tiep tuc",
    "tu tu",
    "chet",
    "khong con suc",
    "khong muon noi nhieu",
)


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("Ä‘", "d").replace("đ", "d")
    return re.sub(r"\s+", " ", folded.lower()).strip()


def _pick_contextual_filename(text: str) -> tuple[str, str] | None:
    normalized = _normalize(text)
    for filename, triggers in _CONTEXTUAL_MEMES:
        if any(trigger in normalized for trigger in triggers):
            return filename, f"context:{filename.rsplit('.', 1)[0]}"
    return None


def _next_unused_filename(seed: str, used_filenames: set[str]) -> str | None:
    available = [filename for filename in _EMOTION_MEMES if filename not in used_filenames]
    if not available:
        return None
    pick = int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8], 16) % len(available)
    return available[pick]


def _meme_id_for(filename: str) -> str:
    try:
        idx = _EMOTION_MEMES.index(filename)
    except ValueError:
        idx = int(hashlib.sha1(filename.encode("utf-8")).hexdigest()[:8], 16) % 1000
    return f"emotion_{idx}"


def maybe_select_meme_suggestion(
    *,
    persona_id: str,
    safety_tier: str,
    distress_score: float,
    session_id: str,
    assistant_turn_index: int,
    cooldown_turns: int = 1,
    user_message: str = "",
    assistant_text: str = "",
    previous_meme_image_paths: list[str] | tuple[str, ...] | None = None,
) -> MemeSuggestion | None:
    """
    Context-aware playful meme policy for `dung_luong` only.

    - Scope: normal chat, low distress, persona `dung_luong`.
    - Cadence is controlled by the router via cooldown_turns / turn index.
    - Does not repeat an image already used in the same conversation while unused assets remain.
    """
    if persona_id != "dung_luong":
        return None
    if safety_tier != "normal":
        return None
    if distress_score >= 0.5:
        return None
    combined = f"{user_message} {assistant_text}"
    normalized = _normalize(combined)
    if any(token in normalized for token in _HOLD_MEME_HINTS):
        return None
    if assistant_turn_index <= 0:
        return None
    if assistant_turn_index % cooldown_turns != 0:
        return None

    used_filenames = {
        str(item or "").rsplit("/", 1)[-1].strip()
        for item in (previous_meme_image_paths or [])
        if str(item or "").strip()
    }

    contextual = _pick_contextual_filename(combined)
    if contextual:
        filename, reason = contextual
        if filename in used_filenames:
            filename = _next_unused_filename(
                f"{session_id}:{assistant_turn_index}:{reason}:alternate",
                used_filenames,
            )
            reason = "context_alternate"
        if not filename:
            return None
        return {
            "id": _meme_id_for(filename),
            "image_path": filename,
            "alt": "Meme cảm xúc phù hợp với ngữ cảnh",
            "trigger_reason": f"dung_luong_{reason}",
        }

    pick_seed = f"{session_id}:{assistant_turn_index}:asset"
    filename = _next_unused_filename(pick_seed, used_filenames)
    if not filename:
        return None
    return {
        "id": _meme_id_for(filename),
        "image_path": filename,
        "alt": "Emotion meme",
        "trigger_reason": "dung_luong_emotion_meme",
    }
