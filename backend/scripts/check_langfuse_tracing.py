from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.langfuse_tracing import ChatTurnTracer


PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


def _mask_state(value: str | None) -> str:
    return "set" if str(value or "").strip() else "missing"


def _proxy_summary() -> str:
    parts: list[str] = []
    for key in PROXY_KEYS:
        value = os.getenv(key)
        if value:
            parts.append(f"{key}={value}")
    return ", ".join(parts) if parts else "none"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Langfuse SDK/config and optionally send a diagnostic trace.")
    parser.add_argument("--send-test", action="store_true", help="Send a synthetic non-sensitive trace to Langfuse.")
    args = parser.parse_args()

    settings = get_settings()
    spec = importlib.util.find_spec("langfuse")
    print(f"langfuse_installed={bool(spec)}")
    if spec:
        try:
            print(f"langfuse_version={importlib.metadata.version('langfuse')}")
        except importlib.metadata.PackageNotFoundError:
            print("langfuse_version=unknown")
    print(f"public_key={_mask_state(settings.langfuse_public_key)}")
    print(f"secret_key={_mask_state(settings.langfuse_secret_key)}")
    print(f"host={settings.langfuse_host}")
    print(f"proxy_env={_proxy_summary()}")

    if not args.send_test:
        return 0

    seed = f"manual-langfuse-diagnostic-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    tracer = ChatTurnTracer(
        correlation_id=seed,
        user_id="diagnostic-user",
        session_id="diagnostic-session",
        input_meta={"endpoint": "diagnostic", "route_tier": "fast", "persona_id": "dung_luong"},
    )
    tracer.routing_decision(
        route_tier="fast",
        reason_codes=["diagnostic_probe"],
        planned_advisor_ids=[],
        selected_advisor_ids=[],
        interaction_need="diagnostic",
        persona_id="dung_luong",
    )
    tracer.worker_enqueue({"memory_extraction": "queued"})
    tracer.update_output(
        "Langfuse diagnostic trace from local backend.",
        metadata={"route_tier": "fast", "persona_id": "dung_luong"},
    )
    tracer.flush()
    print(f"sent_trace_seed={seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
