from __future__ import annotations

import re
import unicodedata

from app.services.schemas.routing import RoutingDecision

_GREETING_HINTS = ("chao", "hello", "hi", "hey", "yo")
_EXPLICIT_ADVISOR_HINTS = (
    "phan tich",
    "ke hoach",
    "phuong an",
    "lam gi tiep",
    "nen lam gi",
    "phai lam gi",
    "go tung nut",
    "tach su kien",
    "suy dien",
    "plan",
    "analyze",
    "strategy",
)
_SERVICE_HINTS = (
    "an gi",
    "an uong",
    "khong an",
    "khong con thay vi",
    "vi giac",
    "dinh duong",
    "nutrition",
    "ngu",
    "sleep",
    "bai tap",
    "grounding",
)
_DOMAIN_COMPLEX_HINTS = (
    "deadline",
    "han nop",
    "bo bua",
    "khong an",
    "an uong",
    "khong con thay vi",
    "vi giac",
    "can kiet",
    "can suc",
    "kiet suc",
    "het minh",
    "het suc",
    "tu trach",
    "loi tai minh",
    "vo dung",
    "thua kem",
    "qua tai",
    "mac ket",
    "bat luc",
    "gia dinh",
    "bo be gia dinh",
    "ranh gioi",
    "lam vua long",
    "stress",
    "overthinking",
    "khong biet lam sao",
)
_LISTEN_ONLY_HINTS = (
    "chi can lang nghe",
    "chi muon ke",
    "khong can loi khuyen",
    "just listen",
    "just vent",
)
_SMALL_TALK_RE = re.compile(r"^(ok|uhm|hmm|vay a|the a|cam on|thanks|tks|dạ|da)\W*$", re.IGNORECASE)


def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")
    return re.sub(r"\s+", " ", no_accent)


def _looks_multi_issue(text: str) -> bool:
    markers = ("; ", ", ", " va ", " roi ", " nhung ")
    return sum(text.count(m) for m in markers) >= 3


def _domain_signal_count(text: str) -> int:
    return sum(1 for token in _DOMAIN_COMPLEX_HINTS if token in text)


def _has_token(text: str, token: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text))


class FastNeedRouter:
    def route(self, *, user_message: str, recent_user_messages: list[str] | None = None) -> RoutingDecision:
        text = _normalize(user_message)
        if not text:
            return RoutingDecision(route_tier="fast", reason_codes=["empty_fast"], should_call_advisors=False)

        if _SMALL_TALK_RE.match(text):
            return RoutingDecision(route_tier="fast", reason_codes=["small_talk_fast"], should_call_advisors=False)

        if any(k in text for k in _LISTEN_ONLY_HINTS):
            return RoutingDecision(route_tier="fast", reason_codes=["listen_only_fast"], should_call_advisors=False)

        if any(_has_token(text, k) for k in _GREETING_HINTS) and len(text) <= 40:
            return RoutingDecision(route_tier="fast", reason_codes=["greeting_fast"], should_call_advisors=False)

        service_hit = any(k in text for k in _SERVICE_HINTS)
        domain_count = _domain_signal_count(text)

        if service_hit:
            # keep service requests lightweight unless clearly complex
            if len(text) < 280 and not _looks_multi_issue(text) and domain_count < 2:
                return RoutingDecision(route_tier="service_only", reason_codes=["service_domain"], should_call_advisors=False)

        if any(k in text for k in _EXPLICIT_ADVISOR_HINTS):
            return RoutingDecision(route_tier="advisor_assisted", reason_codes=["explicit_analysis_request"], should_call_advisors=True)

        if domain_count >= 2:
            return RoutingDecision(route_tier="advisor_assisted", reason_codes=["multi_domain_signal"], should_call_advisors=True)

        if len(text) >= 420 or _looks_multi_issue(text):
            return RoutingDecision(route_tier="advisor_assisted", reason_codes=["complexity_signal"], should_call_advisors=True)

        if recent_user_messages:
            recent = [_normalize(m) for m in recent_user_messages[-3:]]
            if len(recent) >= 2 and all(("loi tai minh" in m or "tu trach" in m) for m in recent[-2:]):
                return RoutingDecision(route_tier="advisor_assisted", reason_codes=["repeated_self_blame"], should_call_advisors=True)

        return RoutingDecision(route_tier="fast", reason_codes=["default_fast"], should_call_advisors=False)
