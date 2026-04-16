from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def utc_now() -> datetime:
    return datetime.now(UTC)


def now_plus(days: int = 0, seconds: int = 0) -> datetime:
    return utc_now() + timedelta(days=days, seconds=seconds)


def local_date_utc7(source: datetime | None = None):
    point = source or utc_now()
    return point.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def make_id(prefix: str, size: int = 10) -> str:
    token = "".join(secrets.choice(ID_ALPHABET) for _ in range(size))
    return f"{prefix}_{token}"
