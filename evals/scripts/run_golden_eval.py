"""Run Serene LLM-as-Judge eval against evals/golden/serene_golden_v0.jsonl.

Usage:
    python evals/scripts/run_golden_eval.py --model gpt-4o-mini --limit 20
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

GOLDEN_PATH = Path(__file__).parent.parent / "golden" / "serene_golden_v0.jsonl"
RUBRIC_PATH = Path(__file__).parent.parent / "rubrics" / "serene_judge_rubric_v1.md"
REPORT_DIR = Path(__file__).parent.parent / "reports"

RUBRIC_PROMPT_TEMPLATE = """\
You are a clinical psychologist evaluating a mental health chatbot response.

USER MESSAGE:
{user_message}

SERENE RESPONSE:
{assistant_response}

RECENT CONTEXT (if any):
{context}

Score the response using this rubric, then return ONLY valid JSON with these keys:
empathy (0-3), cognitive_distortion_id (0-3), reflection (0-3),
strategy (0-3), encouragement (0-3), relevance (0-3), total (sum), reasoning (string).
"""

DIMENSIONS = ["empathy", "cognitive_distortion_id", "reflection", "strategy", "encouragement", "relevance"]
MIN_PASS_AVERAGE = 12.0


def _load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        print(f"ERROR: Golden set not found at {GOLDEN_PATH}", file=sys.stderr)
        sys.exit(1)
    return [json.loads(line) for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _score_case(case: dict, model: str, client) -> dict | None:
    user_message = case.get("user_message", "")
    assistant_response = case.get("assistant_response", "")
    context = case.get("context", "")

    if not user_message or not assistant_response:
        return None

    prompt = RUBRIC_PROMPT_TEMPLATE.format(
        user_message=user_message,
        assistant_response=assistant_response,
        context=context or "(none)",
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content or ""
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        scores = json.loads(raw)
        scores["case_id"] = case.get("id", "unknown")
        scores["category"] = case.get("category", "unknown")
        return scores
    except Exception as exc:
        print(f"  WARN: score failed for {case.get('id')}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Serene judge eval")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model for judge")
    parser.add_argument("--limit", type=int, default=0, help="Max cases to evaluate (0 = all)")
    parser.add_argument("--output", default="", help="Output file path (default: auto)")
    args = parser.parse_args()

    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)
    cases = _load_golden()
    if args.limit > 0:
        cases = cases[: args.limit]

    print(f"Evaluating {len(cases)} golden cases with {args.model}...")
    results: list[dict] = []

    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.get('id', '?')}", end=" ... ", flush=True)
        scores = _score_case(case, args.model, client)
        if scores:
            results.append(scores)
            print(f"total={scores.get('total', '?')}")
        else:
            print("SKIPPED")
        time.sleep(0.3)

    if not results:
        print("No results collected. Exiting.", file=sys.stderr)
        sys.exit(1)

    totals = [r.get("total", 0) for r in results]
    average = sum(totals) / len(totals)

    print(f"\n=== Results ===")
    print(f"Cases scored: {len(results)}")
    print(f"Average total: {average:.1f} / 18")
    print(f"Min pass threshold: {MIN_PASS_AVERAGE}")
    print(f"VERDICT: {'PASS' if average >= MIN_PASS_AVERAGE else 'FAIL'}")

    for dim in DIMENSIONS:
        dim_scores = [r.get(dim, 0) for r in results]
        print(f"  {dim}: avg {sum(dim_scores)/len(dim_scores):.2f}/3")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import date
    out_path = Path(args.output) if args.output else REPORT_DIR / f"{date.today()}_judge_eval.json"
    out_path.write_text(
        json.dumps(
            {"summary": {"cases": len(results), "average": average, "pass": average >= MIN_PASS_AVERAGE}, "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nReport saved: {out_path}")
    sys.exit(0 if average >= MIN_PASS_AVERAGE else 1)


if __name__ == "__main__":
    main()
