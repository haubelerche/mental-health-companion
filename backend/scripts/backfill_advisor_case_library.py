"""Backfill app.advisor_case_library from app.counseling_knowledge.

Usage:
    python backend/scripts/backfill_advisor_case_library.py --dry-run --limit 10
    python backend/scripts/backfill_advisor_case_library.py --limit 500

The script stores internal counseling guidance only. It never writes a final
user-facing assistant answer copied from the source response.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
for _p in (_BACKEND, _REPO):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.replace("Ä‘", "d").lower()).strip()


def _tags_from_text(text: str) -> tuple[list[str], list[str], list[str], list[str]]:
    normalized = _normalize(text)
    topics: list[str] = []
    emotions: list[str] = []
    patterns: list[str] = []
    risks: list[str] = []

    checks = (
        ("family_pressure", ("gia dinh", "bo me", "ba me", "cha me")),
        ("work_study_pressure", ("deadline", "hoc", "thi", "cong viec", "lam viec", "sep")),
        ("relationship_stress", ("nguoi yeu", "ban be", "dong nghiep", "crush", "chia tay")),
        ("sleep_energy", ("mat ngu", "khong ngu", "met", "can kiet", "bo bua", "khong an")),
        ("boundaries", ("ranh gioi", "tu choi", "lam vua long", "ap luc")),
    )
    for tag, needles in checks:
        if any(k in normalized for k in needles):
            topics.append(tag)

    emotion_checks = (
        ("overwhelmed", ("qua tai", "ngop", "met", "can kiet", "ap luc")),
        ("sad", ("buon", "khoc", "that vong")),
        ("anxious", ("lo", "bat an", "hoang", "so")),
        ("guilty", ("toi loi", "tu trach", "loi tai minh")),
        ("angry", ("tuc", "gian", "buc")),
    )
    for tag, needles in emotion_checks:
        if any(k in normalized for k in needles):
            emotions.append(tag)

    pattern_checks = (
        ("self_blame", ("loi tai minh", "tu trach", "do minh", "vo dung")),
        ("catastrophizing", ("hong het", "fail", "khong con cach", "chac chan")),
        ("mind_reading", ("ho nghi", "ho ghe", "bi danh gia")),
        ("people_pleasing", ("lam vua long", "so that vong", "khong dam tu choi")),
        ("helplessness_belief", ("bat luc", "mac ket", "khong biet lam sao")),
    )
    for tag, needles in pattern_checks:
        if any(k in normalized for k in needles):
            patterns.append(tag)

    if any(k in normalized for k in ("tu tu", "chet", "tu hai", "khong muon song")):
        risks.append("self_harm_signal")
    if any(k in normalized for k in ("danh", "dam", "giet", "lam hai nguoi")):
        risks.append("harm_to_others_signal")

    return topics, emotions, patterns, risks


def infer_interaction_need(question: str, response: str = "") -> str:
    normalized = _normalize(f"{question} {response}")
    if any(k in normalized for k in ("tu tu", "tu hai", "khong muon song", "lam hai")):
        return "safety"
    if any(k in normalized for k in ("hoang", "run", "kho tho", "ngop", "mat ngu")):
        return "grounding"
    if any(k in normalized for k in ("suy dien", "loi tai minh", "vo dung", "khong bao gio", "luc nao cung")):
        return "cognitive_reframe"
    if any(k in normalized for k in ("lam sao", "nen lam gi", "phai lam gi", "ke hoach")):
        return "problem_solving"
    if any(k in normalized for k in ("co phai", "dung khong", "toi sai", "yeu duoi")):
        return "reassurance"
    return "venting"


def build_case_from_raw(row: dict[str, str]) -> dict[str, Any]:
    question = str(row.get("question") or "").strip()
    response = str(row.get("response") or "").strip()
    topics, emotions, patterns, risks = _tags_from_text(f"{question} {response}")
    interaction_need = infer_interaction_need(question, response)
    primary_problem = question[:360]
    goal = "giúp người dùng gọi tên vấn đề, giảm tự trách và chọn một bước nhỏ an toàn"
    if interaction_need == "grounding":
        goal = "giúp người dùng hạ cường độ căng thẳng trước khi phân tích"
    elif interaction_need == "problem_solving":
        goal = "giúp người dùng tách vấn đề thành một bước có thể làm ngay"
    elif interaction_need == "safety":
        goal = "ưu tiên an toàn tức thời và kết nối hỗ trợ phù hợp"

    return {
        "raw_case_id": str(row.get("id") or row.get("raw_case_id") or "").strip() or None,
        "language": "vi" if re.search(r"[ăâđêôơưáàảãạ]", question.lower()) else "en",
        "user_context": question[:1200],
        "primary_problem": primary_problem,
        "topic_tags": topics[:8],
        "emotional_state_tags": emotions[:8],
        "interaction_need": interaction_need,
        "cognitive_pattern_tags": patterns[:8],
        "counseling_goal": goal,
        "recommended_approach": "validation + plain-language formulation + one small agency step",
        "intervention_steps": [
            "phản chiếu ngắn cảm xúc chính",
            "gọi tên vòng lặp đang làm người dùng kẹt bằng ngôn ngữ đời thường",
            "đề xuất một bước nhỏ có thể thử ngay",
        ],
        "reflection_questions": [
            "Trong chuyện này, điều gì là sự kiện chắc chắn, và điều gì là phần não đang suy diễn thêm?"
        ],
        "do_say": [
            "Mình thấy chuyện này không chỉ là mệt, mà còn là cảm giác bị kẹt và mất quyền điều khiển."
        ],
        "do_not_say": [
            "Bạn bị rối loạn tâm lý.",
            "Cứ tích cực lên.",
            "Đây chắc chắn là chẩn đoán của bạn.",
        ],
        "risk_flags": risks[:8],
        "source_response_summary": response[:650],
        "safety_review_status": "needs_review" if risks else "pending",
        "quality_score": 0.55,
    }


def _embedding_text(case: dict[str, Any]) -> str:
    return " ".join(
        str(case.get(key) or "")
        for key in ("user_context", "primary_problem", "counseling_goal", "recommended_approach")
    )[:900]


def _embed_batch(texts: list[str], client) -> list[list[float]]:
    resp = client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def _stable_case_id(raw_case_id: str | None, user_context: str) -> str:
    seed = raw_case_id or hashlib.sha256(user_context.encode("utf-8")).hexdigest()
    return hashlib.sha256(f"advisor-case:{seed}".encode("utf-8")).hexdigest()


def backfill(*, dry_run: bool = False, limit: int | None = None, batch_size: int = 100) -> None:
    from sqlalchemy import text

    from app.core.config import get_settings
    from app.services.db.session import get_engine, get_session_factory

    settings = get_settings()
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        logger.error("Requires PostgreSQL with pgvector. Got: %s", engine.dialect.name)
        sys.exit(1)

    factory = get_session_factory()
    db = factory()
    try:
        rows = db.execute(
            text(
                """
                SELECT id, question, response
                FROM app.counseling_knowledge ck
                WHERE NOT EXISTS (
                    SELECT 1 FROM app.advisor_case_library acl
                    WHERE acl.raw_case_id = ck.id
                )
                ORDER BY created_at
                LIMIT :limit
                """
            ),
            {"limit": int(limit or 500)},
        ).mappings().all()
    finally:
        db.close()

    cases = [build_case_from_raw(dict(row)) for row in rows]
    logger.info("Prepared %d cases.", len(cases))
    if dry_run:
        for case in cases[:3]:
            logger.info("[dry-run] %s", json.dumps(case, ensure_ascii=False)[:1000])
        return

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY is required for embeddings when writing backfill rows.")
        sys.exit(1)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
    db = factory()
    try:
        inserted = 0
        for i in range(0, len(cases), batch_size):
            batch = cases[i : i + batch_size]
            embeddings = _embed_batch([_embedding_text(case) for case in batch], client)
            for case, embedding in zip(batch, embeddings):
                vec_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
                case_id = _stable_case_id(case.get("raw_case_id"), str(case["user_context"]))[:32]
                db.execute(
                    text(
                        f"""
                        INSERT INTO app.advisor_case_library (
                            case_id, raw_case_id, language, user_context, primary_problem,
                            topic_tags, emotional_state_tags, interaction_need, cognitive_pattern_tags,
                            counseling_goal, recommended_approach, intervention_steps,
                            reflection_questions, do_say, do_not_say, risk_flags,
                            source_response_summary, safety_review_status, quality_score, embedding
                        )
                        VALUES (
                            gen_random_uuid(), :raw_case_id, :language, :user_context, :primary_problem,
                            :topic_tags, :emotional_state_tags, :interaction_need, :cognitive_pattern_tags,
                            :counseling_goal, :recommended_approach, CAST(:intervention_steps AS jsonb),
                            CAST(:reflection_questions AS jsonb), CAST(:do_say AS jsonb), CAST(:do_not_say AS jsonb), :risk_flags,
                            :source_response_summary, :safety_review_status, :quality_score, '{vec_str}'::vector
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        **case,
                        "case_id": case_id,
                        "intervention_steps": json.dumps(case["intervention_steps"], ensure_ascii=False),
                        "reflection_questions": json.dumps(case["reflection_questions"], ensure_ascii=False),
                        "do_say": json.dumps(case["do_say"], ensure_ascii=False),
                        "do_not_say": json.dumps(case["do_not_say"], ensure_ascii=False),
                    },
                )
                inserted += 1
            db.commit()
            logger.info("Inserted batch %d (%d rows total).", i // batch_size + 1, inserted)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill advisor_case_library from counseling_knowledge.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    backfill(dry_run=args.dry_run, limit=args.limit, batch_size=args.batch_size)
