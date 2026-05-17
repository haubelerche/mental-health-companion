"""Load and validate AI security test cases from JSONL dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

_DEFAULT_DATASET = Path(__file__).parent / "ai_security_attackset_v1.jsonl"

REQUIRED_FIELDS = {
    "id", "surface", "attack_class", "severity",
    "method", "endpoint", "must_pass", "must_not_contain",
    "expected_status",
}

VALID_SEVERITIES = {"P0", "P1", "P2"}
VALID_SURFACES = {
    "chat", "screening", "mood", "nutrition", "letter",
    "memory", "persona", "reward", "dashboard", "tts",
    "auth", "safety", "rag",
}
VALID_ATTACK_CLASSES = {
    "direct_prompt_injection", "indirect_prompt_injection", "memory_poisoning",
    "data_exfiltration", "safety_bypass", "clinical_boundary", "persona_override",
    "reward_abuse", "frontend_tampering", "idor_bola", "input_validation",
    "log_leakage", "tts_abuse", "rag_injection",
}


def load_cases(
    dataset_path: Path = _DEFAULT_DATASET,
    *,
    surfaces: list[str] | None = None,
    attack_classes: list[str] | None = None,
    severities: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load and filter security cases from JSONL file."""
    cases: list[dict[str, Any]] = []
    with open(dataset_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {lineno}: invalid JSON — {exc}") from exc
            _validate(case, lineno)
            if surfaces and case["surface"] not in surfaces:
                continue
            if attack_classes and case["attack_class"] not in attack_classes:
                continue
            if severities and case["severity"] not in severities:
                continue
            cases.append(case)
    return cases


def _validate(case: dict[str, Any], lineno: int) -> None:
    missing = REQUIRED_FIELDS - set(case.keys())
    if missing:
        raise ValueError(f"Line {lineno} ({case.get('id', '?')}): missing fields {missing}")
    if case["severity"] not in VALID_SEVERITIES:
        raise ValueError(f"Line {lineno}: invalid severity {case['severity']!r}")


def iter_by_class(cases: list[dict[str, Any]]) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Yield (attack_class, [cases]) sorted groups."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in cases:
        groups.setdefault(c["attack_class"], []).append(c)
    for cls in sorted(groups):
        yield cls, groups[cls]


def iter_by_surface(cases: list[dict[str, Any]]) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in cases:
        groups.setdefault(c["surface"], []).append(c)
    for surf in sorted(groups):
        yield surf, groups[surf]
