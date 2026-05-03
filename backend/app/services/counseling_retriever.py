"""Hybrid retriever for counseling_knowledge.

Pipeline:
1) Vector recall via pgvector.
2) Lexical recall (BM25 when available, overlap fallback otherwise).
3) Reciprocal Rank Fusion.
4) Lightweight rerank to top-3.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_INJECTION_RE = re.compile(
    r"(ignore previous|system prompt|developer message|do not follow|jailbreak|###\s*instruction)",
    re.IGNORECASE,
)


def sanitize_retrieved_chunk(text: str) -> str:
    cleaned = _INJECTION_RE.sub(" ", str(text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokenize(text: str) -> list[str]:
    return [tok for tok in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if tok]


def _bm25_or_overlap(query: str, docs: list[str]) -> list[float]:
    tokens = _tokenize(query)
    if not docs:
        return []
    try:
        from rank_bm25 import BM25Okapi

        corpus = [_tokenize(doc) for doc in docs]
        return [float(v) for v in BM25Okapi(corpus).get_scores(tokens)]
    except Exception:
        qset = set(tokens)
        if not qset:
            return [0.0 for _ in docs]
        scores: list[float] = []
        for doc in docs:
            dset = set(_tokenize(doc))
            scores.append(len(qset & dset) / max(1, len(qset)))
        return scores


def get_similar_counseling_examples(
    user_message: str,
    *,
    api_key: str,
    top_k: int = 3,
    min_similarity: float = 0.75,
) -> list[dict[str, str]]:
    """Hybrid retrieve + rerank counseling examples."""
    if not user_message.strip() or not api_key:
        return []
    try:
        from openai import OpenAI
        from sqlalchemy import text

        from app.services.db.session import get_engine, get_session_factory

        if get_engine().dialect.name != "postgresql":
            return []

        client = OpenAI(api_key=api_key, timeout=2.5)
        resp = client.embeddings.create(
            model=_EMBED_MODEL,
            input=[user_message[:512]],
        )
        vec = resp.data[0].embedding
        vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

        factory = get_session_factory()
        db = factory()
        try:
            rows = db.execute(
                text(
                    "SELECT question, response, "
                    "1 - (embedding <=> :vec::vector) AS similarity "
                    "FROM counseling_knowledge "
                    "ORDER BY embedding <=> :vec::vector "
                "LIMIT :top_k"
                ),
            {"vec": vec_str, "top_k": max(10, top_k * 4)},
            ).fetchall()
            lex_rows = db.execute(
                text(
                    "SELECT question, response FROM counseling_knowledge "
                    "WHERE source IS NOT NULL ORDER BY created_at DESC LIMIT 200"
                )
            ).fetchall()
        finally:
            db.close()

        vector_ranked: list[dict[str, Any]] = []
        for idx, row in enumerate(rows):
            sim = float(row.similarity or 0.0)
            if sim < min_similarity:
                continue
            vector_ranked.append(
                {
                    "instruction": sanitize_retrieved_chunk(str(row.question)),
                    "response": sanitize_retrieved_chunk(str(row.response)),
                    "vector_rank": idx + 1,
                    "vector_sim": sim,
                }
            )

        if not vector_ranked:
            return []

        lexical_docs = [f"{str(r.question)} {str(r.response)}" for r in lex_rows]
        lexical_scores = _bm25_or_overlap(user_message, lexical_docs)
        lexical_ranked = sorted(
            (
                {
                    "instruction": sanitize_retrieved_chunk(str(r.question)),
                    "response": sanitize_retrieved_chunk(str(r.response)),
                    "lex_rank": rank + 1,
                    "lex_score": score,
                }
                for rank, (r, score) in enumerate(
                    sorted(
                        zip(lex_rows, lexical_scores),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:50]
                )
            ),
            key=lambda item: item["lex_rank"],
        )

        fused: dict[tuple[str, str], dict[str, Any]] = {}
        for row in vector_ranked:
            key = (row["instruction"], row["response"])
            fused.setdefault(key, {"instruction": key[0], "response": key[1], "rrf": 0.0})
            fused[key]["rrf"] += 1.0 / (60 + row["vector_rank"])
        for row in lexical_ranked:
            key = (row["instruction"], row["response"])
            fused.setdefault(key, {"instruction": key[0], "response": key[1], "rrf": 0.0})
            fused[key]["rrf"] += 1.0 / (60 + row["lex_rank"])

        q_tokens = set(_tokenize(user_message))
        reranked = []
        for item in fused.values():
            text_blob = f"{item['instruction']} {item['response']}"
            t_tokens = set(_tokenize(text_blob))
            overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens))
            item["rerank_score"] = item["rrf"] + 0.1 * overlap - 0.01 * math.log(max(2, len(t_tokens)))
            reranked.append(item)
        reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return [
            {"instruction": row["instruction"], "response": row["response"]}
            for row in reranked[:top_k]
        ]

    except Exception as exc:
        logger.debug("counseling_retriever skipped: %s", exc)
        return []
