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
    "sos_grounding": "Giữ nhịp an toàn",
    "sos_stay_with_user": "Ở lại từng chút",
    "sos_next_safe_step": "Bước an toàn tiếp theo",
    "elevated_encouragement": "Động viên nhẹ",
    "elevated_lightness": "Nhẹ lại một nhịp",
    "elevated_gentle_reminder": "Nhắc nhẹ chậm lại",
    "casual_praise": "Ghi nhận nỗ lực",
    "casual_playful_checkin": "Hỏi thăm nhẹ",
    "casual_habit_nudge": "Nhắc thói quen nhỏ",
}

_SCRIPT_TEMPLATES: dict[str, str] = {
    "sos_grounding": (
        "Bạn thử đặt hai chân chạm sàn. Hít vào nhẹ một nhịp, rồi thở ra dài hơn. "
        "Lúc này chỉ cần ở lại với mình trong vài hơi thở trước đã."
    ),
    "sos_stay_with_user": (
        "Mình sẽ đi chậm với bạn. Hãy nhìn quanh và gọi tên một vật gần nhất. "
        "Nếu có thể, đặt tay lên mặt bàn để cảm thấy mình đang ở đây."
    ),
    "sos_next_safe_step": (
        "Bước tiếp theo là đưa mình đến gần một người đáng tin, hoặc mở phần hỗ trợ khẩn trên màn hình. "
        "Bạn vẫn có thể nhắn tin tiếp với mình từng câu ngắn."
    ),
    "elevated_encouragement": (
        "Mình nghe là đoạn này đang nặng hơn bình thường. Bạn không cần xử lý hết ngay; "
        "chọn một việc nhỏ nhất trước, rồi mình tính tiếp."
    ),
    "elevated_lightness": (
        "Nhắc nhẹ thôi: đừng để đầu mình bắt bạn chạy marathon trong một phút. "
        "Thả vai xuống một chút, rồi làm tiếp một bước nhỏ."
    ),
    "elevated_gentle_reminder": (
        "Nếu ý nghĩ đang xoay nhanh, mình mời bạn chậm lại một nhịp. "
        "Viết ra điều cần làm kế tiếp, chỉ một dòng thôi."
    ),
    "casual_praise": (
        "Công nhận hôm nay bạn vẫn đang cố gắng đó. Không cần hoàn hảo ngay; "
        "cố tiến lên một đoạn là đã đáng được ghi nhận."
    ),
    "casual_playful_checkin": (
        "Mình ghé qua nhắc nhẹ: nghỉ vài một chút đi. Làm tiếp được, nhưng đừng ép mình quá tay."
    ),
    "casual_habit_nudge": (
        "Một việc nhỏ trước đã: uống nước, duỗi vai, rồi quay lại. Nhịp chậm một chút vẫn là tiến độ."
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
