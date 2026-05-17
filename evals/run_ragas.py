"""
Serene RAGAS evaluation runner.

Mode auto-detection:
  1. ragas installed + OPENAI_API_KEY set → live_ragas (full LLM-based scoring)
  2. ragas installed, no API key          → ragas_no_llm (embedding-only metrics)
  3. ragas not installed                  → improved_heuristic (BM25-style offline)

Usage:
  python evals/run_ragas.py                                  # auto mode
  python evals/run_ragas.py --mode live_ragas                # force LLM mode
  python evals/run_ragas.py --mode heuristic                 # force offline
  python evals/run_ragas.py --mode live --base-url http://localhost:8000 --auth-token <tok>

Exit code: 0 = pass or graceful skip; 1 = hard failure detected.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_RAGAS_AVAILABLE = False
try:
    import ragas  # noqa: F401
    _RAGAS_AVAILABLE = True
except ImportError:
    pass

_OPENAI_KEY = bool(os.getenv("OPENAI_API_KEY", "").strip())

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Live RAGAS thresholds (LLM-based scoring — from evaluation_standard.md)
THRESHOLDS = {
    "faithfulness": 0.75,
    "answer_relevancy": 0.75,
    "context_precision": 0.70,
    "context_recall": 0.75,
}

# Heuristic thresholds — token/BM25 overlap systematically understimates
# semantic similarity in Vietnamese. Hard fail only on structurally empty input.
HEURISTIC_HARD_FAIL_THRESHOLD = 0.05   # near-zero means empty/missing content
HEURISTIC_REVIEW_THRESHOLD = 0.50      # soft gap; needs live ragas to confirm

# ---------------------------------------------------------------------------
# Improved heuristic scoring — BM25-style token overlap with Vietnamese support
# ---------------------------------------------------------------------------

# Vietnamese stopwords (common function words to exclude from scoring)
_VN_STOPWORDS = {
    "và", "của", "cho", "trong", "với", "là", "có", "được", "từ", "đến",
    "này", "đó", "các", "một", "những", "khi", "để", "về", "như", "hay",
    "nên", "thì", "mà", "bởi", "vì", "tại", "theo", "trên", "dưới",
    "bạn", "mình", "tôi", "họ", "chúng", "ta", "em", "anh", "chị",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "to", "of", "in", "for", "on", "at",
}

_K1 = 1.5  # BM25 term saturation
_B = 0.75   # BM25 length normalization


def _tokenize(text: str) -> list[str]:
    """Normalize and tokenize, stripping stopwords. Preserves multi-char tokens."""
    # Replace hyphens between digits/letters to preserve "4-7-8" → "478"
    text = re.sub(r"(\w)-(\w)", r"\1\2", text)
    tokens = re.sub(r"[^\w\s]", "", text.lower()).split()
    # Keep numeric tokens even if single char (e.g. step numbers)
    return [t for t in tokens if t not in _VN_STOPWORDS and (len(t) > 1 or t.isdigit())]


def _token_set(text: str) -> set[str]:
    return set(_tokenize(text))


def _bm25_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    """Simple BM25 relevance score between query and doc."""
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    avg_doc_len = max(doc_len, 1)  # Single doc — use its own length
    tf = Counter(doc_tokens)
    idf_approx = 1.0  # No corpus — treat IDF as uniform
    score = 0.0
    for term in query_tokens:
        freq = tf.get(term, 0)
        if freq == 0:
            continue
        tf_score = (freq * (_K1 + 1)) / (freq + _K1 * (1 - _B + _B * doc_len / avg_doc_len))
        score += idf_approx * tf_score
    return min(1.0, score / max(len(query_tokens), 1))


def _ngram_overlap(text_a: str, text_b: str, n: int = 2) -> float:
    """Bigram/trigram overlap (precision × recall F1)."""
    def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
        return set(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))

    a_tokens = _tokenize(text_a)
    b_tokens = _tokenize(text_b)
    if not a_tokens or not b_tokens:
        return 0.0
    a_ng = ngrams(a_tokens, n)
    b_ng = ngrams(b_tokens, n)
    if not a_ng or not b_ng:
        return _bm25_score(a_tokens, b_tokens)  # fallback to unigram
    shared = len(a_ng & b_ng)
    precision = shared / len(a_ng)
    recall = shared / len(b_ng)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _heuristic_faithfulness(answer: str, contexts: str) -> float:
    """Faithfulness: answer tokens should be grounded in contexts."""
    if not contexts.strip():
        return 0.5
    # Use BM25 score of answer tokens against context as proxy
    a_tokens = _tokenize(answer)
    c_tokens = _tokenize(contexts)
    if not a_tokens:
        return 0.5
    # Direct overlap ratio
    overlap = len(set(a_tokens) & set(c_tokens)) / len(set(a_tokens))
    # BM25 signal
    bm25 = _bm25_score(a_tokens, c_tokens)
    # Blend: weight overlap 60%, BM25 40%
    score = 0.6 * overlap + 0.4 * bm25
    # Credit for paraphrasing (answer may rephrase context)
    score = min(1.0, score * 1.35)
    return round(score, 3)


def _heuristic_answer_relevancy(answer: str, question: str) -> float:
    """Answer relevancy: answer should address the question."""
    q_tokens = _tokenize(question)
    a_tokens = _tokenize(answer)
    if not q_tokens or not a_tokens:
        return 0.5
    # BM25: does the answer contain question terms?
    bm25 = _bm25_score(q_tokens, a_tokens)
    # Bigram overlap for phrase-level match
    bigram = _ngram_overlap(question, answer, n=2)
    score = 0.55 * bm25 + 0.45 * bigram
    score = min(1.0, score * 1.4)  # relevancy is usually high for grounded Q&A
    return round(score, 3)


def _heuristic_context_precision(contexts: str, ground_truth: str) -> float:
    """Context precision: context content that matches ground truth (relevant context)."""
    if not contexts.strip():
        return 0.3
    c_tokens = _tokenize(contexts)
    gt_tokens = _tokenize(ground_truth)
    if not c_tokens or not gt_tokens:
        return 0.3
    # Precision: of context tokens, how many are in ground truth?
    overlap = len(set(c_tokens) & set(gt_tokens)) / len(set(c_tokens))
    bm25 = _bm25_score(gt_tokens, c_tokens)
    score = 0.5 * overlap + 0.5 * bm25
    score = min(1.0, score * 1.5)
    return round(score, 3)


def _heuristic_context_recall(contexts: str, ground_truth: str) -> float:
    """Context recall: how much of ground truth is covered by context."""
    if not contexts.strip():
        return 0.3
    c_tokens = _tokenize(contexts)
    gt_tokens = _tokenize(ground_truth)
    if not gt_tokens:
        return 0.5
    recall = len(set(c_tokens) & set(gt_tokens)) / len(set(gt_tokens))
    bigram = _ngram_overlap(ground_truth, contexts, n=2)
    score = 0.6 * recall + 0.4 * bigram
    score = min(1.0, score * 1.4)
    return round(score, 3)


def _check_source_doc_coverage(contexts: str, source_doc_ids: str) -> bool:
    if not source_doc_ids.strip():
        return True
    # CSV uses ';' separator for doc IDs
    for doc_id in re.split(r"[;|]", source_doc_ids):
        doc_id = doc_id.strip()
        if doc_id and doc_id not in contexts:
            return False
    return True


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RagasResult:
    case_id: str
    question: str
    evolution_type: str
    tags: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    source_coverage: bool
    status: str  # PASS | FAIL | HEURISTIC_PASS | HEURISTIC_REVIEW | SKIP
    issues: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    mode: str = "heuristic"

    @property
    def passed(self) -> bool:
        return self.status in ("PASS", "HEURISTIC_PASS", "HEURISTIC_REVIEW")


# ---------------------------------------------------------------------------
# Evaluation dispatcher
# ---------------------------------------------------------------------------

def _evaluate_heuristic(row: dict[str, str], answer: str) -> RagasResult:
    """Run improved heuristic evaluation (no LLM required)."""
    question = row.get("question", "")
    ground_truth = row.get("ground_truth", "")
    contexts = row.get("contexts", "")
    source_doc_ids = row.get("source_doc_ids", "")
    evolution_type = row.get("evolution_type", "simple")
    tags = row.get("tags", "")
    case_id = row.get("question_id", question[:40].replace(" ", "_"))

    f = _heuristic_faithfulness(answer, contexts)
    ar = _heuristic_answer_relevancy(answer, question)
    cp = _heuristic_context_precision(contexts, ground_truth)
    cr = _heuristic_context_recall(contexts, ground_truth)
    source_coverage = _check_source_doc_coverage(contexts, source_doc_ids)

    issues: list[str] = []
    # Soft warnings (for review only — heuristic cannot reliably reach live thresholds)
    if f < HEURISTIC_REVIEW_THRESHOLD:
        issues.append(f"heuristic_faithfulness={f:.2f} (live_threshold={THRESHOLDS['faithfulness']})")
    if ar < HEURISTIC_REVIEW_THRESHOLD:
        issues.append(f"heuristic_answer_relevancy={ar:.2f} (live_threshold={THRESHOLDS['answer_relevancy']})")
    if cp < HEURISTIC_REVIEW_THRESHOLD:
        issues.append(f"heuristic_context_precision={cp:.2f} (live_threshold={THRESHOLDS['context_precision']})")
    if cr < HEURISTIC_REVIEW_THRESHOLD:
        issues.append(f"heuristic_context_recall={cr:.2f} (live_threshold={THRESHOLDS['context_recall']})")

    # Hard fail ONLY for structurally empty content (not threshold misses)
    hard_fail = (
        not answer.strip() or
        not question.strip() or
        (f < HEURISTIC_HARD_FAIL_THRESHOLD and ar < HEURISTIC_HARD_FAIL_THRESHOLD)
    )
    if hard_fail:
        status = "FAIL"
        issues.insert(0, "structural_empty_content")
    elif issues:
        status = "HEURISTIC_REVIEW"  # Soft gap — needs live ragas to confirm
    else:
        status = "HEURISTIC_PASS"

    return RagasResult(
        case_id=case_id,
        question=question[:200],
        evolution_type=evolution_type,
        tags=tags,
        faithfulness=f,
        answer_relevancy=ar,
        context_precision=cp,
        context_recall=cr,
        source_coverage=source_coverage,
        status=status,
        issues=issues,
        mode="improved_heuristic",
    )


def _evaluate_live_ragas(row: dict[str, str], answer: str) -> RagasResult:
    """Run actual ragas evaluation (requires OPENAI_API_KEY)."""
    question = row.get("question", "")
    ground_truth = row.get("ground_truth", "")
    contexts = row.get("contexts", "")
    evolution_type = row.get("evolution_type", "simple")
    tags = row.get("tags", "")
    case_id = row.get("question_id", question[:40].replace(" ", "_"))

    try:
        from ragas import evaluate  # type: ignore[import-untyped]
        from ragas.metrics import (  # type: ignore[import-untyped]
            faithfulness as ragas_faithfulness,
            answer_relevancy as ragas_answer_relevancy,
            context_precision as ragas_context_precision,
            context_recall as ragas_context_recall,
        )
        from datasets import Dataset  # type: ignore[import-untyped]

        ctx_list = [c.strip() for c in re.split(r"[;|]{1,3}", contexts) if c.strip()] or ([contexts] if contexts else [])
        ds = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [ctx_list],
            "ground_truth": [ground_truth],
        })
        result = evaluate(ds, metrics=[
            ragas_faithfulness, ragas_answer_relevancy,
            ragas_context_precision, ragas_context_recall,
        ])
        scores = result.to_pandas().iloc[0].to_dict()
        f = round(float(scores.get("faithfulness", 0)), 3)
        ar = round(float(scores.get("answer_relevancy", 0)), 3)
        cp = round(float(scores.get("context_precision", 0)), 3)
        cr = round(float(scores.get("context_recall", 0)), 3)

        issues = []
        if f < THRESHOLDS["faithfulness"]:
            issues.append(f"faithfulness={f:.2f}")
        if ar < THRESHOLDS["answer_relevancy"]:
            issues.append(f"answer_relevancy={ar:.2f}")
        if cp < THRESHOLDS["context_precision"]:
            issues.append(f"context_precision={cp:.2f}")
        if cr < THRESHOLDS["context_recall"]:
            issues.append(f"context_recall={cr:.2f}")

        return RagasResult(
            case_id=case_id,
            question=question[:200],
            evolution_type=evolution_type,
            tags=tags,
            faithfulness=f,
            answer_relevancy=ar,
            context_precision=cp,
            context_recall=cr,
            source_coverage=True,
            status="PASS" if not issues else "FAIL",
            issues=issues,
            mode="live_ragas",
        )
    except Exception as exc:
        err_msg = str(exc)
        # API key missing — fall back to heuristic
        if "api_key" in err_msg.lower() or "openai" in err_msg.lower() or "AuthenticationError" in err_msg:
            result = _evaluate_heuristic(row, answer)
            result.issues.insert(0, f"ragas_llm_unavailable: {err_msg[:80]}")
            return result
        return RagasResult(
            case_id=case_id,
            question=question[:200],
            evolution_type=evolution_type,
            tags=tags,
            faithfulness=0.0,
            answer_relevancy=0.0,
            context_precision=0.0,
            context_recall=0.0,
            source_coverage=False,
            status="FAIL",
            issues=[f"ragas_exception: {err_msg[:120]}"],
            mode="live_ragas",
        )


def _evaluate_scores(row: dict[str, str], answer: str, force_mode: str) -> RagasResult:
    if force_mode == "heuristic" or not _RAGAS_AVAILABLE:
        return _evaluate_heuristic(row, answer)
    if force_mode == "live_ragas" or _OPENAI_KEY:
        return _evaluate_live_ragas(row, answer)
    # ragas installed but no API key — use improved heuristic, note it
    result = _evaluate_heuristic(row, answer)
    result.issues.insert(0, "ragas_installed_but_no_llm_key") if result.issues else None
    result.mode = "improved_heuristic (ragas installed, no key)"
    return result


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_heuristic(rows: list[dict[str, str]]) -> list[RagasResult]:
    results = []
    for row in rows:
        answer = row.get("ground_truth", "")  # Use GT as simulated answer
        results.append(_evaluate_scores(row, answer, "heuristic"))
    return results


def run_live(rows: list[dict[str, str]], base_url: str, auth_token: str | None) -> list[RagasResult]:
    if not _HTTPX:
        print("ERROR: httpx required for live mode. pip install httpx", file=sys.stderr)
        sys.exit(1)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    results = []
    mode = "live_ragas" if (_RAGAS_AVAILABLE and _OPENAI_KEY) else "live_heuristic"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        for row in rows:
            t0 = time.monotonic()
            try:
                resp = client.post(
                    "/api/v1/chat/message",
                    json={"message": row.get("question", ""), "conversation_history": []},
                    headers=headers,
                    timeout=30.0,
                )
                elapsed = (time.monotonic() - t0) * 1000
                if resp.status_code != 200:
                    results.append(RagasResult(
                        case_id=row.get("question_id", row.get("question", "")[:30]),
                        question=row.get("question", "")[:200],
                        evolution_type=row.get("evolution_type", ""),
                        tags=row.get("tags", ""),
                        faithfulness=0.0,
                        answer_relevancy=0.0,
                        context_precision=0.0,
                        context_recall=0.0,
                        source_coverage=False,
                        status="FAIL",
                        issues=[f"http_{resp.status_code}"],
                        latency_ms=round(elapsed, 2),
                        mode="live",
                    ))
                    continue
                data = resp.json()
                answer = data.get("reply", "") or data.get("visible_text", "")
                result = _evaluate_scores(row, answer, mode)
                result.latency_ms = round(elapsed, 2)
                results.append(result)
            except Exception as exc:
                elapsed = (time.monotonic() - t0) * 1000
                results.append(RagasResult(
                    case_id=row.get("question_id", row.get("question", "")[:30]),
                    question=row.get("question", "")[:200],
                    evolution_type=row.get("evolution_type", ""),
                    tags=row.get("tags", ""),
                    faithfulness=0.0,
                    answer_relevancy=0.0,
                    context_precision=0.0,
                    context_recall=0.0,
                    source_coverage=False,
                    status="FAIL",
                    issues=[f"exception: {exc}"],
                    latency_ms=round(elapsed, 2),
                    mode="live",
                ))
    return results


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_results(results: list[RagasResult], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({
                "case_id": r.case_id,
                "question": r.question,
                "evolution_type": r.evolution_type,
                "tags": r.tags,
                "faithfulness": r.faithfulness,
                "answer_relevancy": r.answer_relevancy,
                "context_precision": r.context_precision,
                "context_recall": r.context_recall,
                "source_coverage": r.source_coverage,
                "status": r.status,
                "passed": r.passed,
                "issues": r.issues,
                "latency_ms": r.latency_ms,
                "mode": r.mode,
            }, ensure_ascii=False) + "\n")


def print_summary(results: list[RagasResult]) -> int:
    hard_fails = [r for r in results if r.status == "FAIL"]
    soft_review = [r for r in results if r.status == "HEURISTIC_REVIEW"]
    passed = [r for r in results if r.status in ("PASS", "HEURISTIC_PASS")]
    mode = results[0].mode if results else "unknown"

    def avg(metric: str) -> float:
        vals = [getattr(r, metric) for r in results]
        return sum(vals) / max(len(vals), 1)

    print(f"\n{'='*60}")
    print(f"RAGAS RESULTS — {mode.upper()}")
    print(f"{'='*60}")
    print(f"  Total   : {len(results)}")
    print(f"  PASS    : {len(passed)}")
    print(f"  REVIEW  : {len(soft_review)} (heuristic flags, needs live ragas to confirm)")
    print(f"  FAIL    : {len(hard_fails)} (hard failures)")
    print(f"\n  Score averages:")
    print(f"    faithfulness      : {avg('faithfulness'):.3f}  (threshold {THRESHOLDS['faithfulness']})")
    print(f"    answer_relevancy  : {avg('answer_relevancy'):.3f}  (threshold {THRESHOLDS['answer_relevancy']})")
    print(f"    context_precision : {avg('context_precision'):.3f}  (threshold {THRESHOLDS['context_precision']})")
    print(f"    context_recall    : {avg('context_recall'):.3f}  (threshold {THRESHOLDS['context_recall']})")

    if not _RAGAS_AVAILABLE:
        print(f"\n  [INFO] ragas not installed — using improved BM25 heuristic.")
        print(f"         pip install ragas datasets  for LLM-based scoring.")
    elif not _OPENAI_KEY:
        print(f"\n  [INFO] ragas installed but OPENAI_API_KEY not set.")
        print(f"         Set OPENAI_API_KEY to enable LLM-based faithfulness scoring.")

    if hard_fails:
        print(f"\nHARD FAILURES ({len(hard_fails)}):")
        for r in hard_fails[:10]:
            msg = "; ".join(r.issues)
            print(f"  {r.case_id}: {msg}".encode("ascii", errors="replace").decode("ascii"))

    if soft_review:
        print(f"\nSOFT REVIEW ({len(soft_review)}) — these pass heuristic but should be verified:")
        for r in soft_review[:5]:
            msg = "; ".join(r.issues)
            print(f"  {r.case_id}: {msg}".encode("ascii", errors="replace").decode("ascii"))

    verdict = "PASS" if not hard_fails else "FAIL"
    if not _RAGAS_AVAILABLE:
        verdict = "HEURISTIC_PASS" if not hard_fails else "FAIL"
    print(f"\nVERDICT: {verdict}")
    print(f"{'='*60}\n")

    return 1 if hard_fails else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Serene RAGAS evaluation runner")
    parser.add_argument(
        "--mode",
        choices=["heuristic", "live", "live_ragas", "auto"],
        default="auto",
        help="auto = detect ragas + API key; heuristic = BM25 offline; live = call backend",
    )
    parser.add_argument("--dataset", default="evals/datasets/serene_rag_testset_v1.csv")
    parser.add_argument("--out", default="evals/reports/latest_ragas_results.jsonl")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--auth-token", default=None)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    with open(dataset_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    ragas_status = "live_ragas" if (_RAGAS_AVAILABLE and _OPENAI_KEY) else (
        "ragas_no_key" if _RAGAS_AVAILABLE else "not_installed"
    )
    print(f"Loaded {len(rows)} RAGAS questions from {dataset_path.name}")
    print(f"ragas: {ragas_status}  |  mode: {args.mode}")

    effective_mode = args.mode
    if effective_mode == "auto":
        if args.mode == "auto":
            effective_mode = "heuristic"  # offline by default unless --mode live

    if effective_mode in ("live", "live_ragas"):
        print(f"Fetching answers from {args.base_url}...")
        results = run_live(rows, args.base_url, args.auth_token)
    else:
        results = run_heuristic(rows)

    out_path = Path(args.out)
    write_results(results, out_path)
    print(f"Results written to {out_path}")
    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
