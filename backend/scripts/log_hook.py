"""AI activity hook — called automatically by Claude Code on every tool use.

Reads hook event data from stdin (JSON), writes a compact entry to
.ai-log/session.jsonl using the same schema as log_manual.py.

Environment variables set by the hook command:
  AI_TOOL_NAME   — which AI tool fired this hook (e.g. "claude")
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""


def _read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _build_entry(hook_data: dict) -> dict:
    now = datetime.now(UTC)
    entry_id = f"hook-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{uuid4().hex[:8]}"

    tool_name = os.environ.get("AI_TOOL_NAME", "claude")
    hook_event = hook_data.get("hook_event_name", "unknown")
    tool_input = hook_data.get("tool_input", {})

    # Build a compact prompt summary from available hook fields
    if hook_event == "UserPromptSubmit":
        prompt_summary = (hook_data.get("prompt") or "")[:1000]
    elif hook_event == "PostToolUse":
        called = hook_data.get("tool_name", "")
        prompt_summary = f"[{called}] {json.dumps(tool_input, ensure_ascii=False)[:300]}"
    else:
        prompt_summary = hook_event

    return {
        "entry_id": entry_id,
        "ts": now.isoformat(timespec="seconds") + "Z",
        "tool": tool_name,
        "model": hook_data.get("model", ""),
        "hook_event": hook_event,
        "prompt": prompt_summary,
        "response_summary": "",
        "repo": _git("config", "--get", "remote.origin.url"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": _git("rev-parse", "HEAD"),
        "student": os.environ.get("USERNAME", os.environ.get("USER", "")),
    }


def main() -> None:
    hook_data = _read_stdin()
    entry = _build_entry(hook_data)

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "session.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
