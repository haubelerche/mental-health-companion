# Serene Evaluation Report
**Generated:** 2026-05-16T17:36:42Z  
**Mode:** offline  
**Blueprint Score:** 94.5 / 100  
**Overall Verdict:** CONDITIONAL_PASS

---

## Executive Summary

| Dimension | Score | Status |
|---|---|---|
| safety_first_runtime | 100% | PASS |
| evaluation_rigor | 100% | PASS |
| guardrails_depth | 100% | PASS |
| observability | 60% | PENDING |
| mental_health_boundary | 100% | PASS |
| frontend_authority | 70% | PENDING |
| quality_gates | 100% | PASS |

## Runner Results

### Golden Dataset
- Mode: offline
- Cases: 30 | Pass: 30 | Fail: 0
- Pass rate: 100.0%

### Adversarial Guardrails
- Cases: 20 | Pass: 16 | Fail: 0 | Skip: 4
- Pass rate (runnable): 100.0%
- P0 failures: 0

### LLM-as-Judge
- Mode: heuristic_fallback
- Cases: 50 | Pass: 50 | Fail: 0
- Overall avg: 4.22 / 5.0 (threshold 4.0)
- Safety avg: 5.00 / 5.0 (threshold 4.8 on SOS)
- Hard gate fails: 0

### RAGAS
- Status: RAGAS_DEPENDENCY_PENDING
- Cases: 59 | Hard fails: 0
- **NOTE:** 59 cases in heuristic fallback (ragas not installed)
- Faithfulness: 0.329 (threshold 0.75)
- Answer Relevancy: 0.787 (threshold 0.75)
- Context Precision: 0.519 (threshold 0.7)
- Context Recall: 0.329 (threshold 0.75)

## P1 Gaps (Open)
- Structured JSON logging (python-json-logger) — requires dep confirmation
- Prometheus metrics wiring — requires dep confirmation
- SLO YAML + alert rules + Grafana dashboard
- PHQ-9/GAD-7 localStorage → backend endpoint (Home.tsx:553,603)
- AnalystBundle.risk_indicators sanitization pass
- test_safety_escalate_integration.py expansion (target 5+ cases)
- Eval runner completion: run_ragas live scoring when ragas dep approved
- Golden dataset expansion: 30 → 150+ cases

## Recommended Actions
1. Add python-json-logger + Prometheus metrics (confirm deps with team)
1. Move PHQ-9/GAD-7 from localStorage to POST /api/v1/screening/submit
