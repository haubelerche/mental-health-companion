"""Danh sách phòng khám/tư vấn tâm lý: tải từ JSON, tính khoảng cách (Haversine) trong bộ nhớ.

Tọa độ user không được lưu — chỉ dùng để sort/filter response (xem API_SPEC /connect/clinics).
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "clinics_vn.json"

# Bounding box gần đúng nội thành Hà Nội — dùng cho danh sách mặc định khi không có GPS (API spec).
_HANOI_LAT_MIN, _HANOI_LAT_MAX = 20.95, 21.15
_HANOI_LNG_MIN, _HANOI_LNG_MAX = 105.72, 105.92

_DEFAULT_RADIUS_KM = 25


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Khoảng cách đường chim bay giữa hai điểm WGS84, đơn vị km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


@lru_cache(maxsize=1)
def _load_clinics() -> tuple[dict[str, object], ...]:
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("clinics_vn.json must be a JSON array")
    out: list[dict[str, object]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f"clinics_vn.json[{i}] must be an object")
        for key in ("id", "name", "address", "lat", "lng", "phone", "hours"):
            if key not in row:
                raise ValueError(f"clinics_vn.json[{i}] missing {key!r}")
        out.append(dict(row))
    return tuple(out)


def _in_hanoi_default_area(lat: float, lng: float) -> bool:
    return _HANOI_LAT_MIN <= lat <= _HANOI_LAT_MAX and _HANOI_LNG_MIN <= lng <= _HANOI_LNG_MAX


def clinics_for_default_list() -> list[dict[str, object]]:
    """Khi user không gửi GPS: danh sách gợi ý khu vực Hà Nội (không có distance_km)."""
    rows = [dict(c) for c in _load_clinics() if _in_hanoi_default_area(float(c["lat"]), float(c["lng"]))]
    rows.sort(key=lambda x: str(x["name"]))
    for r in rows:
        r["distance_km"] = None
    if not rows:
        rows = [dict(c) for c in _load_clinics()]
        for r in rows:
            r["distance_km"] = None
    return rows


def clinics_near(lat: float, lng: float, radius_km: int | None) -> list[dict[str, object]]:
    """Lọc phòng khám trong bán kính, sort tăng dần theo khoảng cách."""
    limit = radius_km if radius_km is not None else _DEFAULT_RADIUS_KM
    enriched: list[tuple[float, dict[str, object]]] = []
    for c in _load_clinics():
        d = haversine_km(lat, lng, float(c["lat"]), float(c["lng"]))
        if d <= limit:
            row = dict(c)
            row["distance_km"] = round(d, 1)
            enriched.append((d, row))
    enriched.sort(key=lambda x: x[0])
    return [row for _, row in enriched]
