#!/usr/bin/env python3
"""
  python scripts/review_pr.py            # review main 
  python scripts/review_pr.py develop    # review branch phụ
  python scripts/review_pr.py --staged   # review only staged changes
"""
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import re
import sys
import subprocess
from pathlib import Path

try:
    load_dotenv()
except ImportError:
    pass


REVIEW_PROMPT = """You are an expert code reviewer. Review the following git diff and provide a structured analysis.

Focus on:

## 1. Security Issues
- Hardcoded secrets, API keys, passwords
- SQL injection, XSS, command injection risks
- Insecure dependencies or imports
- Authentication/authorization gaps

## 2. Test Coverage
- Which new functions/logic lack tests
- Edge cases that should be tested
- Suggested test cases (be specific)

## 3. Code Quality
- Bugs or logic errors
- Unhandled exceptions or edge cases
- Performance concerns
- Naming and readability

## 4. Summary
Overall assessment: APPROVE / REQUEST_CHANGES / NEEDS_ATTENTION

Be specific and actionable. Reference file names and line numbers where possible.

---
Git diff:
```
{diff}
```
"""


def run_git(cmd: list) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError:
        return ""


def get_diff(base: str = "main", staged_only: bool = False) -> str:
    if staged_only:
        return run_git(["git", "diff", "--cached"])

    # Try comparing against base branch
    diff = run_git(["git", "diff", f"{base}...HEAD"])
    if diff:
        return diff

    # Fallback: last commit vs working tree
    diff = run_git(["git", "diff", "HEAD~1", "HEAD"])
    if diff:
        return diff

    return run_git(["git", "diff", "--cached"])


def _smart_truncate(diff: str, max_chars: int) -> str:
    """Truncate diff at file boundaries to avoid cutting mid-context."""
    if len(diff) <= max_chars:
        return diff

    # Split into per-file sections (lines starting with "diff --git")
    parts = re.split(r'(?=^diff --git )', diff, flags=re.MULTILINE)

    included = []
    total = 0
    omitted_files = []

    for part in parts:
        if total + len(part) <= max_chars:
            included.append(part)
            total += len(part)
        else:
            # Extract filename for the omission notice
            m = re.search(r'^diff --git a/(\S+)', part, re.MULTILINE)
            omitted_files.append(m.group(1) if m else "unknown")

    result = "".join(included)
    if omitted_files:
        result += (
            f"\n\n... [diff truncated: {len(omitted_files)} file(s) omitted"
            f" ({len(diff) - total} chars): {', '.join(omitted_files)}] ..."
        )
    return result


def review_code(diff: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY is not set. Check your .env file."

    model = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-20250514")
    max_diff_chars = int(os.environ.get("MAX_DIFF_CHARS", "50000"))
    client = Anthropic(api_key=api_key)

    truncated = _smart_truncate(diff, max_diff_chars)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": REVIEW_PROMPT.format(diff=truncated)
            }]
        )
        return response.content[0].text
    except Exception as e:
        print(f"[review] Anthropic API error: {e}", file=sys.stderr)
        sys.exit(1)


def save_review(review: str) -> Path:
    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    output = log_dir / "last-review.md"
    try:
        output.write_text(review, encoding="utf-8")
    except OSError as e:
        print(f"[review] Could not save review: {e}", file=sys.stderr)
    return output


def main():
    staged_only = "--staged" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else "main"

    if staged_only:
        print("[review] Reviewing staged changes...\n")
    else:
        print(f"[review] Reviewing changes against '{base}'...\n")

    diff = get_diff(base=base, staged_only=staged_only)
    if not diff.strip():
        print("[review] No changes found to review.")
        sys.exit(0)

    print(f"[review] Diff size: {len(diff)} chars. Sending to Claude...\n")
    review = review_code(diff)

    print(review)

    saved = save_review(review)
    print(f"\n[review] Saved to {saved}")


if __name__ == "__main__":
    main()
