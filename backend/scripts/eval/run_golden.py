from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from backend.scripts.eval.common import heuristic_answer, read_jsonl, redact_visible_text, stable_hash, write_jsonl
else:
    from .common import heuristic_answer, read_jsonl, redact_visible_text, stable_hash, write_jsonl


def _call_api(api_base: str, case: dict, token: str | None) -> dict:
    payload = json.dumps({"message": case["input"], "session_id": f"eval_{case['id']}"}).encode("utf-8")
    req = urllib.request.Request(
        api_base.rstrip("/") + "/v1/chat/message",
        data=payload,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    data = body.get("data") or {}
    return {
        "assistant_text": str(data.get("assistant_text") or data.get("reply") or ""),
        "route_tier": str(data.get("route_tier") or ""),
        "used_advisor_ids": list(data.get("used_advisor_ids") or []),
        "trace_id": data.get("trace_id"),
        "latency_trace": data.get("latency_trace") or {},
    }


def run(dataset: Path, out: Path, api_base: str | None, token: str | None) -> list[dict]:
    rows = []
    for case in read_jsonl(dataset):
        if api_base:
            observed = _call_api(api_base, case, token)
        else:
            observed = {
                "assistant_text": heuristic_answer(case),
                "route_tier": case.get("route_expected"),
                "used_advisor_ids": list(case.get("advisor_expected") or []),
                "trace_id": f"offline-{case['id']}",
                "latency_trace": {"total_backend_ms": 100},
            }
        rows.append(
            {
                "case_id": case["id"],
                "category": case["category"],
                "difficulty": case["difficulty"],
                "input_hash": stable_hash(case.get("input", "")),
                "expected_behavior": case.get("expected_behavior", []),
                "route_expected": case.get("route_expected"),
                "route_actual": observed["route_tier"],
                "advisor_expected": case.get("advisor_expected", []),
                "advisor_actual": observed["used_advisor_ids"],
                "contexts_expected": case.get("contexts_expected", []),
                "metrics_applicable": case.get("metrics_applicable", []),
                "assistant_text_redacted": redact_visible_text(observed["assistant_text"]),
                "trace_id": observed.get("trace_id"),
                "latency_trace": observed.get("latency_trace", {}),
            }
        )
    write_jsonl(out, rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--api-base")
    parser.add_argument("--token")
    args = parser.parse_args()
    rows = run(Path(args.dataset), Path(args.out), args.api_base, args.token)
    print(json.dumps({"outputs": len(rows), "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
