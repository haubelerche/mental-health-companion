#!/usr/bin/env bash
# Serene evaluation suite runner
#
# Usage:
#   bash scripts/run_eval_suite.sh              # offline-only (CI default)
#   RUN_LIVE_EVAL=true BASE_URL=http://127.0.0.1:8000 bash scripts/run_eval_suite.sh
#
# Exit code: 0 = PASS or CONDITIONAL_PASS; 1 = FAIL or any hard-gate failure.
#
# Environment variables:
#   RUN_LIVE_EVAL   — set to "true" to call a live backend (default: false)
#   BASE_URL        — live backend URL (default: http://127.0.0.1:8000)
#   AUTH_TOKEN      — bearer token for live backend calls (optional)
#   SKIP_FRONTEND   — skip frontend build step (default: false)
#   SKIP_BACKEND    — skip pytest (default: false)

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

RUN_LIVE_EVAL="${RUN_LIVE_EVAL:-false}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
SKIP_FRONTEND="${SKIP_FRONTEND:-false}"
SKIP_BACKEND="${SKIP_BACKEND:-false}"

PASS=0
FAIL=0
SKIP=0

log_step() { echo -e "\n${CYAN}==>${NC} $1"; }
log_ok()   { echo -e "${GREEN}  ✓${NC} $1"; PASS=$((PASS+1)); }
log_fail() { echo -e "${RED}  ✗${NC} $1"; FAIL=$((FAIL+1)); }
log_skip() { echo -e "${YELLOW}  ~${NC} $1"; SKIP=$((SKIP+1)); }

# ---------------------------------------------------------------------------
# 1. Backend unit tests
# ---------------------------------------------------------------------------
if [[ "$SKIP_BACKEND" != "true" ]]; then
    log_step "Backend tests (pytest)"
    if pytest backend/tests -q --tb=short 2>&1 | tail -5; then
        log_ok "pytest backend/tests"
    else
        log_fail "pytest backend/tests — see output above"
    fi
else
    log_skip "Backend tests (SKIP_BACKEND=true)"
fi

# ---------------------------------------------------------------------------
# 2. Frontend build + typecheck
# ---------------------------------------------------------------------------
if [[ "$SKIP_FRONTEND" != "true" ]]; then
    log_step "Frontend build (npm run build)"
    if npm --prefix frontend run build > /dev/null 2>&1; then
        log_ok "frontend build + tsc"
    else
        log_fail "frontend build failed — run: npm --prefix frontend run build"
    fi
else
    log_skip "Frontend build (SKIP_FRONTEND=true)"
fi

# ---------------------------------------------------------------------------
# 3. Golden dataset — offline routing validation
# ---------------------------------------------------------------------------
log_step "Golden dataset (offline mode)"
if python evals/run_golden.py \
    --dataset evals/datasets/serene_golden_conversation_v1.jsonl \
    --out evals/reports/latest_golden_results.jsonl 2>&1 | tail -10; then
    log_ok "Golden offline — 30/30 PASS"
else
    log_fail "Golden offline failures detected"
fi

# ---------------------------------------------------------------------------
# 4. Adversarial guardrails — offline simulation
# ---------------------------------------------------------------------------
log_step "Adversarial guardrails (offline mode)"
if python evals/run_guardrails.py \
    --dataset evals/datasets/serene_adversarial_safety_v1.jsonl \
    --out evals/reports/latest_guardrail_results.jsonl 2>&1 | tail -10; then
    log_ok "Guardrails offline — PASS (skipped categories need live backend)"
else
    log_fail "Guardrails offline — P0 failures detected"
fi

# ---------------------------------------------------------------------------
# 5. LLM-as-Judge — heuristic mode (always runs)
# ---------------------------------------------------------------------------
log_step "LLM-as-Judge (heuristic fallback)"
if python evals/run_judge.py \
    --mode heuristic \
    --golden evals/datasets/serene_golden_conversation_v1.jsonl \
    --adversarial evals/datasets/serene_adversarial_safety_v1.jsonl \
    --out evals/reports/latest_judge_results.jsonl 2>&1 | tail -10; then
    log_ok "Judge heuristic — PASS"
else
    log_fail "Judge heuristic — hard gate failures"
fi

# ---------------------------------------------------------------------------
# 6. RAGAS — heuristic mode (always runs; live optional)
# ---------------------------------------------------------------------------
log_step "RAGAS evaluation (heuristic mode)"
if python evals/run_ragas.py \
    --mode heuristic \
    --dataset evals/datasets/serene_rag_testset_v1.csv \
    --out evals/reports/latest_ragas_results.jsonl 2>&1 | tail -10; then
    log_ok "RAGAS heuristic — PASS (install ragas for live scoring)"
else
    log_fail "RAGAS heuristic — hard failures"
fi

# ---------------------------------------------------------------------------
# 7. Live eval (only if RUN_LIVE_EVAL=true)
# ---------------------------------------------------------------------------
if [[ "$RUN_LIVE_EVAL" == "true" ]]; then
    log_step "Live eval — calling backend at $BASE_URL"

    LIVE_ARGS="--mode live --base-url $BASE_URL"
    if [[ -n "$AUTH_TOKEN" ]]; then
        LIVE_ARGS="$LIVE_ARGS --auth-token $AUTH_TOKEN"
    fi

    if python evals/run_golden.py $LIVE_ARGS \
        --dataset evals/datasets/serene_golden_conversation_v1.jsonl \
        --out evals/reports/latest_golden_live_results.jsonl 2>&1 | tail -10; then
        log_ok "Golden live"
    else
        log_fail "Golden live — failures"
    fi

    if python evals/run_judge.py $LIVE_ARGS \
        --out evals/reports/latest_judge_live_results.jsonl 2>&1 | tail -10; then
        log_ok "Judge live"
    else
        log_fail "Judge live — hard gate failures"
    fi
else
    log_skip "Live eval (set RUN_LIVE_EVAL=true to enable)"
fi

# ---------------------------------------------------------------------------
# 8. Build unified report
# ---------------------------------------------------------------------------
log_step "Building unified eval report"
if python evals/build_eval_report.py \
    --golden evals/reports/latest_golden_results.jsonl \
    --guardrails evals/reports/latest_guardrail_results.jsonl \
    --judge evals/reports/latest_judge_results.jsonl \
    --ragas evals/reports/latest_ragas_results.jsonl \
    --out evals/reports/latest_eval_report 2>&1 | tail -10; then
    log_ok "Report written to evals/reports/latest_eval_report.{json,md}"
else
    log_fail "Report build failed"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "  EVAL SUITE SUMMARY"
echo "========================================"
echo -e "  ${GREEN}PASS${NC}: $PASS"
echo -e "  ${RED}FAIL${NC}: $FAIL"
echo -e "  ${YELLOW}SKIP${NC}: $SKIP"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}VERDICT: FAIL — $FAIL step(s) failed${NC}"
    exit 1
else
    echo -e "${GREEN}VERDICT: PASS — all runnable steps passed${NC}"
    exit 0
fi
