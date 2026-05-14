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
ADVISOR_JSONL_STATUS_ALLOWED = {"approved", "rejected", "needs_review"}
ADVISOR_JSONL_DOMAIN_PATHS = {
    "empathy": _REPO / "data" / "data-advisors" / "empathy" / "empathy.jsonl",
    "cbt_pattern": _REPO / "data" / "data-advisors" / "cbtpattern" / "cbt-pattern.jsonl",
    "reflection": _REPO / "data" / "data-advisors" / "reflection" / "reflection.jsonl",
    "strategy": _REPO / "data" / "data-advisors" / "strategy" / "strategy.jsonl",
    "safety": _REPO / "data" / "data-advisors" / "safety" / "safety.jsonl",
    "relevance": _REPO / "data" / "data-advisors" / "relevance" / "relevance.jsonl",
    "nutrition": _REPO / "data" / "data-advisors" / "nutrition" / "nutrition.jsonl",
}
ADVISOR_DOMAIN_RUNTIME_IDS = {
    "empathy": "empathy_advisor",
    "cbt_pattern": "cbt_pattern_advisor",
    "reflection": "reflection_advisor",
    "strategy": "strategy_resource_advisor",
    "safety": "counseling_advisor",
    "relevance": "relevance_naturalness_critic",
    "nutrition": "nutrition_support_advisor",
}


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.replace("Ä‘", "d").lower()).strip()


