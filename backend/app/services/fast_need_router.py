from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from app.services.schemas.routing import RoutingDecision


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    no_accent = no_accent.replace("đ", "d")
    no_accent = re.sub(r"[“”‘’]", "'", no_accent)
    no_accent = re.sub(r"[^\w\s,.;:!?'\-/]", " ", no_accent)
    return re.sub(r"\s+", " ", no_accent).strip()


def _has_phrase(text: str, phrase: str) -> bool:
    phrase = _normalize(phrase)
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text))


def _has_any(text: str, phrases: Iterable[str]) -> bool:
    return any(_has_phrase(text, p) for p in phrases)


def _count_any(text: str, phrases: Iterable[str]) -> int:
    return sum(1 for p in phrases if _has_phrase(text, p))


def _word_count(text: str) -> int:
    return len([w for w in text.split(" ") if w])


# ---------------------------------------------------------------------------
# Hint lexicons
# Keep these plain, deterministic, and easy to audit.
# Do not put explicit self-harm handling here. SafetyGate owns SOS.
# ---------------------------------------------------------------------------

_GREETING_HINTS = (
    "chao",
    "xin chao",
    "hello",
    "hi",
    "hey",
    "yo",
    "alo",
    "helu",
    "hii",
    "heyy",
    "wassup",
    "sup",
    "e",
    "ee",
    "hu",
)

_THANKS_HINTS = (
    "cam on",
    "thanks",
    "thank you",
    "tks",
    "oke cam on",
    "ok cam on",
    "biet roi",
)

_ACK_ONLY_HINTS = (
    "uh",
    "um",
    "uhm",
    "uk",
    "ok",
    "oke",
    "dung roi",
    "that a",
    "vay a",
    "the a",
    "hmm",
    "da",
    "vang",
)

_EXPLICIT_ADVISOR_HINTS = (
    # Vietnamese
    "phan tich",
    "phan tich giup",
    "giai thich",
    "ly giai",
    "ke hoach",
    "lap ke hoach",
    "phuong an",
    "giai phap",
    "chien luoc",
    "huong xu ly",
    "cach xu ly",
    "lam gi tiep",
    "nen lam gi",
    "phai lam gi",
    "minh nen lam sao",
    "toi nen lam sao",
    "go tung nut",
    "go roi",
    "go van de",
    "tach su kien",
    "tach cam xuc",
    "tach y",
    "nhin ro hon",
    "cho minh loi khuyen",
    "dua loi khuyen",
    "tu van",
    "co nen",
    "nen hay khong",
    "quyet dinh",
    "lua chon",
    "uu nhuoc diem",
    "buoc tiep theo",
    "3 buoc",
    "ba buoc",
    "plan 3 buoc",

    # CBT / thinking pattern
    "suy dien",
    "suy nghi sai",
    "vong lap",
    "lap lai trong dau",
    "mac ket trong dau",
    "nghi qua nhieu",
    "tu duy",
    "pattern",
    "cognitive",
    "reframe",
    "reframing",

    # English
    "plan",
    "analyze",
    "analysis",
    "strategy",
    "advice",
    "what should i do",
    "what do i do",
    "next step",
    "break it down",
)

_LISTEN_ONLY_HINTS = (
    "chi can lang nghe",
    "chi muon ke",
    "chi muon noi ra",
    "khong can loi khuyen",
    "khong can tu van",
    "dung khuyen",
    "nghe thoi",
    "cho minh xa",
    "cho toi xa",
    "de minh ke",
    "de toi ke",
    "just listen",
    "just vent",
    "no advice",
    "i just want to vent",
)

_SERVICE_HINTS = (
    # Nutrition
    "an gi",
    "an uong",
    "bua sang",
    "bua trua",
    "bua toi",
    "bo bua",
    "khong an",
    "chan an",
    "them an",
    "an qua nhieu",
    "an vo toi va",
    "khong con thay vi",
    "vi giac",
    "dinh duong",
    "nutrition",
    "meal",
    "calo",
    "protein",
    "duong huyet",

    # Sleep
    "ngu",
    "mat ngu",
    "kho ngu",
    "ngu khong sau",
    "thuc khuya",
    "ngu ngay",
    "sleep",
    "insomnia",

    # Exercise / grounding
    "bai tap",
    "tho",
    "hit tho",
    "grounding",
    "thien",
    "meditation",
    "thu gian",
    "body scan",
    "co gian",
    "di bo",
)

