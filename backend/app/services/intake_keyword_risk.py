"""
Keyword-based intake risk score (0.0–1.0) for Vietnamese free text.

- Một lớp regex Unicode cho cụm rõ nghĩa (vd. "tự tử" ≠ "từ từ" sau khi bỏ dấu).
- Lớp cụm đã chuẩn hóa (bỏ dấu, đ→d) để khớp telex / không dấu.
- Không dùng cụm đã chuẩn hóa "tu tu" đơn lẻ (trùng "tự tử" và "từ từ").
"""

from __future__ import annotations

import re
import unicodedata

# Khớp trên chuỗi gốc (có dấu) — phân tách "tự tử" / "tự sát" với "từ từ".
_UNICODE_CRITICAL: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"tự\s*tử", re.IGNORECASE), 0.95),
    (re.compile(r"tự\s*sát", re.IGNORECASE), 0.95),
    (re.compile(r"tự\s*hại", re.IGNORECASE), 0.92),
    (re.compile(r"tự\s*vẫn", re.IGNORECASE), 0.94),
    (re.compile(r"tự\s*giết", re.IGNORECASE), 0.92),
    (re.compile(r"không\s*muốn\s*sống", re.IGNORECASE), 0.93),
    (re.compile(r"chẳng\s*muốn\s*sống", re.IGNORECASE), 0.93),
]

# Trọng số cụm sau normalize. Nhiều cụm khớp → max + boost nhỏ.
_CRITICAL = [
    ("tu sat", 0.95),
    ("tu hai", 0.92),
    ("tu giet", 0.92),
    ("lam hai ban than", 0.94),
    ("lam hai minh", 0.93),
    ("muon chet", 0.94),
    ("buon chet", 0.93),
    ("chang muon song", 0.93),
    ("khong muon song", 0.93),
    ("khong con muon song", 0.94),
    ("ket thuc cuoc doi", 0.93),
    ("ket thuc doi minh", 0.93),
    ("ket lieu", 0.9),
    ("tim cach chet", 0.94),
    ("chet di duoc roi", 0.9),
    ("chet cho roi", 0.9),
    ("chet di", 0.88),
    ("chet roi hay hon", 0.85),
    ("nhay xuong", 0.88),
    ("nhay lau", 0.88),
    ("nhay cau", 0.87),
    ("treo co", 0.9),
    ("cat tay", 0.88),
    ("cat co tay", 0.88),
    ("uong het thuoc", 0.88),
    ("uong thuoc", 0.72),
    ("overdose", 0.88),
    ("suicide", 0.92),
    ("self harm", 0.9),
    ("kill myself", 0.9),
    ("ngu mai mai", 0.88),
    ("ngu khong day", 0.87),
    ("khong day nua", 0.86),
    ("di xa khong ve", 0.85),
    ("di mot chieu", 0.82),
    ("thoat khoi cuoc doi", 0.9),
    ("giai thoat", 0.85),
    ("buong xuoi het", 0.84),
    ("buong xuoi", 0.78),
    ("lam dieu dai dot", 0.86),
    ("hai ban than", 0.85),
    ("hai minh", 0.84),
    ("muon tu tu", 0.96),
    ("y dinh tu tu", 0.95),
    ("ke hoach tu sat", 0.94),
    ("se tu sat", 0.93),
    ("toi muon chet", 0.95),
    ("moi muon chet", 0.94),
    ("song khong noi", 0.92),
    ("song nua lam gi", 0.91),
    ("chet di cho roi", 0.89),
    ("ra di vinh vien", 0.88),
    ("ket thuc moi thu", 0.89),
    ("khong con gi de song", 0.91),
    ("tuc chet di", 0.87),
    ("chet cho xong", 0.86),
    ("tuc minh chet qua", 0.85),
    ("cutting", 0.88),
    ("tu ket lieu", 0.93),
    ("muon bien mat", 0.89),
    ("khong muon ton tai", 0.90),
    ("xoa so ban than", 0.88),
]