def validate_advisor_jsonl_record(raw: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate advisor JSONL before staging or promotion."""
    errors: list[str] = []
    quality = raw.get("quality_flags") if isinstance(raw.get("quality_flags"), dict) else {}
    if quality.get("no_final_text") is not True:
        errors.append("quality_flags.no_final_text must be true")
    if raw.get("display_allowed") is not False:
        errors.append("display_allowed must be false")
    if str(raw.get("locale") or "").strip() != "vi":
        errors.append("locale must be vi")
    status = str(raw.get("safety_review_status") or raw.get("review_status") or "").strip()
    if status not in ADVISOR_JSONL_STATUS_ALLOWED:
        errors.append("safety_review_status must be approved, rejected, or needs_review")
    forbidden_keys = {"final_text", "assistant_response", "reply", "message_to_user", "user_message_text"}
    present = sorted(forbidden_keys & set(raw))
    if present:
        errors.append(f"forbidden user-facing fields present: {', '.join(present)}")
    return not errors, errors


def _iter_tolerant_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    idx = 0
    size = len(text)
    rows: list[dict[str, Any]] = []
    while idx < size:
        while idx < size and text[idx] in " \t\r\n,[]":
            idx += 1
        if idx >= size:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        idx = end
        if isinstance(obj, dict):
            rows.append(obj)
        elif isinstance(obj, list):
            rows.extend(item for item in obj if isinstance(item, dict))
    return rows


def iter_validated_advisor_jsonl(domain_id: str) -> list[tuple[dict[str, Any], list[str]]]:
    path = ADVISOR_JSONL_DOMAIN_PATHS[domain_id]
    rows: list[tuple[dict[str, Any], list[str]]] = []
    parsed = _iter_tolerant_json_objects(path.read_text(encoding="utf-8"))
    if not parsed:
        return [({"file": str(path)}, ["no json objects found"])]
    for raw in parsed:
        valid, errors = validate_advisor_jsonl_record(raw)
        rows.append((raw, [] if valid else errors))
    return rows


def stage_advisor_jsonl(*, domain_id: str, dry_run: bool = False, imported_by: str | None = None) -> None:
    from sqlalchemy import text

    from app.services.db.session import get_engine, get_session_factory

    if domain_id not in ADVISOR_JSONL_DOMAIN_PATHS:
        raise ValueError(f"unknown advisor domain: {domain_id}")
    runtime_advisor_id = ADVISOR_DOMAIN_RUNTIME_IDS.get(domain_id)
    rows = iter_validated_advisor_jsonl(domain_id)
    valid_count = sum(1 for _raw, errors in rows if not errors)
    invalid_count = len(rows) - valid_count
    logger.info("Validated %d rows for %s: valid=%d invalid=%d", len(rows), domain_id, valid_count, invalid_count)
    if dry_run:
        for raw, errors in rows[:5]:
            logger.info(
                "[dry-run:%s] item_id=%s status=%s errors=%s",
                domain_id,
                raw.get("item_id"),
                "valid" if not errors else "invalid",
                errors,
            )
        return

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        logger.error("Requires PostgreSQL. Got: %s", engine.dialect.name)
        sys.exit(1)

    factory = get_session_factory()
    db = factory()
    try:
        import_id = db.execute(
            text(
                """
                INSERT INTO app.advisor_dataset_imports (
                    file_name, domain_id, runtime_advisor_id, row_count, imported_by, status, metadata
                )
                VALUES (
                    :file_name, :domain_id, :runtime_advisor_id, :row_count, :imported_by,
                    'validated', CAST(:metadata AS jsonb)
                )
                RETURNING import_id
                """
            ),
            {
                "file_name": str(ADVISOR_JSONL_DOMAIN_PATHS[domain_id].relative_to(_REPO)),
                "domain_id": domain_id,
                "runtime_advisor_id": runtime_advisor_id,
                "row_count": len(rows),
                "imported_by": imported_by,
                "metadata": json.dumps({"valid_count": valid_count, "invalid_count": invalid_count}, ensure_ascii=False),
            },
        ).scalar_one()
        for raw, errors in rows:
            db.execute(
                text(
                    """
                    INSERT INTO app.advisor_dataset_staging (
                        import_id, domain_id, runtime_advisor_id, raw_payload,
                        normalized_question, normalized_response, validation_status, error_message
                    )
                    VALUES (
                        :import_id, :domain_id, :runtime_advisor_id, CAST(:raw_payload AS jsonb),
                        :normalized_question, :normalized_response, :validation_status, :error_message
                    )
                    """
                ),
                {
                    "import_id": import_id,
                    "domain_id": domain_id,
                    "runtime_advisor_id": runtime_advisor_id,
                    "raw_payload": json.dumps(raw, ensure_ascii=False),
                    "normalized_question": str(raw.get("user_scenario") or raw.get("trigger_keywords") or "")[:1200],
                    "normalized_response": str(raw.get("summary") or raw.get("content") or "")[:1200],
                    "validation_status": "valid" if not errors else "invalid",
                    "error_message": "; ".join(errors)[:1000] if errors else None,
                },
            )
        db.commit()
        logger.info("Staged advisor import %s for domain %s.", import_id, domain_id)
    finally:
        db.close()


def _case_from_advisor_payload(raw: dict[str, Any], *, domain_id: str) -> dict[str, Any]:
    def list_value(key: str) -> list[str]:
        value = raw.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item or "").strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    item_id = str(raw.get("item_id") or "").strip()
    summary = str(raw.get("summary") or raw.get("content") or raw.get("title") or "").strip()
    user_context = str(raw.get("user_scenario") or raw.get("soft_interpretation") or summary or item_id).strip()
    return {
        "raw_case_id": item_id,
        "language": "vi",
        "user_context": user_context[:1200],
        "primary_problem": str(raw.get("user_scenario") or raw.get("title") or summary)[:500],
        "topic_tags": list_value("tags")[:12],
        "emotional_state_tags": list_value("emotional_state")[:12],
        "interaction_need": None,
        "cognitive_pattern_tags": [str(raw.get("pattern_family"))] if raw.get("pattern_family") else [],
        "counseling_goal": summary[:500],
        "recommended_approach": str(raw.get("safe_wording_hint") or raw.get("soft_interpretation") or raw.get("friend_usage_rule") or "")[:500],
        "intervention_steps": (list_value("advisor_advice_to_friend") + list_value("suggested_response_moves"))[:6],
        "reflection_questions": list_value("reflection_questions")[:4],
        "do_say": list_value("safe_wording_hint")[:6],
        "do_not_say": (list_value("forbidden_moves") + list_value("forbidden_clinical_wording"))[:8],
        "risk_flags": list_value("contraindications")[:8],
        "source_response_summary": summary[:700],
        "safety_review_status": "approved",
        "quality_score": 0.65,
        "source": "advisor_jsonl",
        "advisor_domains": [domain_id],
        "safety_constraints": {"no_diagnosis": True, "no_raw_response_copy": True, "no_final_text": True},
        "metadata": {"processor": "advisor_jsonl_promote.v1", "knowledge_type": raw.get("knowledge_type")},
    }


def promote_staged_advisor_jsonl(*, import_id: str, dry_run: bool = False) -> None:
    from sqlalchemy import text

    from app.services.db.session import get_engine, get_session_factory

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        logger.error("Requires PostgreSQL. Got: %s", engine.dialect.name)
        sys.exit(1)

    factory = get_session_factory()
    db = factory()
    try:
        rows = db.execute(
            text(
                """
                SELECT domain_id, runtime_advisor_id, raw_payload
                FROM app.advisor_dataset_staging
                WHERE import_id = :import_id
                  AND validation_status = 'valid'
                  AND COALESCE(raw_payload->>'safety_review_status', raw_payload->>'review_status') = 'approved'
                """
            ),
            {"import_id": import_id},
        ).mappings().all()
        logger.info("Promotion candidate rows for import %s: %d", import_id, len(rows))
        if dry_run:
            for row in rows[:5]:
                raw = row["raw_payload"]
                logger.info("[dry-run:promote] item_id=%s domain=%s", raw.get("item_id"), row["domain_id"])
            return
        promoted = 0
        for row in rows:
            raw = row["raw_payload"]
            domain_id = str(row["domain_id"])
            runtime_advisor_id = str(row["runtime_advisor_id"] or ADVISOR_DOMAIN_RUNTIME_IDS.get(domain_id) or "")
            case = _case_from_advisor_payload(raw, domain_id=domain_id)
            db.execute(
                text(
                    """
                    INSERT INTO app.advisor_case_library (
                        raw_case_id, language, user_context, primary_problem,
                        topic_tags, emotional_state_tags, interaction_need, cognitive_pattern_tags,
                        counseling_goal, recommended_approach, intervention_steps,
                        reflection_questions, do_say, do_not_say, risk_flags,
                        source_response_summary, safety_review_status, quality_score,
                        source, advisor_domains, safety_constraints, metadata
                    )
                    VALUES (
                        :raw_case_id, :language, :user_context, :primary_problem,
                        :topic_tags, :emotional_state_tags, :interaction_need, :cognitive_pattern_tags,
                        :counseling_goal, :recommended_approach, CAST(:intervention_steps AS jsonb),
                        CAST(:reflection_questions AS jsonb), CAST(:do_say AS jsonb), CAST(:do_not_say AS jsonb), :risk_flags,
                        :source_response_summary, :safety_review_status, :quality_score,
                        :source, :advisor_domains, CAST(:safety_constraints AS jsonb), CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    **case,
                    "intervention_steps": json.dumps(case["intervention_steps"], ensure_ascii=False),
                    "reflection_questions": json.dumps(case["reflection_questions"], ensure_ascii=False),
                    "do_say": json.dumps(case["do_say"], ensure_ascii=False),
                    "do_not_say": json.dumps(case["do_not_say"], ensure_ascii=False),
                    "safety_constraints": json.dumps(case["safety_constraints"], ensure_ascii=False),
                    "metadata": json.dumps(case["metadata"], ensure_ascii=False),
                },
            )
            case_id = db.execute(
                text("SELECT case_id FROM app.advisor_case_library WHERE raw_case_id = :raw_case_id LIMIT 1"),
                {"raw_case_id": case["raw_case_id"]},
            ).scalar_one_or_none()
            if case_id:
                db.execute(
                    text(
                        """
                        INSERT INTO app.advisor_case_domain_map(case_id, domain_id, runtime_advisor_id)
                        VALUES (:case_id, :domain_id, :runtime_advisor_id)
                        ON CONFLICT (case_id, domain_id) DO UPDATE SET
                            runtime_advisor_id = EXCLUDED.runtime_advisor_id
                        """
                    ),
                    {"case_id": case_id, "domain_id": domain_id, "runtime_advisor_id": runtime_advisor_id},
                )
                promoted += 1
        db.execute(
            text("UPDATE app.advisor_dataset_imports SET status = 'promoted', updated_at = now() WHERE import_id = :import_id"),
            {"import_id": import_id},
        )
        db.commit()
        logger.info("Promoted %d staged advisor rows.", promoted)
    finally:
        db.close()


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


