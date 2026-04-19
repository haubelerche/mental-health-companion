"""Mask PII before persisting messages (API_SPEC §9.3)."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_PHONE_VN = re.compile(r"\b(?:\+84|0)[3-9]\d{8}\b")
_DIGITS_LONG = re.compile(r"\b\d{9,12}\b")


def mask_pii(text: str) -> str:
    s = _EMAIL.sub("[EMAIL]", text)
    s = _PHONE_VN.sub("[PHONE]", s)
    s = _DIGITS_LONG.sub("[ID]", s)
    return s
