from __future__ import annotations

import re
from dataclasses import dataclass


_UNVERIFIED_CLINICAL_PATTERNS = [
    re.compile(r"\b(chan doan|chẩn đoán|diagnose|prescribe|kê đơn)\b", re.IGNORECASE),
    re.compile(r"\b(uong thuoc|uống thuốc|thuoc nay|liều)\b", re.IGNORECASE),
]
_ALLOWED_ENTITIES = (
    "vinmec",
    "115",
    "18001567",
    "1800 1567",
    "1800599920",
    "1800 599 920",
)


@dataclass
class GroundingResult:
    reply: str
    grounded: bool
    reasons: list[str]


def sanitize_grounded_reply(reply: str, retrieved_context: str = "") -> GroundingResult:
    text = (reply or "").strip()
    reasons: list[str] = []
    if not text:
        return GroundingResult(
            reply="Mình ở đây để đồng hành cùng bạn. Bạn có thể chia sẻ thêm để mình hỗ trợ an toàn hơn nhé.",
            grounded=False,
            reasons=["empty_reply"],
        )

    lowered = text.lower()
    context = (retrieved_context or "").lower()

    for patt in _UNVERIFIED_CLINICAL_PATTERNS:
        if patt.search(text) and not patt.search(retrieved_context):
            reasons.append("unverified_clinical_claim")
            break

    if any(entity in lowered for entity in _ALLOWED_ENTITIES):
        if not any(entity in context for entity in _ALLOWED_ENTITIES):
            reasons.append("unverified_external_entity")

    if reasons:
        safe = (
            "Mình sẽ ưu tiên thông tin an toàn và đã kiểm chứng. "
            "Nếu bạn đang khủng hoảng ngay lúc này, hãy gọi 115 hoặc 1800 1567 để nhận hỗ trợ khẩn cấp."
        )
        return GroundingResult(reply=safe, grounded=False, reasons=reasons)

    return GroundingResult(reply=text, grounded=True, reasons=[])
