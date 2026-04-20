"""
Kiểm tra kết nối Supabase Postgres (wire) + Neo4j + client Python.

Chạy từ thư mục gốc repo:
  python backend/tests/test_db.py

Biến môi trường (.env):
  DATABASE_URL      — Postgres (Supabase)
  NEO4J_URI, NEO4J_PASSWORD — Neo4j (NEO4J_USER hoặc NEO4J_USERNAME, tùy chọn NEO4J_DATABASE)
  SUPABASE_URL, SUPABASE_SECRET — client supabase-py (URL mặc định theo SUPABASE_PROJECT_ID trong scripts.config)
"""
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

import httpx

from scripts.config import (
    DATABASE_URL,
    NEO4J_DATABASE,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    SUPABASE_PROJECT_ID,
    SUPABASE_SECRET,
    SUPABASE_URL,
)
from src.database import get_client, test_connection


def _mask(s: str, keep: int = 4) -> str:
    if not s:
        return "(empty)"
    if len(s) <= keep * 2:
        return "(set)"
    return f"{s[:keep]}...{s[-keep:]}"


def check_postgres() -> None:
    if not DATABASE_URL:
        raise SystemExit(
            "[!] Missing DATABASE_URL in .env.\n"
            "    Supabase Dashboard -> Project Settings -> Database -> copy URI "
            "(transaction pooler :6543 or session/direct :5432)."
        )
    ok = test_connection()
    assert ok, "SELECT 1 không thành công"
    print("[+] PostgreSQL (Supabase): OK (SELECT 1)")


def check_neo4j() -> None:
    if not NEO4J_URI or not NEO4J_PASSWORD:
        raise SystemExit("[!] Missing NEO4J_URI or NEO4J_PASSWORD in .env.")
    try:
        from neo4j import GraphDatabase
    except ImportError as e:
        raise SystemExit("[!] Install neo4j: pip install neo4j\n" + str(e)) from e

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
        with driver.session(database=NEO4J_DATABASE) as session:
            rec = session.run("RETURN 1 AS n").single()
            assert rec and rec["n"] == 1
    finally:
        driver.close()
    print(f"[+] Neo4j: OK (bolt + RETURN 1, database={NEO4J_DATABASE})")


def check_supabase_client() -> None:
    client = get_client()
    assert client is not None
    print("[+] Supabase Python client: OK")


def check_rest_informational() -> None:
    """PostgREST có thể 503 trong lúc Postgres vẫn ổn — chỉ in trạng thái, không fail script."""
    health_url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SUPABASE_SECRET,
        "Authorization": f"Bearer {SUPABASE_SECRET}",
    }
    try:
        resp = httpx.get(health_url, headers=headers, timeout=15)
        print(f"[i] REST PostgREST /rest/v1/: HTTP {resp.status_code}")
        if resp.status_code == 503:
            print(
                "[i] HTTP 503 often means paused project, gateway maintenance, or transient "
                "PostgREST outage; Postgres was already verified via DATABASE_URL above."
            )
    except httpx.HTTPError as e:
        print(f"[i] REST ping failed: {e}")


def main() -> None:
    print(f"[+] SUPABASE_URL: {SUPABASE_URL}")
    print(f"[+] Project ref: {SUPABASE_PROJECT_ID or '(optional if SUPABASE_URL is set)'}")
    print(f"[+] DATABASE_URL: {_mask(DATABASE_URL, 6)}")
    print(f"[+] NEO4J_URI: {_mask(NEO4J_URI, 8)}")

    check_postgres()
    check_neo4j()
    check_supabase_client()
    check_rest_informational()

    print("[+] All checks passed: Postgres + Neo4j + Supabase client.")


if __name__ == "__main__":
    main()
