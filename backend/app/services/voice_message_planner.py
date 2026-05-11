"""Deterministic voice script planner for Serene chat turns.

The policy engine decides how many voice cards are allowed. This module keeps
the spoken scripts short, Vietnamese, and different from visible text.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.voice.types import VoiceIntent, VoiceMessagePlan, VoicePriority, VoiceDedupePolicy

TEMPLATE_VERSION = "voice_policy_v1"


_INTENT_TITLES: dict[str, str] = {
    "sos_grounding": "Giu nhip an toan",
    "sos_stay_with_user": "O lai tung chut",
    "sos_next_safe_step": "Buoc an toan tiep theo",
    "elevated_encouragement": "Dong vien nhe",
    "elevated_lightness": "Nhe lai mot nhip",
    "elevated_gentle_reminder": "Nhac nhe cham lai",
    "casual_praise": "Ghi nhan no luc",
    "casual_playful_checkin": "Hoi tham nhe",
    "casual_habit_nudge": "Nhac thoi quen nho",
}

_SCRIPT_TEMPLATES: dict[str, str] = {
    "sos_grounding": (
        "Ban thu dat hai chan cham san. Hit vao nhe mot nhip, roi tho ra dai hon. "
        "Luc nay chi can o lai voi minh trong vai hoi tho truoc da."
    ),
    "sos_stay_with_user": (
        "Minh se di cham voi ban. Hay nhin quanh va goi ten mot vat gan nhat. "
        "Neu co the, dat tay len mat ban de cam thay minh dang o day."
    ),
    "sos_next_safe_step": (
        "Buoc tiep theo la dua minh den gan mot nguoi dang tin, hoac mo phan ho tro khan tren man hinh. "
        "Ban van co the nhan tin tiep voi minh tung cau ngan."
    ),
    "elevated_encouragement": (
        "Minh nghe la doan nay dang nang hon binh thuong. Ban khong can xu ly het ngay; "
        "chon mot viec nho nhat truoc, roi minh tinh tiep."
    ),
    "elevated_lightness": (
        "Nhac nhe thoi: dung de dau minh bat ban chay marathon trong mot phut. "
        "Tha vai xuong mot chut, roi lam tiep mot buoc nho."
    ),
    "elevated_gentle_reminder": (
        "Neu y nghi dang xoay nhanh, minh moi ban cham lai mot nhip. "
        "Viet ra dieu can lam ke tiep, chi mot dong thoi."
    ),
    "casual_praise": (
        "Cong nhan hom nay ban van dang co gang do. Khong can hoan hao ngay; "
        "co tien len mot doan la da dang duoc ghi nhan."
    ),
    "casual_playful_checkin": (
        "Minh ghe qua nhac nhe: nghi vai mot chut di. Lam tiep duoc, nhung dung ep minh qua tay."
    ),
    "casual_habit_nudge": (
        "Mot viec nho truoc da: uong nuoc, duoi vai, roi quay lai. Nhip cham mot chut van la tien do."
    ),
}


def intent_title(intent: str) -> str:
    return _INTENT_TITLES.get(intent, "Tin nhan thoai")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _too_similar(a: str, b: str) -> bool:
    left = set(_normalize(a).split())
    right = set(_normalize(b).split())
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= 0.6


def _safe_variant(script: str, index: int) -> str:
    prefixes = [
        "Minh noi cham lai nhe. ",
        "O doan nay, minh giu nhip that ngan. ",
        "Them mot nhip nho nua. ",
    ]
    prefix = prefixes[index % len(prefixes)]
    if script.startswith(prefix):
        return script
    return f"{prefix}{script}"


def build_voice_message_plan(
    *,
    plan_id: str,
    intent: VoiceIntent,
    priority: VoicePriority,
    dedupe_policy: VoiceDedupePolicy,
    visible_text: str = "",
    max_duration_seconds: int = 30,
    script_override: str | None = None,
    variant_index: int = 0,
    reason_codes: Iterable[str] = (),
) -> VoiceMessagePlan:
    script = (script_override or _SCRIPT_TEMPLATES[str(intent)]).strip()
    if _too_similar(script, visible_text):
        script = _safe_variant(_SCRIPT_TEMPLATES[str(intent)], variant_index)
    if variant_index:
        script = _safe_variant(script, variant_index)
    return VoiceMessagePlan(
        id=plan_id,
        intent=intent,
        voice_script=script,
        priority=priority,
        should_enqueue=True,
        dedupe_policy=dedupe_policy,
        max_duration_seconds=max_duration_seconds,
        reason_codes=list(reason_codes),
    )
