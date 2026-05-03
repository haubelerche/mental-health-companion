"""Seed counseling_knowledge table from docs/csv/mental_health.csv.

Usage:
    python backend/scripts/seed_counseling_knowledge.py [--dry-run] [--limit N]

Requires PostgreSQL with pgvector. Skips gracefully on SQLite.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

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

_CSV_PATH = _REPO / "docs" / "csv" / "mental_health.csv"
_EMBED_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100
_SOURCE = "mental_health_v1"
_QUARANTINE_LOG = _BACKEND / "data" / "seed_quarantine.log"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _content_hash(question: str, response: str) -> str:
    return hashlib.sha256(f"{question}\n{response}".encode("utf-8")).hexdigest()


def _load_csv(limit: int | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            question = (row.get("Context") or row.get("Question") or "").strip()
            response = (row.get("Response") or row.get("Answer") or "").strip()
            if question and response:
                rows.append({"question": question, "response": response, "content_hash": _content_hash(question, response)})
            if limit and len(rows) >= limit:
                break
    return rows


def _get_existing_hashes(db) -> set[str]:
    from sqlalchemy import text
    result = db.execute(
        text("SELECT md5(question || '\n' || response) AS h FROM counseling_knowledge WHERE source LIKE :src"),
        {"src": f"{_SOURCE}%"},
    )
    return {row.h for row in result}


def _is_low_quality(row: dict[str, str]) -> tuple[bool, str]:
    question = row["question"]
    response = row["response"]
    if len(question) < 12 or len(response) < 20:
        return True, "too_short"
    if "..." in question and "..." in response:
        return True, "ocr_artifact"
    return False, ""


def _log_quarantine(reason: str, row: dict[str, str]) -> None:
    _QUARANTINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(_QUARANTINE_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat()} | {reason} | {row['question'][:120]}\n")


def _embed_batch(texts: list[str], client) -> list[list[float]]:
    resp = client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def seed(dry_run: bool = False, limit: int | None = None) -> None:
    from app.core.config import get_settings
    from app.services.db.session import get_engine, get_session_factory

    settings = get_settings()
    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY not set — cannot compute embeddings.")
        sys.exit(1)

    engine = get_engine()
    if engine.dialect.name != "postgresql":
        logger.error("Requires PostgreSQL with pgvector. Got: %s", engine.dialect.name)
        sys.exit(1)

    rows = _load_csv(limit)
    logger.info("Loaded %d rows from CSV.", len(rows))

    if dry_run:
        logger.info("[dry-run] Would embed and insert up to %d rows. Exiting.", len(rows))
        return

    from openai import OpenAI
    from sqlalchemy import text

    client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
    factory = get_session_factory()
    db = factory()

    try:
        existing = _get_existing_hashes(db)
        logger.info("Already in DB: %d rows (by md5 hash).", len(existing))

        quality_rows: list[dict[str, str]] = []
        for row in rows:
            bad, reason = _is_low_quality(row)
            if bad:
                _log_quarantine(reason, row)
                continue
            quality_rows.append(row)

        new_rows = [r for r in quality_rows if _md5(f"{r['question']}\n{r['response']}") not in existing]
        logger.info("New rows to insert: %d.", len(new_rows))

        if not new_rows:
            logger.info("Nothing to do.")
            return

        inserted = 0
        for i in range(0, len(new_rows), _BATCH_SIZE):
            batch = new_rows[i : i + _BATCH_SIZE]
            texts = [r["question"][:512] for r in batch]
            embeddings = _embed_batch(texts, client)

            for row, emb in zip(batch, embeddings):
                vec_str = "[" + ",".join(f"{x:.8f}" for x in emb) + "]"
                # psycopg3 treats ':' as a parameter prefix, so we cannot write
                # ':emb::vector'. Instead embed the vector literal directly in
                # the SQL string and bind only the scalar params.
                sql = (
                    "INSERT INTO counseling_knowledge (id, question, response, source, embedding) "
                    f"VALUES (:id, :q, :r, :src, '{vec_str}'::vector) "
                    "ON CONFLICT (id) DO NOTHING"
                )
                db.execute(
                    text(sql),
                    {
                        "id": str(uuid.uuid4()),
                        "q": row["question"],
                        "r": row["response"],
                        "src": f"{_SOURCE}:{datetime.now(timezone.utc).date().isoformat()}",
                    },
                )
                inserted += 1

            db.commit()
            logger.info("Inserted batch %d/%d (%d rows so far).", i // _BATCH_SIZE + 1, -(-len(new_rows) // _BATCH_SIZE), inserted)

        logger.info("Done. Total inserted: %d rows.", inserted)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed counseling_knowledge table.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process.")
    args = parser.parse_args()
    seed(dry_run=args.dry_run, limit=args.limit)
