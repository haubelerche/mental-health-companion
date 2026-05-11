"""Small deterministic emotional-state detector for response planning."""

from __future__ import annotations

from app.services.sos_handler import _normalize_text


def detect_emotional_state(message: str, *, distress_score: float = 0.0) -> str:
    normalized = _normalize_text(message)
    if any(k in normalized for k in ("qua doi", "ra di", "tang le")):
        return "grief_loss"
    if "mat" in normalized and "mat ngu" not in normalized:
        return "grief_loss"
    if any(k in normalized for k in ("tuyet vong", "khong co loi thoat", "khong tiep tuc")) or distress_score >= 0.72:
        return "despair_overload"
    if any(k in normalized for k in ("toi sai", "loi cua toi", "tu trach", "vo dung", "kem coi")):
        return "self_blame"
    if any(k in normalized for k in ("co don", "mot minh", "khong ai")):
        return "loneliness"
    if any(k in normalized for k in ("gian", "buc", "uc", "tra thu")):
        return "anger"
    if any(k in normalized for k in ("lo", "so", "bat an", "hoang")):
        return "anxiety"
    return "distress"
