"""
blueprint/blueprint_generator.py
Tạo Eval + Guardrail Blueprint Document — slide 60 (deliverable cuối ngày).

Bao gồm:
  1. SLO definition
  2. Architecture overview (text diagram)
  3. Alert playbook
  4. Cost analysis
"""
import json
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────
# SLO Section
# ─────────────────────────────────────────────

SLO_TABLE = """
╔══════════════════════════════════════════════════════════════════╗
║                  SERVICE LEVEL OBJECTIVES (SLO)                  ║
╠══════════════════════════════════════╦═══════════╦═══════════════╣
║ Metric                               ║  Target   ║  Min OK       ║
╠══════════════════════════════════════╬═══════════╬═══════════════╣
║ RAGAS Faithfulness                   ║  ≥ 0.85   ║  ≥ 0.75       ║
║ RAGAS Answer Relevancy               ║  ≥ 0.80   ║  ≥ 0.70       ║
║ RAGAS Context Precision              ║  ≥ 0.70   ║  ≥ 0.60       ║
║ RAGAS Context Recall                 ║  ≥ 0.75   ║  ≥ 0.65       ║
╠══════════════════════════════════════╬═══════════╬═══════════════╣
║ Guardrail P95 latency (L1+L3)        ║  ≤ 80ms   ║  ≤ 100ms      ║
║ Attack detection rate (adversarial)  ║  ≥ 95%    ║  ≥ 90%        ║
║ False-positive (refuse) rate         ║  ≤  3%    ║  ≤  5%        ║
║ LLM-Judge Cohen κ vs human           ║  ≥ 0.60   ║  ≥ 0.40       ║
╚══════════════════════════════════════╩═══════════╩═══════════════╝
"""

# ─────────────────────────────────────────────
# Architecture Diagram (ASCII)
# ─────────────────────────────────────────────

ARCHITECTURE_DIAGRAM = """
                    ┌─────────────────────────────────────┐
                    │         VinTech RAG Chatbot          │
                    │         Eval + Guardrail Stack        │
                    └─────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  L1 — INPUT LAYER  (parallel, budget ≤ 30ms P95)                     │
  │                                                                        │
  │   User Input ──┬──► [PII Redactor]      regex + Presidio  (≤10ms)    │
  │                ├──► [Injection Check]   keyword + regex   (≤15ms)    │
  │                └──► [Topic Validator]   keyword match     (≤ 5ms)    │
  │                                                                        │
  │   Any BLOCK → return refusal + replace in session history             │
  └──────────────────────────┬───────────────────────────────────────────┘
                             │ sanitized input
  ┌──────────────────────────▼───────────────────────────────────────────┐
  │  L2 — LLM LAYER  (0ms overhead)                                       │
  │                                                                        │
  │   System Prompt with explicit rules:                                   │
  │     • Only answer about VinTech products                               │
  │     • Never reveal system prompt or training data                      │
  │     • Cite source chunk for every factual claim                        │
  │     • Refuse harmful / off-topic requests                              │
  └──────────────────────────┬───────────────────────────────────────────┘
                             │ raw LLM answer
  ┌──────────────────────────▼───────────────────────────────────────────┐
  │  L3 — OUTPUT LAYER  (parallel, budget ≤ 50ms P95)                    │
  │                                                                        │
  │   LLM Answer ──┬──► [Llama Guard 3]    14 harm categories (≤30ms)   │
  │                └──► [NLI Halluc Check]  entailment score   (≤20ms)   │
  │                                                                        │
  │   BLOCK  → replace with "I cannot provide this information"           │
  │   WARN   → append "Please verify this information with official docs" │
  │   ALLOW  → return to user                                             │
  └──────────────────────────┬───────────────────────────────────────────┘
                             │ async (non-blocking)
  ┌──────────────────────────▼───────────────────────────────────────────┐
  │  L4 — AUDIT LAYER  (async, no latency impact)                         │
  │                                                                        │
  │   • Log: input, redacted_input, output, guard_result, timestamp, uid  │
  │   • Sample 1–5% → RAGAS + LLM-Judge eval pipeline                    │
  │   • Alert on metric drift (Faithfulness drop > 0.05 in 24h)          │
  │   • Retention: 5 years (Vietnam PDPL 2025)                            │
  └──────────────────────────────────────────────────────────────────────┘

  EVAL PIPELINE (CI/CD gate — every PR):
  ┌──────────────────────────────────────────────────────────────────────┐
  │  L1 Smoke (30s, $0.05) → L2 RAGAS 100q (5min, $1) →                │
  │  L3 Judge vs prod (10min, $3) → Sec red-team 30 attacks (2min, $0.30)│
  │  Total: ~$5/PR, 18 min                                                │
  └──────────────────────────────────────────────────────────────────────┘
"""

