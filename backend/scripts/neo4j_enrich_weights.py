"""Strengthen existing Neo4j edge weights from counseling Q&A co-occurrence.

Scans docs/csv/mental_health.csv for co-occurrences of existing Neo4j entity slugs
(Symptom, CognitiveDistortion, CopingAction) and updates CO_OCCURS_WITH.weight
and TARGETS_SYMPTOM.strength accordingly.

Does NOT create new nodes or relationship types.

Usage:
    python backend/scripts/neo4j_enrich_weights.py --dry-run   # print report only
    python backend/scripts/neo4j_enrich_weights.py --apply     # write to Neo4j
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import unicodedata
from collections import defaultdict
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
_MAX_DELTA = 0.10  # cap per-edge delta to protect DSM-5 authored weights


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    no_accent = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9\s_]", " ", no_accent)


def _load_entity_keywords(driver) -> dict[str, list[tuple[str, str]]]:
    """Query Neo4j for entity slugs + name_en, return keyword→(slug, label) map."""
    keyword_map: dict[str, list[tuple[str, str]]] = defaultdict(list)

    queries = [
        ("Symptom", "MATCH (n:Symptom) RETURN n.slug AS slug, n.name_en AS name_en"),
        ("CognitiveDistortion", "MATCH (n:CognitiveDistortion) RETURN n.slug AS slug, n.name_en AS name_en"),
        ("CopingAction", "MATCH (n:CopingAction) RETURN n.action_id AS slug, n.name_en AS name_en"),
    ]

    with driver.session() as session:
        for label, query in queries:
            result = session.run(query)
            for record in result:
                slug = str(record.get("slug") or "").strip()
                name_en = str(record.get("name_en") or "").strip()
                if slug:
                    for kw in [slug.replace("_", " "), slug]:
                        keyword_map[_normalize(kw)].append((slug, label))
                if name_en:
                    keyword_map[_normalize(name_en)].append((slug, label))

    logger.info(
        "Loaded %d keyword entries from Neo4j.",
        sum(len(v) for v in keyword_map.values()),
    )
    return dict(keyword_map)


def _scan_corpus(
    keyword_map: dict[str, list[tuple[str, str]]],
) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str, str], int], int]:
    """Scan Q&A corpus and count co-occurrences.

    Returns:
        symptom_cooccur: {(slug_a, slug_b): count} for Symptom pairs in questions
        coping_targets: {(coping_slug, symptom_slug, 'TARGETS'): count} for response→question links
        total_pairs: total Q&A pairs processed
    """
    symptom_cooccur: dict[tuple[str, str], int] = defaultdict(int)
    coping_targets: dict[tuple[str, str, str], int] = defaultdict(int)
    total = 0

    with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            question = _normalize(row.get("Context") or row.get("Question") or "")
            response = _normalize(row.get("Response") or row.get("Answer") or "")
            if not question or not response:
                continue
            total += 1

            # Find symptoms in question
            q_symptoms: list[str] = []
            for kw, entries in keyword_map.items():
                if kw in question:
                    for slug, label in entries:
                        if label == "Symptom" and slug not in q_symptoms:
                            q_symptoms.append(slug)

            # CO_OCCURS_WITH: symptom pairs from question
            for i, a in enumerate(q_symptoms):
                for b in q_symptoms[i + 1:]:
                    key = (min(a, b), max(a, b))
                    symptom_cooccur[key] += 1

            # Find coping actions in response → link to question symptoms
            for kw, entries in keyword_map.items():
                if kw in response:
                    for coping_slug, label in entries:
                        if label == "CopingAction":
                            for sym_slug in q_symptoms:
                                coping_targets[(coping_slug, sym_slug, "TARGETS")] += 1

    return dict(symptom_cooccur), dict(coping_targets), total


def _apply_updates(
    driver,
    symptom_cooccur: dict[tuple[str, str], int],
    coping_targets: dict[tuple[str, str, str], int],
    total_pairs: int,
) -> None:
    with driver.session() as session:
        for (a, b), count in symptom_cooccur.items():
            delta = min(_MAX_DELTA, count / total_pairs)
            session.run(
                """
                MATCH (a:Symptom {slug: $a})-[r:CO_OCCURS_WITH]-(b:Symptom {slug: $b})
                SET r.weight = CASE WHEN r.weight + $delta > 1.0 THEN 1.0
                                    ELSE round(r.weight + $delta, 4) END,
                    r.evidence_count = coalesce(r.evidence_count, 0) + $count,
                    r.last_updated = datetime()
                """,
                {"a": a, "b": b, "delta": delta, "count": count},
            )

        for (coping, symptom, _), count in coping_targets.items():
            delta = min(_MAX_DELTA, count / total_pairs)
            session.run(
                """
                MATCH (c:CopingAction {action_id: $coping})-[r:TARGETS_SYMPTOM]->(s:Symptom {slug: $symptom})
                SET r.strength = CASE WHEN r.strength + $delta > 1.0 THEN 1.0
                                      ELSE round(r.strength + $delta, 4) END,
                    r.evidence_count = coalesce(r.evidence_count, 0) + $count,
                    r.last_updated = datetime()
                """,
                {"coping": coping, "symptom": symptom, "delta": delta, "count": count},
            )


def run(dry_run: bool) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.neo4j_uri:
        logger.error("NEO4J_URI not configured.")
        sys.exit(1)

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    try:
        keyword_map = _load_entity_keywords(driver)
        symptom_cooccur, coping_targets, total = _scan_corpus(keyword_map)

        logger.info("Scanned %d Q&A pairs.", total)
        logger.info("Symptom CO_OCCURS_WITH updates: %d edges", len(symptom_cooccur))
        logger.info("CopingAction TARGETS_SYMPTOM updates: %d edges", len(coping_targets))

        if symptom_cooccur:
            top = sorted(symptom_cooccur.items(), key=lambda x: x[1], reverse=True)[:5]
            for (a, b), cnt in top:
                logger.info("  CO_OCCURS_WITH: %s ↔ %s = %d times (delta +%.4f)", a, b, cnt, min(_MAX_DELTA, cnt / total))

        if dry_run:
            logger.info("[dry-run] No changes written to Neo4j.")
            return

        _apply_updates(driver, symptom_cooccur, coping_targets, total)
        logger.info("Done. Neo4j edge weights updated.")
    finally:
        driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Neo4j edge weights from Q&A co-occurrence.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Print report, no writes.")
    group.add_argument("--apply", action="store_true", help="Apply updates to Neo4j.")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