def infer_advisor_domains(interaction_need: str, patterns: list[str], topics: list[str], risks: list[str]) -> list[str]:
    domains: list[str] = []
    if risks or interaction_need == "safety":
        domains.append("safety")
    if patterns or interaction_need in {"cognitive_reframe", "reassurance"}:
        domains.append("cbt_pattern")
    if interaction_need in {"problem_solving", "grounding"}:
        domains.append("strategy")
    if "sleep_energy" in topics:
        domains.append("nutrition")
    domains.append("empathy")
    out: list[str] = []
    for item in domains:
        if item not in out:
            out.append(item)
    return out[:5]


def build_case_from_raw(row: dict[str, str]) -> dict[str, Any]:
    question = str(row.get("question") or "").strip()
    response = str(row.get("response") or "").strip()
    topics, emotions, patterns, risks = _tags_from_text(f"{question} {response}")
    interaction_need = infer_interaction_need(question, response)
    advisor_domains = infer_advisor_domains(interaction_need, patterns, topics, risks)
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
        "source": str(row.get("source") or "counseling_knowledge").strip() or "counseling_knowledge",
        "advisor_domains": advisor_domains,
        "safety_constraints": {"no_diagnosis": True, "no_raw_response_copy": True},
        "metadata": {"processor": "backfill_advisor_case_library.v1"},
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
                            source_response_summary, safety_review_status, quality_score,
                            source, advisor_domains, safety_constraints, metadata, embedding
                        )
                        VALUES (
                            gen_random_uuid(), :raw_case_id, :language, :user_context, :primary_problem,
                            :topic_tags, :emotional_state_tags, :interaction_need, :cognitive_pattern_tags,
                            :counseling_goal, :recommended_approach, CAST(:intervention_steps AS jsonb),
                            CAST(:reflection_questions AS jsonb), CAST(:do_say AS jsonb), CAST(:do_not_say AS jsonb), :risk_flags,
                            :source_response_summary, :safety_review_status, :quality_score,
                            :source, :advisor_domains, CAST(:safety_constraints AS jsonb), CAST(:metadata AS jsonb), '{vec_str}'::vector
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
                        "safety_constraints": json.dumps(case["safety_constraints"], ensure_ascii=False),
                        "metadata": json.dumps(case["metadata"], ensure_ascii=False),
                    },
                )
                inserted += 1
            db.commit()
            logger.info("Inserted batch %d (%d rows total).", i // batch_size + 1, inserted)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill advisor_case_library from counseling_knowledge.")
    subparsers = parser.add_subparsers(dest="command")

    backfill_parser = subparsers.add_parser("backfill-raw", help="Backfill app.advisor_case_library from app.counseling_knowledge")
    backfill_parser.add_argument("--dry-run", action="store_true")
    backfill_parser.add_argument("--limit", type=int, default=100)
    backfill_parser.add_argument("--batch-size", type=int, default=100)

    stage_parser = subparsers.add_parser("stage-jsonl", help="Validate and stage advisor JSONL rows")
    stage_parser.add_argument("--domain", required=True, choices=sorted(ADVISOR_JSONL_DOMAIN_PATHS))
    stage_parser.add_argument("--dry-run", action="store_true")
    stage_parser.add_argument("--imported-by")

    promote_parser = subparsers.add_parser("promote-jsonl", help="Promote valid approved staged advisor JSONL rows")
    promote_parser.add_argument("--import-id", required=True)
    promote_parser.add_argument("--dry-run", action="store_true")

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.command == "stage-jsonl":
        stage_advisor_jsonl(domain_id=args.domain, dry_run=args.dry_run, imported_by=args.imported_by)
    elif args.command == "promote-jsonl":
        promote_staged_advisor_jsonl(import_id=args.import_id, dry_run=args.dry_run)
    else:
        backfill(dry_run=args.dry_run, limit=args.limit, batch_size=args.batch_size)
