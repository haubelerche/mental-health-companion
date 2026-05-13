from __future__ import annotations

import logging
import math
import re
from typing import Any

from app.services.schemas.advisors import AdvisorCase, AdvisorCaseRetrievalResult

logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"
_INJECTION_RE = re.compile(
    r"(ignore previous|system prompt|developer message|do not follow|jailbreak|###\s*instruction)",
    re.IGNORECASE,
)


def sanitize_case_text(text: str, *, limit: int = 1200) -> str:
    cleaned = _INJECTION_RE.sub(" ", str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.split(r"[^a-zA-Z0-9_]+", (text or "").lower()) if len(tok) >= 3}


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [sanitize_case_text(str(item), limit=280) for item in value if str(item or "").strip()]
    if isinstance(value, str) and value.strip():
        return [sanitize_case_text(value, limit=280)]
    return []


def _json_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _case_from_row(row: Any, *, retrieval_score: float | None = None) -> AdvisorCase:
    return AdvisorCase(
        case_id=str(row.case_id),
        raw_case_id=str(row.raw_case_id) if row.raw_case_id is not None else None,
        language=str(row.language or "vi"),
        user_context=sanitize_case_text(str(row.user_context or "")),
        primary_problem=sanitize_case_text(str(row.primary_problem or ""), limit=500) or None,
        topic_tags=_json_list(row.topic_tags),
        emotional_state_tags=_json_list(row.emotional_state_tags),
        interaction_need=sanitize_case_text(str(row.interaction_need or ""), limit=80) or None,
        cognitive_pattern_tags=_json_list(row.cognitive_pattern_tags),
        counseling_goal=sanitize_case_text(str(row.counseling_goal or ""), limit=500) or None,
        recommended_approach=sanitize_case_text(str(row.recommended_approach or ""), limit=500) or None,
        intervention_steps=_json_list(row.intervention_steps),
        reflection_questions=_json_list(row.reflection_questions),
        do_say=_json_list(row.do_say),
        do_not_say=_json_list(row.do_not_say),
        risk_flags=_json_list(row.risk_flags),
        source_response_summary=sanitize_case_text(str(row.source_response_summary or ""), limit=700) or None,
        safety_review_status=str(row.safety_review_status or "pending"),
        quality_score=float(row.quality_score) if row.quality_score is not None else None,
        source=sanitize_case_text(str(getattr(row, "source", "") or ""), limit=120) or None,
        advisor_domains=_json_list(getattr(row, "advisor_domains", [])),
        safety_constraints=_json_dict(getattr(row, "safety_constraints", {})),
        metadata=_json_dict(getattr(row, "metadata", {})),
        reviewed_by=sanitize_case_text(str(getattr(row, "reviewed_by", "") or ""), limit=120) or None,
        retrieval_score=retrieval_score,
    )


class AdvisorCaseRetriever:
    def __init__(self, *, api_key: str | None = None) -> None:
        self.api_key = api_key

    def retrieve(
        self,
        user_message: str,
        *,
        interaction_need: str | None = None,
        top_k: int = 4,
        approved_only: bool = True,
    ) -> AdvisorCaseRetrievalResult:
        if not str(user_message or "").strip():
            return AdvisorCaseRetrievalResult(cases=[], approved_only=approved_only)
        try:
            from sqlalchemy import text

            from app.services.db.session import get_engine, get_session_factory

            engine = get_engine()
            if engine.dialect.name != "postgresql":
                return AdvisorCaseRetrievalResult(cases=[], approved_only=approved_only)

            vec_str = self._embed_query(user_message)
            factory = get_session_factory()
            db = factory()
            try:
                if vec_str:
                    rows = db.execute(
                        text(
                            """
                            SELECT *,
                                   1 - (embedding <=> :vec::vector) AS retrieval_score
                            FROM app.advisor_case_library
                            WHERE embedding IS NOT NULL
                              AND (:approved_only IS FALSE OR safety_review_status = 'approved')
                              AND (:need IS NULL OR interaction_need = :need OR interaction_need IS NULL)
                            ORDER BY embedding <=> :vec::vector
                            LIMIT :limit
                            """
                        ),
                        {
                            "vec": vec_str,
                            "approved_only": bool(approved_only),
                            "need": interaction_need,
                            "limit": max(8, top_k * 3),
                        },
                    ).fetchall()
                else:
                    rows = []

                if not rows:
                    rows = db.execute(
                        text(
                            """
                            SELECT *, NULL::double precision AS retrieval_score
                            FROM app.advisor_case_library
                            WHERE (:approved_only IS FALSE OR safety_review_status = 'approved')
                              AND (:need IS NULL OR interaction_need = :need OR interaction_need IS NULL)
                            ORDER BY created_at DESC
                            LIMIT :limit
                            """
                        ),
                        {
                            "approved_only": bool(approved_only),
                            "need": interaction_need,
                            "limit": max(25, top_k * 8),
                        },
                    ).fetchall()
            finally:
                db.close()

            cases = [_case_from_row(row, retrieval_score=getattr(row, "retrieval_score", None)) for row in rows]
            ranked = self._rerank(user_message, cases)[:top_k]
            return AdvisorCaseRetrievalResult(cases=ranked, approved_only=approved_only, fallback_used=not bool(vec_str))
        except Exception as exc:
            logger.debug("advisor case retrieval skipped: %s", exc)
            return AdvisorCaseRetrievalResult(cases=[], approved_only=approved_only)

    def _embed_query(self, user_message: str) -> str | None:
        if not self.api_key:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, timeout=2.5)
            resp = client.embeddings.create(model=_EMBED_MODEL, input=[user_message[:512]])
            vec = resp.data[0].embedding
            return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
        except Exception as exc:
            logger.debug("advisor case embedding skipped: %s", exc)
            return None

    @staticmethod
    def _rerank(user_message: str, cases: list[AdvisorCase]) -> list[AdvisorCase]:
        q = _tokenize(user_message)
        if not q:
            return cases

        def score(case: AdvisorCase) -> float:
            text_blob = " ".join(
                [
                    case.user_context,
                    case.primary_problem or "",
                    " ".join(case.topic_tags),
                    " ".join(case.emotional_state_tags),
                    " ".join(case.cognitive_pattern_tags),
                    case.counseling_goal or "",
                    case.recommended_approach or "",
                ]
            )
            tokens = _tokenize(text_blob)
            overlap = len(q & tokens) / max(1, len(q))
            base = float(case.retrieval_score or 0.0)
            quality = float(case.quality_score or 0.0)
            length_penalty = 0.01 * math.log(max(2, len(tokens)))
            return base + overlap + 0.1 * quality - length_penalty

        return sorted(cases, key=score, reverse=True)