_SEVERE = [
    ("tuyet vong", 0.82),
    ("het hy vong", 0.82),
    ("het cuu", 0.82),
    ("khong con hy vong", 0.82),
    ("khong con loi thoat", 0.83),
    ("vo vong", 0.8),
    ("chan doi", 0.78),
    ("dau long", 0.78),
    ("dau don vo cung", 0.8),
    ("khong the chiu noi", 0.8),
    ("khong chiu noi nua", 0.8),
    ("sup do roi", 0.76),
    ("tram cam nang", 0.78),
    ("tram cam tram trong", 0.8),
    ("benh tam than", 0.65),
    ("khong an toan", 0.75),
    ("cam thay nguy hiem", 0.74),
    ("so minh lam dieu du dai", 0.8),
    ("so minh khong kiem che", 0.78),
    ("mat kiem soat", 0.72),
    ("hoan toan kiet que", 0.78),
    ("kiet suc", 0.7),
    ("qua dau kho", 0.72),
    ("cuc ky tuyet vong", 0.82),
    ("het roi", 0.68),
    ("ket thuc het", 0.72),
    ("ket thuc", 0.62),
    ("chang ai can", 0.7),
    ("vo ich het", 0.72),
    ("song cung the", 0.7),
    ("song de lam gi", 0.74),
    ("cuoc doi vo nghia", 0.82),
    ("song nhu chet", 0.82),
    ("dau kho qua", 0.81),
    ("sup do hoan toan", 0.81),
    ("khong ai hieu", 0.78),
    ("minh vo dung", 0.79),
    ("cuoc song qua nang ne", 0.81),
    ("muon buong xuoi het", 0.8),
]

_ELEVATED = [
    ("qua tai", 0.55),
    ("qua suc", 0.52),
    ("rat cang thang", 0.54),
    ("cang thang cuc do", 0.56),
    ("hoang loan", 0.56),
    ("hoang so", 0.52),
    ("lo lang", 0.48),
    ("lo lang nhieu", 0.52),
    ("so hai", 0.5),
    ("buon ba", 0.46),
    ("tram cam", 0.5),
    ("stress", 0.45),
    ("rat met", 0.48),
    ("met moi", 0.44),
    ("cuc ky met", 0.5),
    ("khong ngu duoc", 0.46),
    ("mat ngu", 0.44),
    ("hoi hop", 0.42),
    ("bat on", 0.48),
    ("on ao trong dau", 0.5),
    ("rat buon", 0.46),
    ("cuc ky buon", 0.5),
    ("lo lang trien mien", 0.55),
    ("ap luc qua lon", 0.56),
    ("tam trang bat on", 0.54),
    ("cuc ky met moi", 0.53),
    ("buon ba lien tuc", 0.52),
    ("stress nang", 0.55),
]

_MODERATE = [
    ("rat", 0.32),
    ("qua muc", 0.34),
    ("so", 0.3),
    ("buon", 0.3),
    ("met", 0.28),
    ("kho chiu", 0.3),
    ("cang thang", 0.34),
    ("kho tho", 0.36),
    ("chan nan", 0.36),
    ("that vong", 0.38),
    ("trong rong", 0.36),
    ("ap luc", 0.34),
    ("met moi", 0.3),
    ("buon ba", 0.26),
]


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_intake_text(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = _strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s


def _unicode_critical_max(raw: str) -> float:
    if not raw or not raw.strip():
        return 0.0
    best = 0.0
    for rx, w in _UNICODE_CRITICAL:
        if rx.search(raw):
            best = max(best, w)
    return best


def _phrase_match(norm: str, padded: str, phrase: str) -> bool:
    pl = phrase.strip().lower()
    pl = pl.replace("đ", "d").replace("Đ", "d")
    pl = _strip_accents(pl)
    pl = re.sub(r"\s+", " ", pl).strip()
    if len(pl) < 4:
        return f" {pl} " in padded
    return pl in norm


def _build_weight_table() -> list[tuple[str, float]]:
    seen: dict[str, float] = {}
    for group in (_CRITICAL, _SEVERE, _ELEVATED, _MODERATE):
        for phrase, w in group:
            key = normalize_intake_text(phrase)
            if not key:
                continue
            seen[key] = max(seen.get(key, 0.0), w)
    return sorted(seen.items(), key=lambda x: (-len(x[0]), -x[1]))


_WEIGHTED = _build_weight_table()


def score_intake_keywords(text: str) -> tuple[float, list[str]]:
    """
    Trả về (điểm 0..1, danh sách cụm đã khớp sau chuẩn hóa / nhãn unicode).
    """
    raw = text or ""
    max_w = max(0.08, _unicode_critical_max(raw))

    norm = normalize_intake_text(raw)
    if not norm:
        return round(min(1.0, max_w), 3), []

    padded = f" {norm} "
    matched: list[str] = []
    if max_w >= 0.9:
        matched.append("[unicode:critical]")

    for phrase, w in _WEIGHTED:
        if _phrase_match(norm, padded, phrase):
            max_w = max(max_w, w)
            if phrase not in matched:
                matched.append(phrase)

    if len(matched) >= 2:
        max_w = min(1.0, max_w + 0.04 * min(len(matched) - 1, 4))

    return round(min(1.0, max_w), 3), matched


def intake_combined_text(overwhelmed: str, unsafe: str, need_help_now: str) -> str:
    return f"{overwhelmed} {unsafe} {need_help_now}"
