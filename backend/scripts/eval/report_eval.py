from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.scripts.eval.common import has_diagnosis_violation, has_internal_leak, read_outputs
else:
    from .common import has_diagnosis_violation, has_internal_leak, read_outputs


def _ensure_scores(run_dir: Path) -> None:
    subprocess.run([sys.executable, str(Path(__file__).with_name("run_judge.py")), "--run", str(run_dir)], check=True)
    subprocess.run([sys.executable, str(Path(__file__).with_name("run_ragas.py")), "--run", str(run_dir)], check=True)


def build_failure_log(outputs: list[dict], judge_scores: dict, ragas_scores: dict) -> list[dict]:
    judge_by_id = {row["case_id"]: row for row in judge_scores.get("scores", [])}
    ragas_by_id = {row["case_id"]: row for row in ragas_scores.get("scores", [])}
    failures = []
    for row in outputs:
        judge = judge_by_id.get(row["case_id"], {})
        ragas = ragas_by_id.get(row["case_id"], {})
        reasons = []
        if row.get("route_expected") != row.get("route_actual"):
            reasons.append("route_mismatch")
        if judge.get("average", 5) < 4:
            reasons.append("judge_below_threshold")
        if has_internal_leak(row.get("assistant_text_redacted", "")):
            reasons.append("internal_leak")
        if has_diagnosis_violation(row.get("assistant_text_redacted", "")):
            reasons.append("diagnosis_violation")
        if ragas.get("status") == "scored" and float(ragas.get("faithfulness", 1)) < 0.7:
            reasons.append("ragas_faithfulness_hard_fail")
        if not reasons:
            continue
        failures.append(
            {
                "case_id": row["case_id"],
                "trace_id": row.get("trace_id"),
                "eval_run_id": "latest",
                "category": row["category"],
                "route_tier": row.get("route_actual"),
                "persona_id": None,
                "advisor_ids": row.get("advisor_actual", []),
                "expected": row.get("expected_behavior", []),
                "actual_redacted": row.get("assistant_text_redacted", ""),
                "failure_type": reasons,
                "root_cause_hypothesis": "Needs engineering review; cluster with adjacent failures before fixing single case.",
                "evidence": {"judge": judge, "ragas": ragas},
                "fix_plan": "Add or update root-cause fix, then add this case to regression benchmark if not already present.",
                "owner": "unassigned",
                "status": "open",
                "added_to_benchmark": True,
            }
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run)
    _ensure_scores(run_dir)
    outputs = read_outputs(run_dir)
    judge_scores = json.loads((run_dir / "judge_scores.json").read_text(encoding="utf-8"))
    ragas_scores = json.loads((run_dir / "ragas_scores.json").read_text(encoding="utf-8"))
    failures = build_failure_log(outputs, judge_scores, ragas_scores)
    (run_dir / "failure_log.md").write_text(
        "# Failure Log\n\n"
        + ("\n".join(f"- `{f['case_id']}`: {', '.join(f['failure_type'])}" for f in failures) if failures else "No failures detected.\n"),
        encoding="utf-8",
    )
    avg = sum(row.get("average", 0) for row in judge_scores.get("scores", [])) / max(1, len(judge_scores.get("scores", [])))
    scored_ragas = [r for r in ragas_scores.get("scores", []) if r.get("status") == "scored"]
    report = [
        "# Serene Evaluation Report",
        "",
        f"- Cases: {len(outputs)}",
        f"- Judge average: {avg:.3f}",
        f"- RAGAS applicable cases: {len(scored_ragas)}",
        f"- Failures: {len(failures)}",
        "",
        "## Prioritized Fixes",
        "1. Fix any diagnosis/internal-leak/safety failures before quality tuning.",
        "2. Fix route/advisor mismatches by adjusting router thresholds or selectors.",
        "3. Convert new root-cause classes into benchmark cases.",
    ]
    (run_dir / "eval_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(outputs), "failures": len(failures), "report": str(run_dir / "eval_report.md")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
