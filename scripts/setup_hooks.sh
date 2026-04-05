#!/bin/bash
# Install git hooks:
#   pre-commit  — security & syntax checks before each commit
#   pre-push    — submit AI logs to grading server before push
set -e

echo "[hooks] Installing git hooks..."

# ── pre-commit: security & syntax checks ─────────────────────────────────────
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

# 2. Detect potential hardcoded secrets in staged Python/JS/TS files
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '\.(py|js|ts|json)$' || true)
if [ -n "$STAGED" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] || continue
        if grep -inE "(password|passwd|pwd|secret|api_key|access_key|private_key|token|credential|auth_key|db_pass)\s*=\s*['\"]?[A-Za-z0-9+/_\-]{8,}" "$f" 2>/dev/null; then
            echo -e "${YELLOW}[WARN] Possible hardcoded secret in: $f${NC}"
        fi
    done <<< "$STAGED"
fi

# 3. Python syntax check — find python interpreter (cross-platform)
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
        echo -e "${YELLOW}[WARN] Python not found in PATH — skipping syntax check.${NC}"
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

# ── pre-push: submit AI logs to grading server ────────────────────────────────
cat > ".git/hooks/pre-push" << 'HOOK'
#!/bin/bash
# Pre-push hook: submit AI interaction logs to grading server
PYTHON=""
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null && "$cmd" --version &>/dev/null 2>&1; then
        PYTHON="$cmd"
        break
    fi
done

if [ -n "$PYTHON" ]; then
    "$PYTHON" scripts/submit_log.py
else
    echo "[ai-log] Python not found — skipping log submission." >&2
fi
exit 0  # Never block push
HOOK

chmod +x ".git/hooks/pre-push"
echo "[hooks] pre-push hook installed."

# ── ensure .ai-log directory exists ──────────────────────────────────────────
mkdir -p .ai-log
touch .ai-log/.gitkeep

echo ""
echo "[hooks] Setup complete!"
echo "  pre-commit : blocks .env commits, detects hardcoded secrets, Python syntax check"
echo "  pre-push   : submit AI logs → AI_LOG_SERVER"
echo ""
echo "Next step: copy .env.example to .env and fill in your API keys."
