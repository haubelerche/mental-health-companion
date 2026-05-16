from __future__ import annotations

import re
import unicodedata

from app.services.schemas.routing import AdvisorSelection, RoutingDecision

MAX_ADVISORS_PER_TURN = 2


def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).replace("đ", "d")
    return re.sub(r"\s+", " ", no_accent)


class AdvisorSelector:
    def select(
        self,
        *,
        routing: RoutingDecision,
        user_message: str,
        recent_user_messages: list[str] | None = None,
    ) -> AdvisorSelection:
        if not routing.should_call_advisors:
            return AdvisorSelection(advisor_ids=[], max_rounds=1, timeout_ms=1200)

        text = _normalize(user_message)
        picked: list[str] = []

        def add(advisor_id: str) -> None:
            if advisor_id not in picked:
                picked.append(advisor_id)

        # Priority order is intentional: concrete body/food signals first,
        # then self-blame/thought-pattern support, then planning. The cap keeps
        # latency predictable while still covering the strongest two needs.
        if any(
            k in text
            for k in (
                "tram cam",
                "roi loan",
                "chan doan",
                "benh gi",
                "bipolar",
                "luong cuc",
                "panic",
                "tu tu",
                "tu hai",
                "muon chet",
            )
        ):
            add("safety_policy_layer")
        if any(
            k in text
            for k in (
                "an gi",
                "an uong",
                "khong con thay vi",
                "vi giac",
                "dinh duong",
                "bo bua",
                "khong an",
                "nutrition",
                "meal",
                "bua",
                "ca phe",
            )
        ):
            add("nutrition_support_advisor")
        if any(
            k in text
            for k in (
                "loi tai minh",
                "tu trach",
                "do minh",
                "vo dung",
                "thua kem",
                "suy dien",
                "tach su kien",
                "chac ho",
                "khong bao gio",
                "luc nao cung",
            )
        ):
            add("cbt_pattern_advisor")
        if any(
            k in text
            for k in (
                "ke hoach",
                "phuong an",
                "phai lam gi",
                "nen lam gi",
                "lam gi tiep",
                "go tung nut",
                "deadline",
                "han nop",
                "chua lam gi",
                "plan",
            )
        ):
            add("strategy_resource_advisor")
        if any(
            k in text
            for k in (
                "cam thay",
                "buon",
                "met",
                "tuyet vong",
                "qua tai",
                "kiet suc",
                "can kiet",
                "can suc",
                "bo be gia dinh",
                "khong biet lam sao",
            )
        ):
            add("empathy_advisor")
        if len(text) > 320:
            add("reflection_advisor")
            add("relevance_naturalness_critic")

        if not picked:
            # Context-aware fallback: check recent messages for emotional signals
            recent_normalized = [_normalize(m) for m in (recent_user_messages or [])[-3:]]
            recent_combined = " ".join(recent_normalized)

            has_recent_self_blame = any(
                k in recent_combined
                for k in (
                    "tu trach", "loi tai minh", "tai minh", "vo dung",
                    "thua kem", "minh te", "minh kem", "lam hong",
                )
            )
            has_recent_emotional = any(
                k in recent_combined
                for k in (
                    "cam thay", "buon", "met", "tuyet vong", "qua tai",
                    "kiet suc", "khong on", "can kiet", "kho tho", "cang thang",
                )
            )

            if has_recent_self_blame:
                picked = ["cbt_pattern_advisor"]
            elif has_recent_emotional:
                picked = ["empathy_advisor"]
            else:
                picked = ["reflection_advisor"]

        return AdvisorSelection(
            advisor_ids=picked[:MAX_ADVISORS_PER_TURN],
            max_rounds=1,
            timeout_ms=1200,
        )
