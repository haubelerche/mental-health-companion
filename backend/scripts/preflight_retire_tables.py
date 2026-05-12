"""Operational preflight for legacy table retirement migrations.

Run:
    DATABASE_URL=<postgres_url> python backend/scripts/preflight_retire_tables.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlalchemy as sa

from app.core.config import get_settings

BACKUP_SCHEMA = "schema_cleanup_backup_20260512"
RETIRED_TABLES = {
    "app_drop_now": (
        ("app", "memory_card_audit_events"),
        ("app", "memory_cards"),
        ("app", "journal_entries"),
        ("app", "journal_prompts"),
        ("app", "bookmarks"),
        ("app", "play_events"),
        ("app", "risk_inference_log"),
    ),
    "app": (
        "screening_results",
        "conversation_memories",
        "mem0_memories_entities",
        "mem0migrations",
        "analyst_bundles",
        "async_outbox",
    ),
    "public": (
        "screening_results",
        "conversation_memories",
        "mem0_memories_entities",
        "mem0migrations",
        "memory_cards",
        "memory_card_audit_events",
        "analyst_bundles",
        "async_outbox",
    ),
    "extensions_drift_audit_only": (
        ("extensions", "mem0_memories_entities"),
        ("extensions", "mem0migrations"),
    ),
}


def _dependency_rows(conn: sa.Connection, *, schema_name: str, table_name: str) -> list[str]:
    qualified = f"{schema_name}.{table_name}"
    target = conn.execute(sa.text("SELECT to_regclass(:qualified)"), {"qualified": qualified}).scalar()
    if target is None:
        return []

    fk_rows = conn.execute(
        sa.text(
            """
            SELECT format('fk:%I.%I(%I)', dep_ns.nspname, dep_rel.relname, con.conname) AS detail
            FROM pg_constraint con
            JOIN pg_class dep_rel ON dep_rel.oid = con.conrelid
            JOIN pg_namespace dep_ns ON dep_ns.oid = dep_rel.relnamespace
            WHERE con.contype = 'f'
              AND con.confrelid = to_regclass(:qualified)
              AND NOT (dep_ns.nspname = :schema_name AND dep_rel.relname = :table_name)
            ORDER BY detail
            """
        ),
        {"qualified": qualified, "schema_name": schema_name, "table_name": table_name},
    ).scalars()

    view_rows = conn.execute(
        sa.text(
            """
            SELECT format('view:%I.%I', dep_ns.nspname, dep_rel.relname) AS detail
            FROM pg_depend dep
            JOIN pg_rewrite rw ON rw.oid = dep.objid
            JOIN pg_class dep_rel ON dep_rel.oid = rw.ev_class
            JOIN pg_namespace dep_ns ON dep_ns.oid = dep_rel.relnamespace
            WHERE dep.refobjid = to_regclass(:qualified)
              AND dep_rel.relkind IN ('v', 'm')
              AND dep_ns.nspname <> :backup_schema
            ORDER BY detail
            """
        ),
        {"qualified": qualified, "backup_schema": BACKUP_SCHEMA},
    ).scalars()

    return [*fk_rows, *view_rows]


def main() -> None:
    settings = get_settings()
    db_url = settings.normalized_database_url()
    if "sqlite" in db_url:
        print(json.dumps({"error": "DATABASE_URL points to sqlite"}, ensure_ascii=False))
        sys.exit(1)

    engine = sa.create_engine(
        db_url,
        connect_args={"options": "-c search_path=app,extensions", "connect_timeout": 10},
    )
    try:
        with engine.connect() as conn:
            for table_group, entries in RETIRED_TABLES.items():
                normalized_entries: list[tuple[str, str]] = []
                for entry in entries:
                    if isinstance(entry, tuple):
                        normalized_entries.append(entry)
                    else:
                        schema_name = "app" if table_group in {"app", "app_drop_now"} else table_group
                        normalized_entries.append((schema_name, entry))
                for schema_name, table_name in normalized_entries:
                    exists = bool(
                        conn.execute(
                            sa.text("SELECT to_regclass(:qualified) IS NOT NULL"),
                            {"qualified": f"{schema_name}.{table_name}"},
                        ).scalar()
                    )
                    row_count = None
                    dependencies: list[str] = []
                    if exists:
                        row_count = int(
                            conn.execute(sa.text(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")).scalar() or 0
                        )
                        dependencies = _dependency_rows(
                            conn,
                            schema_name=schema_name,
                            table_name=table_name,
                        )

                    print(
                        json.dumps(
                            {
                                "schema": schema_name,
                                "table": table_name,
                                "table_group": table_group,
                                "exists": exists,
                                "row_count": row_count,
                                "dependencies": dependencies,
                                "backup_target": f"{BACKUP_SCHEMA}.{schema_name}_{table_name}",
                                "safe_to_drop": bool(not exists or not dependencies),
                            },
                            ensure_ascii=False,
                        )
                    )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
