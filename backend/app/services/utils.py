from __future__ import annotations
import re

import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

PeriodKind = Literal["day", "week", "month"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def now_plus(days: int = 0, seconds: int = 0) -> datetime:
    return utc_now() + timedelta(days=days, seconds=seconds)


def local_date_utc7(source: datetime | None = None):
    point = source or utc_now()
    return point.astimezone(VN_TZ).date()


def utc_naive_vn_midnight(d: date) -> datetime:
    """Start of calendar day ``d`` in Vietnam, stored as naive UTC (matches DB timestamps)."""
    dt = datetime.combine(d, time.min, tzinfo=VN_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def vn_period_inclusive_dates(kind: PeriodKind, ref: date | None = None) -> tuple[date, date]:
    """
    Inclusive calendar bounds in Asia/Ho_Chi_Minh for dashboard KPIs.

    - day: today only
    - week: ISO week Mon–Sun containing ``ref`` (full week; future days simply have no activity yet)
    - month: month-to-date (1st of month through ``ref``)
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


def vn_period_utc_range(kind: PeriodKind, ref: date | None = None) -> tuple[date, date, datetime, datetime]:
    """
    Returns ``date_from``, ``date_to`` (inclusive, VN calendar), ``start_utc_naive`` inclusive,
    ``end_utc_naive`` exclusive for filtering ``DateTime`` columns stored as naive UTC.
    """
    date_from, date_to = vn_period_inclusive_dates(kind, ref=ref)
    start = utc_naive_vn_midnight(date_from)
    end = utc_naive_vn_midnight(date_to + timedelta(days=1))
    return date_from, date_to, start, end


def vn_month_chart_range(ref: date | None = None) -> tuple[date, date, int]:
    """First day of month through ``ref`` (inclusive) and number of days in that span."""
    today = ref or local_date_utc7()
    first = today.replace(day=1)
    n = (today - first).days + 1
    return first, today, n


def vn_week_chart_range(ref: date | None = None) -> tuple[date, date, int]:
    """Rolling last 7 days ending on ``ref`` (inclusive), 7 points."""
    today = ref or local_date_utc7()
    start = today - timedelta(days=6)
    return start, today, 7


def make_id(prefix: str, size: int = 10) -> str:
    token = "".join(secrets.choice(ID_ALPHABET) for _ in range(size))
    return f"{prefix}_{token}"


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

def get_youtube_id(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:v=|\/|embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None