_STUDY_WORK_HINTS = (
    "deadline",
    "han nop",
    "bai tap",
    "do an",
    "thi",
    "kiem tra",
    "hoc",
    "mon hoc",
    "truong",
    "lop",
    "cong viec",
    "du an",
    "sep",
    "dong nghiep",
    "intern",
    "thuc tap",
    "cv",
    "career",
    "job",
    "burnout",
)

_RELATIONSHIP_HINTS = (
    "ban be",
    "ban than",
    "nguoi yeu",
    "crush",
    "chia tay",
    "yeu xa",
    "bi bo roi",
    "bo roi",
    "ghost",
    "ghosting",
    "seen khong rep",
    "khong rep",
    "toxic",
    "ghen",
    "cai nhau",
    "moi quan he",
    "relationship",
)

_FAMILY_BOUNDARY_HINTS = (
    "gia dinh",
    "bo me",
    "me minh",
    "ba minh",
    "cha minh",
    "anh chi em",
    "ho hang",
    "ky vong",
    "ap luc gia dinh",
    "lam vua long",
    "lam hai long",
    "ranh gioi",
    "boundary",
    "khong duoc song cho minh",
    "bi kiem soat",
)

_EMOTIONAL_LOAD_HINTS = (
    "stress",
    "cang thang",
    "qua tai",
    "ngop",
    "nghet tho",
    "nghieng nga",
    "sap sup",
    "can kiet",
    "can suc",
    "kiet suc",
    "het nang luong",
    "het pin",
    "het suc",
    "met moi",
    "roi boi",
    "hon loan",
    "khong biet lam sao",
    "khong biet lam gi",
    "mac ket",
    "be tac",
    "bat luc",
    "vo vong",
    "tut mood",
    "down mood",
    "toang",
    "suy",
    "suy ngang",
    "lua chay",
    "khong on",
    "khong chiu noi",
    "khong tai noi",
    "chiu het noi",
)

_SELF_BLAME_HINTS = (
    "tu trach",
    "loi tai minh",
    "tai minh",
    "minh sai",
    "do minh",
    "minh te",
    "minh kem",
    "minh vo dung",
    "vo dung",
    "thua kem",
    "khong du tot",
    "chang ra gi",
    "phi pham",
    "lam hong moi thu",
    "minh lam hong",
    "minh la ganh nang",
    "ganh nang",
    "toi te",
    "dang xau ho",
    "nhuc",
    "co loi",
)

_CBT_PATTERN_HINTS = (
    "luc nao cung",
    "lan nao cung",
    "khong bao gio",
    "chac chan",
    "kieu gi cung",
    "ai cung",
    "khong ai",
    "tat ca moi nguoi",
    "minh biet la ho nghi",
    "ho chac nghi",
    "se that bai",
    "se bi ghep",
    "se bi bo",
    "se bi bo roi",
    "se hong het",
    "the la het",
    "het cuu",
    "khong co cach nao",
    "khong con cach nao",
    "overthinking",
    "suy dien",
    "tuong tuong ra",
    "nghi mai",
    "nghi qua nhieu",
)

_GROUNDING_HINTS = (
    "hoang loan",
    "panic",
    "panick",
    "run",
    "tim dap nhanh",
    "kho tho",
    "nghet tho",
    "mat binh tinh",
    "khong binh tinh",
    "dau dau",
    "cang co",
    "run tay",
    "choang",
    "te nguoi",
    "dang qua tai",
    "can binh tinh",
    "giup minh binh tinh",
)

_REASSURANCE_HINTS = (
    "co phai minh sai",
    "minh co sai khong",
    "co phai minh qua dang",
    "minh co qua nhay cam",
    "minh co te khong",
    "minh co ich ky",
    "minh co vo ly",
    "co phai minh kem",
    "co phai loi tai minh",
    "minh lam vay co dung khong",
    "minh co nen cam thay vay khong",
)

