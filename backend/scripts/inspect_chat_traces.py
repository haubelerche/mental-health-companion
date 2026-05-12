from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_TRACE_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "observability" / "latest_traces.jsonl"


def _load_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            out.append(item)
    return out


def _span_ms(trace: dict[str, Any], name: str) -> int:
    spans = trace.get("spans")
    if not isinstance(spans, list):
        return 0
    return sum(int(span.get("duration_ms") or 0) for span in spans if isinstance(span, dict) and span.get("name") == name)


def _metric_value(trace: dict[str, Any], name: str) -> float | None:
    metrics = trace.get("metrics")
    if not isinstance(metrics, list):
        return None
    for metric in reversed(metrics):
        if isinstance(metric, dict) and metric.get("name") == name:
            value = metric.get("value")
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _events(trace: dict[str, Any], name: str) -> list[dict[str, Any]]:
    events = trace.get("events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict) and event.get("name") == name]


def _event_metadata(trace: dict[str, Any], name: str) -> dict[str, Any]:
    matches = _events(trace, name)
    if not matches:
        return {}
    metadata = matches[-1].get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _advisor_spans(trace: dict[str, Any]) -> list[str]:
    spans = trace.get("spans")
    if not isinstance(spans, list):
        return []
    names: list[str] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        name = str(span.get("name") or "")
        if name.startswith("advisor.") and name.endswith(".run"):
            advisor_id = name.removeprefix("advisor.").removesuffix(".run")
            if advisor_id not in names:
                names.append(advisor_id)
    return names


def _format_row(trace: dict[str, Any]) -> str:
    metadata = trace.get("metadata") if isinstance(trace.get("metadata"), dict) else {}
    quality = trace.get("quality_tags") if isinstance(trace.get("quality_tags"), dict) else {}
    routing = _event_metadata(trace, "dynamic_routing.decision")
    workers = _event_metadata(trace, "chat_turn_completed").get("worker_outcomes")
    latency = _metric_value(trace, "chat_latency_ms")
    latency_text = f"{int(latency)}ms" if latency is not None else f"{int(trace.get('duration_ms') or 0)}ms"
    advisors = _advisor_spans(trace)
    if not advisors and isinstance(routing.get("planned_advisor_ids"), list):
        advisors = [str(item) for item in routing.get("planned_advisor_ids") or []]
    advisor_text = ",".join(advisors) if advisors else "-"
    worker_text = "-"
    if isinstance(workers, dict):
        worker_text = ",".join(f"{k}:{v}" for k, v in sorted(workers.items()))
    reason_codes = routing.get("reason_codes")
    reason_text = ",".join(str(item) for item in reason_codes[:4]) if isinstance(reason_codes, list) else "-"
    return (
        f"{str(trace.get('trace_id') or '')[:8]} "
        f"route={metadata.get('route_tier', '-')} "
        f"reasons={reason_text} "
        f"persona={metadata.get('persona_id', '-')} "
        f"advisors={advisor_text} "
        f"workers={worker_text} "
        f"validator={quality.get('validator_verdict', '-')} "
        f"latency={latency_text} "
        f"safety={_span_ms(trace, 'safety.pre_check')}ms "
        f"context={_span_ms(trace, 'context.load')}ms "
        f"friend={_span_ms(trace, 'friend_node.respond')}ms"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect redacted Serene chat traces.")
    parser.add_argument("--path", type=Path, default=DEFAULT_TRACE_PATH)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    traces = _load_tail(args.path, max(1, args.limit))
    if not traces:
        print(f"No traces found at {args.path}")
        return 0
    for trace in traces:
        print(_format_row(trace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
