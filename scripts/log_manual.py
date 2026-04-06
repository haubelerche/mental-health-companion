#!/usr/bin/env python3
"""
Manual AI log entry — for tools without automatic hooks (ChatGPT, Gemini Web, etc.)

Usage:
    python scripts/log_manual.py                                       # interactive
    python scripts/log_manual.py --tool chatgpt --prompt "..." --model "gpt-5.4"
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

VN_TZ = timezone(timedelta(hours=7))

KNOWN_TOOLS = ["chatgpt", "gemini-web", "perplexity", "claude-web", "copilot-web", "other"]


def git(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def make_entry(tool, prompt, model="", response_summary=""):
    ts = datetime.now(VN_TZ)
    return {
        "ts": ts.isoformat(),
        "tool": tool,
        "event": "ManualLog",
        "entry_id": f"manual-{ts.strftime('%Y%m%d-%H%M%S')}",
        "model": model,
        "repo": git("git remote get-url origin").split("/")[-1].replace(".git", ""),
        "branch": git("git rev-parse --abbrev-ref HEAD"),
        "commit": git("git rev-parse --short HEAD"),
        "student": git("git config user.email"),
        "prompt": prompt[:1000],
        "response_summary": response_summary[:500],
    }


def save_entry(entry):
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_file


def interactive():
    print("📝 Ghi log AI thủ công")
    print("─" * 40)
    print("Tool AI bạn đã dùng:")
    for i, t in enumerate(KNOWN_TOOLS, 1):
        print(f"  {i}. {t}")
    choice = input("Chọn số hoặc nhập tên tool: ").strip()

    if choice.isdigit() and 1 <= int(choice) <= len(KNOWN_TOOLS):
        tool = KNOWN_TOOLS[int(choice) - 1]
    else:
        tool = choice.lower() or "other"

    prompt = input("Prompt / câu hỏi bạn đã hỏi AI: ").strip()
    if not prompt:
        print("[log] ❌ Prompt không được để trống.", file=sys.stderr)
        sys.exit(1)

    model = input("Model (bỏ trống nếu không biết): ").strip()
    return tool, prompt, model, ""


def main():
    parser = argparse.ArgumentParser(description="Log AI usage manually")
    parser.add_argument("--tool", help="AI tool name (e.g. chatgpt, gemini-web)")
    parser.add_argument("--prompt", help="Prompt you sent to the AI")
    parser.add_argument("--model", default="", help="Model name (optional)")
    parser.add_argument("--response", default="", help="Brief response summary (optional)")
    args = parser.parse_args()

    if args.tool and args.prompt:
        tool = args.tool.lower()
        prompt = args.prompt
        model = args.model
        response_summary = args.response
    else:
        tool, prompt, model, response_summary = interactive()

    entry = make_entry(tool, prompt, model, response_summary)
    log_file = save_entry(entry)

    short_prompt = prompt[:60] + ("..." if len(prompt) > 60 else "")
    print(f"[log] ✅ Logged: [{tool}] {short_prompt}")
    print(f"[log] 📁 Saved to: {log_file}")


if __name__ == "__main__":
    main()