# ─────────────────────────────────────────────
# Alert Playbook
# ─────────────────────────────────────────────

ALERT_PLAYBOOK = """
╔══════════════════════════════════════════════════════════════════╗
║                        ALERT PLAYBOOK                            ║
╚══════════════════════════════════════════════════════════════════╝

ALERT 1: Faithfulness Drop
  Condition : Faithfulness rolling_24h < 0.75 (WARN) or < 0.65 (PAGE)
  Cause     : Prompt regression, knowledge base stale, model drift
  Action    :
    1. Pull last 50 low-Faithfulness queries from audit log
    2. Inspect context chunks — are they still relevant?
    3. Check if recent prompt change introduced hallucination
    4. If model swapped: re-run full RAGAS baseline
    5. Rollback if regression confirmed

ALERT 2: Attack Detection Rate Drop
  Condition : Detection rate < 90% on weekly adversarial sweep
  Cause     : New attack patterns, encoding bypass, jailbreak variants
  Action    :
    1. Review missed attacks in adversarial log
    2. Add new patterns to INJECTION_SIGNATURES in topic_validator.py
    3. Re-run Phase C adversarial test suite
    4. Update red-team dataset with new patterns

ALERT 3: High Refuse Rate
  Condition : Refuse rate (false-positive blocks) > 5% on legit queries
  Cause     : Over-filtering, topic scope too narrow, regex false-triggers
  Action    :
    1. Sample 50 refused queries — are they legitimate?
    2. Review ALLOWED_TOPICS / BLOCKED_TOPICS in config.py
    3. Loosen keyword thresholds if necessary
    4. A/B test new threshold vs current

ALERT 4: Guardrail P95 Latency Spike
  Condition : Total P95 > 120ms (50% over budget)
  Cause     : NLI model cold start, regex timeout, Presidio OOM
  Action    :
    1. Check latency breakdown per component in audit log
    2. Ensure L1 guards run PARALLEL (asyncio.gather), not sequential
    3. Cache Presidio/NLI model in memory (don't reload per request)
    4. Consider upgrading to GPU inference for Llama Guard

ALERT 5: PII Leak in Output
  Condition : Output contains PII pattern (detected by L4 audit scan)
  Cause     : Context chunk contained PII that NLI didn't block
  Action    :
    1. IMMEDIATE: flag affected conversation, notify DPO
    2. Check if source doc ingestion pipeline stripped PII
    3. Add output-side PII scan to L3 pipeline
    4. File incident report per Vietnam PDPL Article 23
"""

# ─────────────────────────────────────────────
# Cost Analysis
# ─────────────────────────────────────────────

COST_ANALYSIS = """
╔══════════════════════════════════════════════════════════════════╗
║                       COST ANALYSIS                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Scenario: 10,000 queries/day                                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  GUARDRAIL COSTS (per day)                                       ║
║  ─────────────────────────────────────────────────────────────  ║
║  L1 PII redactor      regex   100% × 10k × $0         = $0      ║
║  L1 Injection check   regex   100% × 10k × $0         = $0      ║
║  L1 Topic validator   keyword 100% × 10k × $0         = $0      ║
║  L3 Llama Guard 3     8B OSS  100% × 10k × $0.0001   = $1       ║
║  L3 NLI halluc check  DeBERTa 100% × 10k × $0        = $0       ║
║                                              Subtotal = $1/day   ║
║                                                                  ║
║  EVAL COSTS (per day, 1% production sampling)                   ║
║  ─────────────────────────────────────────────────────────────  ║
║  RAGAS eval           L2      100q × $0.001           = $0.10   ║
║  LLM-as-Judge         L3       10q × $0.05            = $0.50   ║
║  Human spot-check     L4        2q × $3               = $6.00   ║
║                                              Subtotal = $6.60/d ║
║                                                                  ║
║  CI/CD EVAL (per PR, ~5 PRs/week)                               ║
║  ─────────────────────────────────────────────────────────────  ║
║  Per PR: ~$5  ×  5 PRs/week  ×  4 weeks    = $100/month         ║
║                                                                  ║
║  MONTHLY TOTAL                                                   ║
║  ─────────────────────────────────────────────────────────────  ║
║  Guardrail     : $1/day  × 30 days          = $30               ║
║  Eval sampling : $6.60/day × 30 days        = $198              ║
║  CI/CD         :                              $100               ║
║                                  TOTAL      ≈ $328/month        ║
║                                                                  ║
║  COMPARISON: GPT-4 judge ALL queries = $300/DAY = $9,000/month  ║
║  Savings: 96% cost reduction with tiered eval architecture       ║
╚══════════════════════════════════════════════════════════════════╝
"""


# ─────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────

