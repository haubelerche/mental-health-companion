#!/bin/bash
# Install git hooks:
#   pre-commit - security and syntax checks before each commit
#   pre-push   - submit AI logs to the grading server before push
set -e

echo "[hooks] Installing git hooks..."

# pre-commit: security and syntax checks
cat > ".git/hooks/pre-commit" << 'HOOK'
#!/bin/bash
# Pre-commit hook: security checks + Python syntax validation
set -e

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

echo "[pre-commit] Running checks..."

FAILED=0

# 1. Block accidental .env commits
if git diff --cached --name-only | grep -qE '^\.env$'; then
    echo -e "${RED}[ERROR] .env file is staged for commit. Remove it: git reset HEAD .env${NC}"
    FAILED=1
fi

# 2. Detect potential hardcoded secrets in staged Python/JS/TS/JSON files
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.(py|js|ts|json)$' || true)
if [ -n "$STAGED" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] || continue
        if grep -inE "(password|passwd|pwd|secret|api_key|access_key|private_key|token|credential|auth_key|db_pass)\s*=\s*['\"]?[A-Za-z0-9+/_\-]{8,}" "$f" 2>/dev/null; then
            echo -e "${YELLOW}[WARN] Possible hardcoded secret in: $f${NC}"
        fi
    done <<< "$STAGED"
fi

# 3. Python syntax check - find Python interpreter cross-platform
PYTHON=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null && "$cmd" --version &>/dev/null 2>&1; then
        PYTHON="$cmd"
        break
    fi
done

PY_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep '\.py$' || true)
if [ -n "$PY_FILES" ]; then
    if [ -z "$PYTHON" ]; then
        echo -e "${YELLOW}[WARN] Python not found in PATH - skipping syntax check.${NC}"
    else
        while IFS= read -r f; do
            [ -f "$f" ] || continue
            if ! "$PYTHON" -m py_compile "$f" 2>/dev/null; then
                echo -e "${RED}[ERROR] Python syntax error in: $f${NC}"
                "$PYTHON" -m py_compile "$f"
                FAILED=1
            fi
        done <<< "$PY_FILES"
        [ "$FAILED" -eq 0 ] && echo -e "${GREEN}[pre-commit] Python syntax OK.${NC}"
    fi
fi

if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}[pre-commit] Checks failed. Fix errors above and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}[pre-commit] All checks passed.${NC}"
exit 0
HOOK

chmod +x ".git/hooks/pre-commit"
echo "[hooks] pre-commit hook installed."

# pre-push: block if no AI logs, then submit
cat > ".git/hooks/pre-push" << 'HOOK'
#!/bin/bash
# Pre-push hook: block push if no AI logs found; submit logs to grading server

echo "[ai-log] Checking AI usage logs before push..."

# Detect Python 3
PYTHON=""
for cmd in python3 python py \
    "$HOME/anaconda3/python.exe" "$HOME/miniconda3/python.exe" \
    "$HOME/AppData/Local/Programs/Python/Python3"*/python.exe; do
    if command -v "$cmd" &>/dev/null && "$cmd" --version 2>&1 | grep -q "Python 3"; then
        PYTHON="$cmd"
        break
    fi
done

LOG_FILE="${AI_LOG_DIR:-.ai-log}/session.jsonl"

_block() {
    echo ""
    echo "[ai-log] BLOCKED: No AI logs found."
    echo ""
    echo "No AI usage log was found for this working session."
    echo "Every team member must record AI usage before pushing."
    echo ""
    echo "How to record logs:"
    echo "  - Automatic-hook tools: Claude Code, Cursor, Codex, Gemini CLI, Copilot."
    echo "    Run: bash scripts/setup_hooks.sh"
    echo "  - ChatGPT, Gemini Web, or another tool without a hook."
    echo "    Run: python scripts/log_manual.py"
    echo ""
    echo "After logging, run git push again."
    return 1
}

# Check log file exists and is non-empty
if [ ! -f "$LOG_FILE" ] || [ ! -s "$LOG_FILE" ]; then
    _block; exit 1
fi

# Count valid JSON entries
if [ -n "$PYTHON" ]; then
    COUNT=$(AI_LOG_FILE="$LOG_FILE" "$PYTHON" -c "
import json, os
n = 0
log_file = os.environ['AI_LOG_FILE']
with open(log_file, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            try: json.loads(line); n += 1
            except Exception: pass
print(n)
" 2>/dev/null)
else
    COUNT=$(grep -c '[^[:space:]]' "$LOG_FILE" 2>/dev/null || echo 0)
fi

if [ -z "$COUNT" ] || [ "$COUNT" -eq 0 ] 2>/dev/null; then
    _block; exit 1
fi

echo ""
echo "[ai-log] Found $COUNT log entries."
echo ""
echo "AI tools with recorded logs:"

if [ -n "$PYTHON" ]; then
    AI_LOG_FILE="$LOG_FILE" "$PYTHON" - << 'PYEOF'
import json, collections, os
counts = collections.Counter()
log_file = os.environ['AI_LOG_FILE']
with open(log_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                counts[json.loads(line).get("tool", "unknown")] += 1
            except Exception:
                pass
for tool, n in counts.most_common():
    print(f"   - {tool}: {n} entries")
PYEOF
fi

echo ""

# Submit logs to grading server
if [ -f "scripts/submit_log.py" ] && [ -n "$PYTHON" ]; then
    echo "[ai-log] Submitting logs to grading server..."
    "$PYTHON" scripts/submit_log.py
fi

echo ""
echo "[ai-log] Push allowed."
exit 0
HOOK

chmod +x ".git/hooks/pre-push"
echo "[hooks] pre-push hook installed."

# Ensure .ai-log directory exists
mkdir -p .ai-log
touch .ai-log/.gitkeep

echo ""
echo "[hooks] Setup complete."
echo "  pre-commit : blocks .env commits, detects hardcoded secrets, checks Python syntax"
echo "  pre-push   : submits AI logs to AI_LOG_SERVER"
echo ""
echo "Next step: copy .env.example to .env and fill in required API keys when needed."
