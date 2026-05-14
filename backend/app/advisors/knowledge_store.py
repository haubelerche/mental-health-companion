from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable


ADVISOR_DATA_DOMAINS: dict[str, str] = {
    "empathy_advisor": "empathy",
    "cbt_pattern_advisor": "cbtpattern",
    "reflection_advisor": "reflection",
    "strategy_resource_advisor": "strategy",
    "nutrition_support_advisor": "nutrition",
    "relevance_naturalness_critic": "relevance",
    "safety_policy_layer": "safety",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", no_accent.replace("đ", "d"))


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _iter_tolerant_json_objects(text: str) -> Iterable[dict[str, Any]]:
    """Read strict JSON arrays and legacy comma-prefixed JSONL fragments."""

    text = text.replace('}\n\n    "rubric_id"', '},\n    "rubric_id"')
    decoder = json.JSONDecoder()
    idx = 0
    size = len(text)
    while idx < size:
        while idx < size and text[idx] in " \t\r\n,[]":
            idx += 1
        if idx >= size:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        idx = end
        if isinstance(obj, dict):
            yield obj
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    yield item


@dataclass(frozen=True)
class AdvisorKnowledgeRecord:
    item_id: str
    advisor_scope: tuple[str, ...]
    locale: str
    summary: str
    advisor_advice_to_friend: tuple[str, ...]
    suggested_response_moves: tuple[str, ...]
    forbidden_moves: tuple[str, ...]
    trigger_keywords: tuple[str, ...]
    tags: tuple[str, ...]
    raw: dict[str, Any]

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "AdvisorKnowledgeRecord | None":
        item_id = str(raw.get("item_id") or "").strip()
        scope = tuple(_as_str_list(raw.get("advisor_scope")))
        locale = str(raw.get("locale") or "").strip()
        summary = str(raw.get("summary") or raw.get("content") or "").strip()
        advice = tuple(_as_str_list(raw.get("advisor_advice_to_friend") or raw.get("critic_advice_to_friend")))
        quality = raw.get("quality_flags") if isinstance(raw.get("quality_flags"), dict) else {}
        if not item_id or not scope or locale != "vi":
            return None
        if not summary and not advice:
            return None
        if quality.get("no_final_text") is not True:
            return None
        if raw.get("display_allowed") is True:
            return None
        return cls(
            item_id=item_id,
            advisor_scope=scope,
            locale=locale,
            summary=summary,
            advisor_advice_to_friend=advice,
            suggested_response_moves=tuple(_as_str_list(raw.get("suggested_response_moves"))),
            forbidden_moves=tuple(_as_str_list(raw.get("forbidden_moves") or raw.get("forbidden_clinical_wording"))),
            trigger_keywords=tuple(_as_str_list(raw.get("trigger_keywords") or raw.get("user_signal_examples"))),
            tags=tuple(_as_str_list(raw.get("tags") or raw.get("target_state"))),
            raw=raw,
        )

    def advice_lines(self, limit: int = 2) -> list[str]:
        lines = list(self.advisor_advice_to_friend)
        if not lines and self.summary:
            lines = [self.summary]
        return lines[:limit]

    def move_lines(self, limit: int = 1) -> list[str]:
        lines = [
            line
            for line in self.suggested_response_moves
            if not (re.fullmatch(r"[a-z0-9_]+", line.strip()) and "_" in line)
        ]
        hint = self.raw.get("safe_wording_hint") or self.raw.get("friend_usage_rule") or self.raw.get("soft_interpretation")
        if isinstance(hint, str) and hint.strip():
            lines = [hint.strip()] + lines
        if not lines and self.summary:
            lines = [self.summary]
        return lines[:limit]


class AdvisorKnowledgeStore:
    def __init__(self, *, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or (_repo_root() / "data" / "data-advisors")
        self._cache: dict[str, list[AdvisorKnowledgeRecord]] = {}

    def load_for_advisor(self, advisor_id: str) -> list[AdvisorKnowledgeRecord]:
        if advisor_id in self._cache:
            return list(self._cache[advisor_id])
        domain = ADVISOR_DATA_DOMAINS.get(advisor_id)
        if not domain:
            self._cache[advisor_id] = []
            return []
        records: list[AdvisorKnowledgeRecord] = []
        for path in sorted((self._base_dir / domain).glob("*.jsonl")):
            text = path.read_text(encoding="utf-8")
            for raw in _iter_tolerant_json_objects(text):
                record = AdvisorKnowledgeRecord.from_raw(raw)
                if record and advisor_id in record.advisor_scope:
                    records.append(record)
        self._cache[advisor_id] = records
        return list(records)

    def retrieve(self, *, advisor_id: str, user_message: str, context_summary: str = "", limit: int = 2) -> list[AdvisorKnowledgeRecord]:
        query = _normalize(f"{user_message} {context_summary}")
        records = self.load_for_advisor(advisor_id)
        if not records:
            return []

        def score(record: AdvisorKnowledgeRecord) -> tuple[int, str]:
            points = 0
            for keyword in record.trigger_keywords:
                normalized_keyword = _normalize(keyword)
                if normalized_keyword and normalized_keyword in query:
                    points += 6
            for tag in record.tags:
                normalized_tag = _normalize(tag).replace("_", " ")
                if normalized_tag and normalized_tag in query:
                    points += 3
            searchable = _normalize(
                " ".join(
                    [
                        str(record.raw.get("title") or ""),
                        record.summary,
                        " ".join(record.advice_lines(limit=3)),
                    ]
                )
            )
            for token in set(re.findall(r"[a-z0-9]{3,}", query)):
                if token in searchable:
                    points += 1
            return (-points, record.item_id)

        ranked = sorted(records, key=score)
        matched = [record for record in ranked if score(record)[0] < 0]
        return (matched or ranked)[: max(1, limit)]