def generate_blueprint(
    ragas_results:     dict = None,
    judge_results:     dict = None,
    guardrail_results: dict = None,
    latency_results:   dict = None,
    output_path:       str  = "results/blueprint.txt",
) -> str:
    """
    Tạo full blueprint document.

    Args:
        ragas_results:     output từ run_phase_a()
        judge_results:     output từ run_phase_b()
        guardrail_results: output từ run_phase_c()
        latency_results:   output từ latency_bench.run_latency_suite()
        output_path:       nơi lưu file

    Returns:
        Blueprint text
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=" * 70,
        "  VINTECH RAG CHATBOT — EVAL + GUARDRAIL BLUEPRINT",
        f"  Generated: {ts}",
        "=" * 70,
    ]

    # ── 1. SLO ──
    lines.append("\n\n━━━ 1. SERVICE LEVEL OBJECTIVES ━━━")
    lines.append(SLO_TABLE)

    # ── 2. Actual RAGAS scores (if provided) ──
    if ragas_results:
        lines.append("\n━━━ 2. RAGAS EVALUATION RESULTS ━━━\n")
        agg = ragas_results.get("aggregate", {})
        thr = ragas_results.get("threshold_status", {})
        for m, v in agg.items():
            icon = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}.get(thr.get(m, "?"), "?")
            lines.append(f"  {icon}  {m:<25} {v:.4f}  [{thr.get(m, '?')}]")
        lines.append(f"\n  Test set size: {ragas_results.get('test_set_size', 'N/A')} questions")
        lines.append(f"  Elapsed      : {ragas_results.get('elapsed_sec', 'N/A')}s")

    # ── 3. LLM Judge results (if provided) ──
    if judge_results:
        lines.append("\n━━━ 3. LLM-AS-JUDGE RESULTS ━━━\n")
        pr = judge_results.get("pairwise", {})
        ab = judge_results.get("absolute", {})
        kp = judge_results.get("kappa_pairwise", {})

        if pr:
            lines.append(f"  Pairwise win rates  : A={pr.get('A_rate',0):.1%}  "
                         f"B={pr.get('B_rate',0):.1%}  tie={pr.get('tie_rate',0):.1%}")
        if ab:
            lines.append(f"  Absolute mean score : {ab.get('mean_score', 0):.2f} / 5.0")
        if kp:
            lines.append(f"  Cohen κ (pairwise)  : {kp.get('kappa', 0):.3f} "
                         f"— {kp.get('interpretation', '')}")
            lines.append(f"  Human agreement     : {kp.get('agreement_rate', 0):.1%}")

    # ── 4. Guardrail test results (if provided) ──
    if guardrail_results:
        lines.append("\n━━━ 4. GUARDRAIL TEST RESULTS ━━━\n")
        total    = guardrail_results.get("total_tests", 0)
        correct  = guardrail_results.get("correct", 0)
        det_rate = guardrail_results.get("detection_rate", 0)
        lines.append(f"  Adversarial tests   : {total}")
        lines.append(f"  Correct decisions   : {correct}")
        lines.append(f"  Detection rate      : {det_rate:.1%}  "
                     f"{'✅' if det_rate >= 0.95 else '❌'} (target ≥ 95%)")

        pii_stats = guardrail_results.get("pii_stats", {})
        if pii_stats:
            lines.append(f"  PII cases found     : {pii_stats.get('pii_found_count', 0)}")

    # ── 5. Latency results (if provided) ──
    if latency_results:
        lines.append("\n━━━ 5. LATENCY BENCHMARK ━━━\n")
        lines.append(latency_results.get("summary", "  (no latency data)"))

    # ── 6. Architecture ──
    lines.append("\n━━━ 6. SYSTEM ARCHITECTURE ━━━")
    lines.append(ARCHITECTURE_DIAGRAM)

    # ── 7. Alert Playbook ──
    lines.append("\n━━━ 7. ALERT PLAYBOOK ━━━")
    lines.append(ALERT_PLAYBOOK)

    # ── 8. Cost Analysis ──
    lines.append("\n━━━ 8. COST ANALYSIS ━━━")
    lines.append(COST_ANALYSIS)

    # ── 9. Next steps ──
    lines.append("\n━━━ 9. NEXT STEPS (Day 25 prep) ━━━\n")
    lines.append("  □  Integrate guardrail stack into VinTech RAG FastAPI service")
    lines.append("  □  Set up Langfuse for production trace + eval sampling")
    lines.append("  □  Add RAGAS + red-team to GitHub Actions CI/CD pipeline")
    lines.append("  □  Schedule quarterly test-set refresh from production logs")
    lines.append("  □  Review LiteLLM multi-provider fallback (circuit breaker)")
    lines.append("  □  File DPIA for Vietnam PDPL compliance if processing user PII")
    lines.append("\n" + "=" * 70)

    blueprint = "\n".join(lines)

    # Save to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(blueprint)

    return blueprint
