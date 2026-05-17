"""Build and render AI security eval reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CaseResult:
    case_id: str
    surface: str
    attack_class: str
    severity: str
    passed: bool
    reason: str
    redacted_response_excerpt: str = ""
    status_code: int = 0
    latency_ms: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class SecurityReport:
    results: list[CaseResult] = field(default_factory=list)
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mode: str = "offline"
    base_url: str = ""

    # ------------------------------------------------------------------ counts

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed and not r.skipped)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def p0_failures(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.skipped and r.severity == "P0")

    @property
    def p1_failures(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.skipped and r.severity == "P1")

    @property
    def p2_failures(self) -> int:
        return sum(1 for r in self.results if not r.passed and not r.skipped and r.severity == "P2")

    @property
    def verdict(self) -> str:
        if self.p0_failures > 0:
            return "FAIL"
        if self.p1_failures > 0:
            return "FAIL"
        if self.p2_failures > 0:
            return "CONDITIONAL_PASS"
        if self.failed > 0:
            return "CONDITIONAL_PASS"
        return "PASS"

    # ------------------------------------------------------------------ by-group

    def by_attack_class(self) -> dict[str, dict[str, int]]:
        groups: dict[str, dict[str, int]] = {}
        for r in self.results:
            g = groups.setdefault(r.attack_class, {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
            g["total"] += 1
            if r.skipped:
                g["skipped"] += 1
            elif r.passed:
                g["passed"] += 1
            else:
                g["failed"] += 1
        return groups

    def by_surface(self) -> dict[str, dict[str, int]]:
        groups: dict[str, dict[str, int]] = {}
        for r in self.results:
            g = groups.setdefault(r.surface, {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
            g["total"] += 1
            if r.skipped:
                g["skipped"] += 1
            elif r.passed:
                g["passed"] += 1
            else:
                g["failed"] += 1
        return groups

    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if not r.passed and not r.skipped]

    # ------------------------------------------------------------------ export

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_at": self.run_at,
            "mode": self.mode,
            "base_url": self.base_url,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "p0_failures": self.p0_failures,
                "p1_failures": self.p1_failures,
                "p2_failures": self.p2_failures,
                "verdict": self.verdict,
            },
            "by_attack_class": self.by_attack_class(),
            "by_surface": self.by_surface(),
            "failures": [
                {
                    "id": r.case_id,
                    "surface": r.surface,
                    "attack_class": r.attack_class,
                    "severity": r.severity,
                    "reason": r.reason,
                    "redacted_response_excerpt": r.redacted_response_excerpt,
                    "status_code": r.status_code,
                }
                for r in self.failures()
            ],
        }

    def save_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def save_markdown(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render_markdown(), encoding="utf-8")

    def _render_markdown(self) -> str:
        verdict_emoji = {"PASS": "✅", "CONDITIONAL_PASS": "⚠️", "FAIL": "❌"}.get(self.verdict, "?")
        lines = [
            "# AI Security Test Report",
            "",
            f"**Run at:** {self.run_at}  ",
            f"**Mode:** `{self.mode}`  ",
            f"**Base URL:** `{self.base_url or 'offline'}`",
            "",
            "## Executive Summary",
            "",
            f"| Field | Value |",
            f"|---|---|",
            f"| Verdict | {verdict_emoji} **{self.verdict}** |",
            f"| Total cases | {self.total} |",
            f"| Passed | {self.passed} |",
            f"| Failed | {self.failed} |",
            f"| Skipped | {self.skipped} |",
            f"| P0 failures | {self.p0_failures} |",
            f"| P1 failures | {self.p1_failures} |",
            f"| P2 failures | {self.p2_failures} |",
            "",
        ]

        # Attack class table
        lines += ["## Coverage by Attack Class", "", "| Attack Class | Total | Passed | Failed | Skipped |", "|---|---:|---:|---:|---:|"]
        for cls, counts in sorted(self.by_attack_class().items()):
            lines.append(f"| {cls} | {counts['total']} | {counts['passed']} | {counts['failed']} | {counts['skipped']} |")
        lines.append("")

        # Surface table
        lines += ["## Coverage by Surface", "", "| Surface | Total | Passed | Failed | Skipped |", "|---|---:|---:|---:|---:|"]
        for surf, counts in sorted(self.by_surface().items()):
            lines.append(f"| {surf} | {counts['total']} | {counts['passed']} | {counts['failed']} | {counts['skipped']} |")
        lines.append("")

        # Failures
        failures = self.failures()
        if failures:
            lines += ["## Failed Cases", "", "| Case ID | Severity | Surface | Attack Class | Reason |", "|---|---|---|---|---|"]
            for r in failures:
                lines.append(f"| {r.case_id} | {r.severity} | {r.surface} | {r.attack_class} | {r.reason[:80]} |")
            lines.append("")
        else:
            lines += ["## Failed Cases", "", "_No failures._", ""]

        lines += [
            "## Release Gate",
            "",
            f"> Verdict: **{self.verdict}**",
            "",
            "- P0 failure → block release" if self.p0_failures else "- No P0 failures ✓",
            "- P1 failure → block release" if self.p1_failures else "- No P1 failures ✓",
        ]

        return "\n".join(lines) + "\n"
