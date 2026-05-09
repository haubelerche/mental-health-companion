from __future__ import annotations

import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

PeriodKind = Literal["day", "week", "month"]

def get_now() -> datetime:
    """Returns the current time in Asia/Ho_Chi_Minh with timezone info."""
    return datetime.now(VN_TZ)

def utc_now() -> datetime:
    """Returns the current time in UTC (Legacy, prefer get_now)."""
    return datetime.now(timezone.utc)

def now_plus(days: int = 0, seconds: int = 0) -> datetime:
    """Returns get_now() plus offset."""
    return get_now() + timedelta(days=days, seconds=seconds)

def local_date_utc7(source: datetime | None = None) -> date:
    """Returns the date in VN timezone."""
    point = source or get_now()
    if point.tzinfo is None:
        # If naive, assume it was intended to be VN time or convert if it was UTC
        # For safety, let's just ensure we return the date part of a VN-aware datetime
        return point.astimezone(VN_TZ).date()
    return point.astimezone(VN_TZ).date()

def vn_period_inclusive_dates(kind: PeriodKind, ref: date | None = None) -> tuple[date, date]:
    """
    Inclusive calendar bounds in Asia/Ho_Chi_Minh for dashboard KPIs.
    """
    today = ref or local_date_utc7()
    if kind == "day":
        return today, today
    if kind == "week":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday
    first = today.replace(day=1)
    return first, today

def vn_month_chart_range() -> tuple[date, date, int]:
    """Returns (start_of_month, today, days_in_range) in VN time."""
    today = local_date_utc7()
    start = today.replace(day=1)
    span = (today - start).days + 1
    return start, today, span

def vn_week_chart_range() -> tuple[date, date, int]:
    """Returns (monday, sunday, 7) in VN time."""
    today = local_date_utc7()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday, 7

def vn_period_utc_range(kind: str) -> tuple[date, date, datetime, datetime]:
    """
    Returns (date_from, date_to, start_naive, end_naive) 
    corresponding to local VN boundaries for DB queries.
    """
    date_from, date_to = vn_period_inclusive_dates(kind)
    start_naive = datetime.combine(date_from, time.min)
    end_naive = datetime.combine(date_to, time.max) + timedelta(microseconds=1)
    return date_from, date_to, start_naive, end_naive

def make_id(prefix: str, size: int = 10) -> str:
    token = "".join(secrets.choice(ID_ALPHABET) for _ in range(size))
    return f"{prefix}_{token}"

def get_youtube_id(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:v=|\/|embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None

def make_anon_name() -> str:
    adjectives = [
        "Nhỏ", "Bình Yên", "Mạnh Mẽ", "Hy Vọng", "Tự Do",
        "Dịu Dàng", "Kiên Cường", "Ấm Áp", "Lặng Lẽ", "Sáng Suốt"
    ]
    nouns = [
        "Mèo", "Gió", "Nắng", "Mây", "Cánh Diều",
        "Hạt Mầm", "Ngôi Sao", "Dòng Sông", "Chiếc Lá", "Biển Cả"
    ]
    return f"{secrets.choice(nouns)} {secrets.choice(adjectives)}"