_DOMAIN_COMPLEX_HINTS = (
    *_STUDY_WORK_HINTS,
    *_RELATIONSHIP_HINTS,
    *_FAMILY_BOUNDARY_HINTS,
    *_EMOTIONAL_LOAD_HINTS,
    *_SELF_BLAME_HINTS,
    *_CBT_PATTERN_HINTS,
    *_GROUNDING_HINTS,
    *_REASSURANCE_HINTS,
    *_SERVICE_HINTS,
)


_SMALL_TALK_RE = re.compile(
    r"^(e+|ê+|hey+|hello+|hi+|hii+|xin chao|chao|chao zin|alo|yo+|hu+|"
    r"uhm+|um+|uk+|ok+|oke+|da|vang|cam on|thanks|tks|that a|vay a|the a|hmm+)[\W_]*$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Complexity features
# ---------------------------------------------------------------------------

def _looks_multi_issue(text: str) -> bool:
    markers = (
        "; ",
        ", ",
        ". ",
        " va ",
        " roi ",
        " nhung ",
        " ma ",
        " voi lai ",
        " ben canh do ",
        " dong thoi ",
        " trong khi ",
    )
    return sum(text.count(m) for m in markers) >= 3


def _domain_signal_count(text: str) -> int:
    groups = (
        _STUDY_WORK_HINTS,
        _RELATIONSHIP_HINTS,
        _FAMILY_BOUNDARY_HINTS,
        _EMOTIONAL_LOAD_HINTS,
        _SELF_BLAME_HINTS,
        _CBT_PATTERN_HINTS,
        _GROUNDING_HINTS,
        _REASSURANCE_HINTS,
        _SERVICE_HINTS,
    )
    return sum(1 for group in groups if _has_any(text, group))


def _route_reason_features(text: str) -> list[str]:
    reasons: list[str] = []

    if _has_any(text, _STUDY_WORK_HINTS):
        reasons.append("study_work_signal")
    if _has_any(text, _RELATIONSHIP_HINTS):
        reasons.append("relationship_signal")
    if _has_any(text, _FAMILY_BOUNDARY_HINTS):
        reasons.append("family_boundary_signal")
    if _has_any(text, _SELF_BLAME_HINTS):
        reasons.append("self_blame_signal")
    if _has_any(text, _CBT_PATTERN_HINTS):
        reasons.append("thinking_pattern_signal")
    if _has_any(text, _GROUNDING_HINTS):
        reasons.append("grounding_signal")
    if _has_any(text, _REASSURANCE_HINTS):
        reasons.append("reassurance_signal")
    if _has_any(text, _SERVICE_HINTS):
        reasons.append("service_signal")
    if _has_any(text, _EMOTIONAL_LOAD_HINTS):
        reasons.append("emotional_load_signal")

    return reasons


def _is_short_light_service_request(text: str) -> bool:
    if _word_count(text) > 45:
        return False
    if _looks_multi_issue(text):
        return False
    if _has_any(text, _SELF_BLAME_HINTS + _CBT_PATTERN_HINTS + _GROUNDING_HINTS):
        return False
    return True


def _recent_repeated_signal(
    recent_user_messages: list[str] | None,
    hints: Iterable[str],
    *,
    min_hits: int = 2,
    window: int = 3,
) -> bool:
    if not recent_user_messages:
        return False

    recent = [_normalize(m) for m in recent_user_messages[-window:]]
    return sum(1 for m in recent if _has_any(m, hints)) >= min_hits


def _recent_escalating_complexity(recent_user_messages: list[str] | None) -> bool:
    if not recent_user_messages or len(recent_user_messages) < 2:
        return False

    recent = [_normalize(m) for m in recent_user_messages[-3:]]
    scores = [
        _domain_signal_count(m)
        + int(_looks_multi_issue(m))
        + int(_word_count(m) >= 70)
        for m in recent
    ]
    return len(scores) >= 2 and scores[-1] >= 2 and scores[-1] >= scores[-2] + 1


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class FastNeedRouter:
    def route(
        self,
        *,
        user_message: str,
        recent_user_messages: list[str] | None = None,
    ) -> RoutingDecision:
        text = _normalize(user_message)

        if not text:
            return RoutingDecision(
                route_tier="fast",
                reason_codes=["empty_fast"],
                should_call_advisors=False,
            )

        word_count = _word_count(text)
        domain_count = _domain_signal_count(text)
        reason_features = _route_reason_features(text)

        # Ultra-light turns should not pay advisor latency.
        if _SMALL_TALK_RE.match(text):
            return RoutingDecision(
                route_tier="fast",
                reason_codes=["small_talk_fast"],
                should_call_advisors=False,
            )

        if _has_any(text, _THANKS_HINTS) and word_count <= 8:
            return RoutingDecision(
                route_tier="fast",
                reason_codes=["thanks_fast"],
                should_call_advisors=False,
            )

        if _has_any(text, _ACK_ONLY_HINTS) and word_count <= 5:
            return RoutingDecision(
                route_tier="fast",
                reason_codes=["ack_fast"],
                should_call_advisors=False,
            )

        if _has_any(text, _GREETING_HINTS) and word_count <= 8 and len(text) <= 50:
            return RoutingDecision(
                route_tier="fast",
                reason_codes=["greeting_fast"],
                should_call_advisors=False,
            )

        listen_only = _has_any(text, _LISTEN_ONLY_HINTS)

        # Listen-only means "do not over-advise", not necessarily "do not use advisors".
        # For long or emotionally dense venting, advisor guidance is still useful for
        # empathy/relevance/avoidance, but FriendAgent must not give a plan-heavy answer.
        if listen_only:
            if word_count >= 80 or domain_count >= 2 or _has_any(text, _SELF_BLAME_HINTS + _GROUNDING_HINTS):
                return RoutingDecision(
                    route_tier="advisor_assisted",
                    reason_codes=["listen_only_complex", *reason_features],
                    should_call_advisors=True,
                )

            return RoutingDecision(
                route_tier="fast",
                reason_codes=["listen_only_fast"],
                should_call_advisors=False,
            )

        # Service-only requests: nutrition/sleep/exercise/grounding can stay cheap when simple.
        service_hit = _has_any(text, _SERVICE_HINTS)
        if service_hit and _is_short_light_service_request(text):
            return RoutingDecision(
                route_tier="service_only",
                reason_codes=["service_domain", *reason_features],
                should_call_advisors=False,
            )

        # Explicit requests for analysis/advice/planning should call advisors.
        if _has_any(text, _EXPLICIT_ADVISOR_HINTS):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["explicit_analysis_request", *reason_features],
                should_call_advisors=True,
            )

        # Grounding signals are often short but should not be treated as small talk.
        # This is still not SOS handling; SafetyGate must run before this router.
        if _has_any(text, _GROUNDING_HINTS):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["grounding_support_request", *reason_features],
                should_call_advisors=True,
            )

        # Reassurance/self-blame/thinking-pattern cases benefit from CBT/reflection advisors.
        if _has_any(text, _REASSURANCE_HINTS) and (_has_any(text, _SELF_BLAME_HINTS) or word_count >= 35):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["reassurance_reflection_request", *reason_features],
                should_call_advisors=True,
            )

        if _count_any(text, _SELF_BLAME_HINTS) >= 1 and (_count_any(text, _CBT_PATTERN_HINTS) >= 1 or word_count >= 45):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["self_blame_cbt_signal", *reason_features],
                should_call_advisors=True,
            )

        # Multi-domain or long multi-issue messages should get advisor guidance.
        if domain_count >= 2:
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["multi_domain_signal", *reason_features],
                should_call_advisors=True,
            )

        if len(text) >= 420 or word_count >= 90 or _looks_multi_issue(text):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["complexity_signal", *reason_features],
                should_call_advisors=True,
            )

        # Recent context can upgrade a short current message.
        if _recent_repeated_signal(recent_user_messages, _SELF_BLAME_HINTS):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["repeated_self_blame"],
                should_call_advisors=True,
            )

        if _recent_repeated_signal(recent_user_messages, _CBT_PATTERN_HINTS):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["repeated_thinking_pattern"],
                should_call_advisors=True,
            )

        if _recent_repeated_signal(recent_user_messages, _EMOTIONAL_LOAD_HINTS):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["repeated_emotional_load"],
                should_call_advisors=True,
            )

        if _recent_escalating_complexity(recent_user_messages):
            return RoutingDecision(
                route_tier="advisor_assisted",
                reason_codes=["recent_complexity_escalation"],
                should_call_advisors=True,
            )

        return RoutingDecision(
            route_tier="fast",
            reason_codes=["default_fast", *reason_features],
            should_call_advisors=False,
        )
