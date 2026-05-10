"""Deterministic interaction-need classifier for Vietnamese chat turns."""

from __future__ import annotations

from typing import Literal

from app.services.sos_handler import _normalize_text

InteractionNeed = Literal["venting", "grief", "reassurance", "advice", "grounding", "safety"]


def classify_interaction_need(message: str, *, distress_score: float = 0.0, sos_triggered: bool = False) -> InteractionNeed:
    if sos_triggered or distress_score >= 0.88:
        return "safety"
    normalized = _normalize_text(message)
    if any(k in normalized for k in ("qua doi", "ra di", "tang le", "khong con nua", "nguoi than")):
        return "grief"
    if "mat" in normalized and "mat ngu" not in normalized:
        return "grief"
    if any(k in normalized for k in ("lam sao", "nen lam gi", "giai quyet", "ke hoach", "cach nao")):
        return "advice"
    if any(k in normalized for k in ("hoang", "run", "kho tho", "qua tai", "roi qua", "nghet")):
        return "grounding"
    if any(k in normalized for k in ("co phai", "dung khong", "toi sai", "minh sai", "yeu duoi")):
        return "reassurance"
    return "venting"
