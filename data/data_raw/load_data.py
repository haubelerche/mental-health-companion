"""
load_disorders_to_neo4j.py
Nạp :DisorderCategory và :Disorder từ CSV vào Neo4j AuraDB.
Tương đương với load_disorders_from_csv.cypher nhưng dùng Python driver
vì AuraDB không cho đọc file:/// từ filesystem local.

Usage:
    python scripts/load_disorders_to_neo4j.py
"""

import csv
import sys
import re
import unicodedata
from pathlib import Path

from neo4j import GraphDatabase

# Repo root so `scripts.config` (Aura user / DB name resolution) is importable.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

# ── Config ──────────────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).resolve().parent
CATS_CSV   = BASE_DIR / "data_raw" / "disorder_categories.csv"
DIS_CSV    = BASE_DIR / "data_raw" / "disorders.csv"

# ── Helpers ──────────────────────────────────────────────────────────────────

# Normalize legacy taxonomy slugs (v2/raw CSV) into schema v3 canonical slugs.
CATEGORY_SLUG_ALIASES = {
    "mood_disorders": "depressive_disorders",
    "disruptive_impulse_conduct_disorders": "disruptive_impulse_conduct",
}

def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def to_slug(value: str) -> str:
    """
    Convert a name into an ASCII snake_case slug.
    This matches the v3 convention used across the graph.
    """
    if value is None:
        value = ""
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value

def canonical_category_slug(value: str) -> str:
    slug = (value or "").strip()
    return CATEGORY_SLUG_ALIASES.get(slug, slug)

def required(row: dict, key: str, context: str) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"Missing required field '{key}' in {context}: {row}")
    return value


# ── Cypher templates ─────────────────────────────────────────────────────────

MERGE_CATEGORY = """
MERGE (c:DisorderCategory {slug: $slug})
  ON CREATE SET c.name_vi = $name_vi, c.name_en = $name_en
  ON MATCH  SET c.name_vi = coalesce(c.name_vi, $name_vi),
               c.name_en = coalesce(c.name_en, $name_en)
"""

MERGE_SUBCATEGORY_OF = """
MATCH (child:DisorderCategory  {slug: $child_slug})
MATCH (parent:DisorderCategory {slug: $parent_slug})
MERGE (child)-[:SUBCATEGORY_OF]->(parent)
"""

MERGE_DISORDER = """
MERGE (d:Disorder {slug: $slug})
  ON CREATE SET d.icd_code   = $icd_code,
               d.name_vi    = $name_vi,
               d.name_en    = $name_en,
               d.dsm5_code  = $dsm5_code,
               d.definition = $definition
  ON MATCH  SET d.icd_code   = coalesce(d.icd_code, $icd_code),
               d.name_vi    = coalesce(d.name_vi, $name_vi),
               d.name_en    = coalesce(d.name_en, $name_en),
               d.dsm5_code  = coalesce(d.dsm5_code, $dsm5_code),
               d.definition = coalesce(d.definition, $definition)
"""

MERGE_IN_DISORDER_CATEGORY = """
MATCH (d:Disorder          {slug: $slug})
MATCH (c:DisorderCategory  {slug: $category_slug})
MERGE (d)-[:IN_DISORDER_CATEGORY]->(c)
"""

# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
        print("[ERROR] Thieu bien moi truong NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD (.env)")
        sys.exit(1)

    cats = read_csv(CATS_CSV)
    disorders = read_csv(DIS_CSV)

    print(f"[INFO] Doc {len(cats)} categories, {len(disorders)} disorders")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session(database=NEO4J_DATABASE) as session:

        # 1. Tạo / cập nhật DisorderCategory
        print("\n-- Buoc 1: MERGE DisorderCategory --")
        for row in cats:
            raw_slug = required(row, "slug", "category row")
            slug = canonical_category_slug(raw_slug)
            session.run(
                MERGE_CATEGORY,
                slug=slug,
                name_vi=required(row, "name_vi", f"category '{raw_slug}'"),
                name_en=required(row, "name_en", f"category '{raw_slug}'"),
            )
        print(f"   [OK] {len(cats)} categories da MERGE")

        # 2. Quan hệ cha-con giữa categories
        print("-- Buoc 2: MERGE SUBCATEGORY_OF --")
        linked = 0
        for row in cats:
            child_slug = canonical_category_slug(required(row, "slug", "category row"))
            ps = canonical_category_slug((row.get("parent_slug", "")).strip())
            if ps:
                session.run(MERGE_SUBCATEGORY_OF,
                            child_slug=child_slug, parent_slug=ps)
                linked += 1
        print(f"   [OK] {linked} quan he SUBCATEGORY_OF da MERGE")

        # 3. Tạo / cập nhật Disorder
        print("-- Buoc 3: MERGE Disorder --")
        for row in disorders:
            # Prefer explicit slug if present; otherwise derive from English name.
            slug = (row.get("slug") or "").strip()
            if not slug:
                slug = to_slug(row.get("name_en", ""))
            if not slug:
                raise ValueError(f"Cannot derive slug for disorder row: {row}")
            category_slug = canonical_category_slug(
                required(row, "category_slug", f"disorder '{slug}'")
            )
            session.run(MERGE_DISORDER,
                        slug      = slug,
                        icd_code  = required(row, "icd_code", f"disorder '{slug}'"),
                        name_vi   = required(row, "name_vi", f"disorder '{slug}'"),
                        name_en   = required(row, "name_en", f"disorder '{slug}'"),
                        dsm5_code = row.get("dsm5_code", ""),
                        definition= row.get("definition", ""))
            session.run(MERGE_IN_DISORDER_CATEGORY, slug=slug, category_slug=category_slug)
        print(f"   [OK] {len(disorders)} disorders da MERGE")

        # 4. Da MERGE IN_DISORDER_CATEGORY trong Buoc 3 de tranh loop lap lai
        print("-- Buoc 4: SKIP MERGE IN_DISORDER_CATEGORY (da xu ly o Buoc 3) --")
        print(f"   [OK] {len(disorders)} quan he IN_DISORDER_CATEGORY da duoc xu ly")

        # 5. Sanity check
        print("-- Buoc 5: Sanity check --")
        r_dis = session.run("MATCH (d:Disorder) RETURN count(d) AS n").single()
        r_cat = session.run("MATCH (c:DisorderCategory) RETURN count(c) AS n").single()
        print(f"   [STAT] Disorders trong DB : {r_dis['n']}")
        print(f"   [STAT] Categories trong DB: {r_cat['n']}")

        # Cảnh báo disorder thiếu / thừa category
        orphans = session.run("""
            MATCH (d:Disorder)
            WITH d, size([(d)-[:IN_DISORDER_CATEGORY]->() | 1]) AS n
            WHERE n <> 1
            RETURN d.slug AS slug, d.icd_code AS icd_code, n
        """).data()
        if orphans:
            print(f"   [WARN] {len(orphans)} disorder khong IN_DISORDER_CATEGORY dung 1 category:")
            for o in orphans:
                print(f"      {o['slug']} ({o['icd_code']}) -> {o['n']} links")
        else:
            print("   [OK] Moi disorder deu IN_DISORDER_CATEGORY dung 1 category")

    driver.close()
    print("\n[DONE] Nap du lieu hoan tat!")


if __name__ == "__main__":
    run()
