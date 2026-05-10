from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


TOOLS = ["chatgpt", "claude", "gemini-web", "copilot", "cursor", "other"]


def git(*args: str) -> str:
    try:
        out = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return ""


def make_entry(tool: str, prompt: str, model: str = "", response_summary: str = "") -> dict[str, str]:
    now = datetime.now(UTC)
    entry_id = f"manual-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{uuid4().hex[:8]}"
    return {
        "entry_id": entry_id,
        "ts": now.isoformat(timespec="seconds") + "Z",
        "tool": (tool or "").strip(),
        "model": (model or "").strip(),
        "prompt": (prompt or "")[:1000],
        "response_summary": (response_summary or "")[:500],
        "repo": git("config", "--get", "remote.origin.url"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git("rev-parse", "HEAD"),
        "student": os.environ.get("USER", ""),
    }


def save_entry(entry: dict[str, object]) -> Path:
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "session.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def _prompt_interactive() -> tuple[str, str, str]:
    for i, t in enumerate(TOOLS, start=1):
        print(f"{i}. {t}")
    pick = input("Tool: ").strip()
    try:
        idx = int(pick) - 1
        tool = TOOLS[idx] if 0 <= idx < len(TOOLS) else pick
    except ValueError:
        tool = pick
    prompt = input("Prompt: ").strip()
    if not prompt:
        raise SystemExit(2)
    model = input("Model (optional): ").strip()
    return tool, prompt, model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool")
    parser.add_argument("--prompt")
    parser.add_argument("--model", default="")
    parser.add_argument("--response-summary", default="")
    args = parser.parse_args()

    if args.tool and not args.prompt:
        parser.error("--tool requires --prompt")
    if args.prompt and not args.tool:
        parser.error("--prompt requires --tool")

    if args.tool and args.prompt:
        tool, prompt, model = args.tool, args.prompt, args.model
    else:
        tool, prompt, model = _prompt_interactive()

    entry = make_entry(tool, prompt, model=model, response_summary=args.response_summary)
    save_entry(entry)


if __name__ == "__main__":
    main()
