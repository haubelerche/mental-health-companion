"""Consolidate duplicated public schema tables into app.

Revision ID: 0022_public_to_app
Revises: 0021_screening_answers_table
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0022_public_to_app"
down_revision = "0021_screening_answers_table"
branch_labels = None
depends_on = None

APP_SCHEMA = "app"
BACKUP_SCHEMA = "schema_cleanup_backup_20260509"

DUPLICATED_APP_TABLES = (
    "users",
    "resources",
    "journal_prompts",
    "reward_store_items",
    "knowledge_packs",
    "knowledge_cards",
    "conversations",
    "messages",
    "mood_checkins",
    "clinical_profiles",
    "session_summaries_archive",
    "user_profiles",
    "user_profile_snapshots",
    "risk_inference_log",
    "session_risk_snapshots",
    "crisis_logs",
    "analyst_signals",
    "insight_hypotheses",
    "bookmarks",
    "play_events",
    "heart_wallets",
    "heart_reward_events",
    "heart_spend_events",
    "streak_states",
    "user_inventory_items",
    "nutrition_meal_checkins",
    "persona_unlock_states",
    "memory_cards",
    "memory_card_audit_events",
    "user_knowledge_progress",
    "user_notification_preferences",
    "user_notifications",
    "therapy_letters",
    "sync_outbox",
    "refresh_tokens",
    "user_identities",
    "email_verification_tokens",
    "password_reset_tokens",
    "admin_audit_log",
    "counseling_knowledge",
    "alembic_version",
)

MEM0_TABLES = (
    "mem0_memories",
)

RETIRED_MEMORY_TABLES = (
    "conversation_memories",
    "mem0_memories_entities",
    "mem0migrations",
)

PUBLIC_ONLY_LEGACY_TABLES = (
    "letter_flows",
    "letter_reactions",
    "letter_replies",
    "letters",
    "reports",
    "user_letter_history",
)

PUBLIC_TABLES_TO_BACKUP_AND_DROP = (
    DUPLICATED_APP_TABLES
    + MEM0_TABLES
    + RETIRED_MEMORY_TABLES
    + PUBLIC_ONLY_LEGACY_TABLES
)

LEGACY_COLUMN_MAP = (
    ("admin_audit_log", "created_at", "timestamp", 'p."timestamp"'),
    (
        "crisis_logs",
        "severity_level",
        "muc_do",
        "CASE p.muc_do WHEN 'cao' THEN 'high' WHEN 'trung_binh' THEN 'moderate' "
        "WHEN 'thap' THEN 'low' ELSE 'unknown' END",
    ),
    (
        "messages",
        "assistant_tone",
        "tone_cam_xuc",
        "CASE p.tone_cam_xuc WHEN 'xac_nhan' THEN 'validating' WHEN 'ho_tro' THEN 'supportive' "
        "WHEN 'vui_ve' THEN 'cheerful' WHEN 'binh_tinh' THEN 'calming' ELSE NULL END",
    ),
)


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _pg_array(values: tuple[str, ...]) -> str:
    return "ARRAY[" + ", ".join(_quote_literal(value) for value in values) + "]"


def _legacy_column_values() -> str:
    return ", ".join(
        "("
        f"{_quote_literal(table)}, "
        f"{_quote_literal(app_column)}, "
        f"{_quote_literal(public_column)}, "
        f"{_quote_literal(select_expr)}"
        ")"
        for table, app_column, public_column, select_expr in LEGACY_COLUMN_MAP
    )


def _table_exists(schema: str, table: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema = :schema
                    AND table_name = :table
                    AND table_type = 'BASE TABLE'
                )
                """
            ),
            {"schema": schema, "table": table},
        ).scalar()
    )


def _assert_app_revision() -> None:
    bind = op.get_bind()
    if not _table_exists(APP_SCHEMA, "alembic_version"):
        return
    version = bind.execute(sa.text("SELECT version_num FROM app.alembic_version LIMIT 1")).scalar()
    if version not in {down_revision, revision}:
        raise RuntimeError(
            "Refusing schema consolidation because app.alembic_version is "
            f"{version!r}, expected {down_revision!r}."
        )


def _preflight_sql() -> str:
    return f"""
    DO $$
    DECLARE
      target_table text;
      app_pk_count integer;
      public_pk_count integer;
      extra_column record;
      extra_count bigint;
      legacy_count bigint;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(DUPLICATED_APP_TABLES)}
      LOOP
        IF to_regclass(format('public.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        IF to_regclass(format('app.%I', target_table)) IS NULL THEN
          RAISE EXCEPTION 'public.% exists but app.% is missing', target_table, target_table;
        END IF;

        SELECT count(*) INTO app_pk_count
        FROM information_schema.table_constraints
        WHERE table_schema = 'app'
          AND table_name = target_table
          AND constraint_type = 'PRIMARY KEY';

        SELECT count(*) INTO public_pk_count
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = target_table
          AND constraint_type = 'PRIMARY KEY';

        IF target_table <> 'alembic_version' AND (app_pk_count <> 1 OR public_pk_count <> 1) THEN
          RAISE EXCEPTION 'Cannot merge %.% because primary key metadata is missing or ambiguous',
            'public', target_table;
        END IF;

        FOR extra_column IN
          SELECT c.column_name
          FROM information_schema.columns c
          WHERE c.table_schema = 'public'
            AND c.table_name = target_table
            AND NOT EXISTS (
              SELECT 1
              FROM (VALUES {_legacy_column_values()}) AS legacy(table_name, app_column, public_column, select_expr)
              WHERE legacy.table_name = target_table
                AND legacy.public_column = c.column_name
            )
            AND NOT EXISTS (
              SELECT 1
              FROM information_schema.columns app_c
              WHERE app_c.table_schema = 'app'
                AND app_c.table_name = c.table_name
                AND app_c.column_name = c.column_name
            )
        LOOP
          EXECUTE format(
            'SELECT count(*) FROM public.%I WHERE %I IS NOT NULL',
            target_table,
            extra_column.column_name
          )
          INTO extra_count;

          IF extra_count > 0 THEN
            RAISE EXCEPTION
              'Cannot merge public.%: extra column % has % non-null rows absent from app.% ',
              target_table,
              extra_column.column_name,
              extra_count,
              target_table;
          END IF;
        END LOOP;
      END LOOP;

      FOREACH target_table IN ARRAY {_pg_array(PUBLIC_ONLY_LEGACY_TABLES)}
      LOOP
        IF to_regclass(format('public.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        EXECUTE format('SELECT count(*) FROM public.%I', target_table) INTO legacy_count;
        IF legacy_count <> 0 THEN
          RAISE EXCEPTION 'Refusing to drop non-empty legacy public-only table public.% with % rows',
            target_table,
            legacy_count;
        END IF;
      END LOOP;
    END $$;
    """


def _backup_sql() -> str:
    return f"""
    CREATE SCHEMA IF NOT EXISTS {BACKUP_SCHEMA};

    DO $$
    DECLARE
      target_table text;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(PUBLIC_TABLES_TO_BACKUP_AND_DROP)}
      LOOP
        IF to_regclass(format('public.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        EXECUTE format(
          'CREATE TABLE IF NOT EXISTS {BACKUP_SCHEMA}.%I (LIKE public.%I INCLUDING ALL)',
          target_table,
          target_table
        );
        EXECUTE format(
          'INSERT INTO {BACKUP_SCHEMA}.%I SELECT * FROM public.%I ON CONFLICT DO NOTHING',
          target_table,
          target_table
        );
      END LOOP;
    END $$;
    """


def _merge_sql() -> str:
    return f"""
    DO $$
    DECLARE
      target_table text;
      insert_columns text;
      select_columns text;
      where_clause text;
      fk record;
      fk_column_count integer;
      mapped_column_count integer;
      null_checks text;
      ref_matches text;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(DUPLICATED_APP_TABLES)}
      LOOP
        IF target_table = 'alembic_version'
           OR to_regclass(format('public.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        SELECT string_agg(format('%I', c.column_name), ', ' ORDER BY c.ordinal_position),
               string_agg(
                 format(
                   '(%s)::%s',
                   COALESCE(legacy.select_expr, format('p.%I', c.column_name)),
                   CASE
                     WHEN c.udt_schema = 'pg_catalog' THEN format('%I', c.udt_name)
                     ELSE format('%I.%I', c.udt_schema, c.udt_name)
                   END
                 ),
                 ', ' ORDER BY c.ordinal_position
               )
        INTO insert_columns, select_columns
        FROM information_schema.columns c
        LEFT JOIN (VALUES {_legacy_column_values()}) AS legacy(table_name, app_column, public_column, select_expr)
          ON legacy.table_name = c.table_name
         AND legacy.app_column = c.column_name
        WHERE c.table_schema = 'app'
          AND c.table_name = target_table
          AND EXISTS (
            SELECT 1
            FROM information_schema.columns public_c
            WHERE public_c.table_schema = 'public'
              AND public_c.table_name = c.table_name
              AND public_c.column_name = COALESCE(legacy.public_column, c.column_name)
          );

        IF insert_columns IS NULL THEN
          RAISE EXCEPTION 'Cannot build merge statement for %', target_table;
        END IF;

        where_clause := 'true';
        FOR fk IN
          SELECT
            ref_ns.nspname AS ref_schema,
            ref_table.relname AS ref_table,
            array_agg(local_att.attname ORDER BY fk_cols.ordinality) AS local_columns,
            array_agg(ref_att.attname ORDER BY fk_cols.ordinality) AS ref_columns
          FROM pg_constraint con
          JOIN pg_class local_table ON local_table.oid = con.conrelid
          JOIN pg_namespace local_ns ON local_ns.oid = local_table.relnamespace
          JOIN pg_class ref_table ON ref_table.oid = con.confrelid
          JOIN pg_namespace ref_ns ON ref_ns.oid = ref_table.relnamespace
          JOIN unnest(con.conkey, con.confkey) WITH ORDINALITY AS fk_cols(local_attnum, ref_attnum, ordinality)
            ON true
          JOIN pg_attribute local_att
            ON local_att.attrelid = local_table.oid
           AND local_att.attnum = fk_cols.local_attnum
          JOIN pg_attribute ref_att
            ON ref_att.attrelid = ref_table.oid
           AND ref_att.attnum = fk_cols.ref_attnum
          WHERE con.contype = 'f'
            AND local_ns.nspname = 'app'
            AND local_table.relname = target_table
          GROUP BY ref_ns.nspname, ref_table.relname, con.oid
        LOOP
          SELECT
            count(*),
            count(*) FILTER (WHERE public_c.column_name IS NOT NULL),
            string_agg(format('p.%I IS NULL', mapped.source_column), ' OR ' ORDER BY mapped.ordinality),
            string_agg(format('r.%I = p.%I', mapped.ref_column, mapped.source_column), ' AND ' ORDER BY mapped.ordinality)
          INTO fk_column_count, mapped_column_count, null_checks, ref_matches
          FROM (
            SELECT
              cols.ordinality,
              cols.local_column,
              cols.ref_column,
              COALESCE(legacy.public_column, cols.local_column) AS source_column
            FROM unnest(fk.local_columns, fk.ref_columns) WITH ORDINALITY AS cols(local_column, ref_column, ordinality)
            LEFT JOIN (VALUES {_legacy_column_values()}) AS legacy(table_name, app_column, public_column, select_expr)
              ON legacy.table_name = target_table
             AND legacy.app_column = cols.local_column
          ) AS mapped
          LEFT JOIN information_schema.columns public_c
            ON public_c.table_schema = 'public'
           AND public_c.table_name = target_table
           AND public_c.column_name = mapped.source_column;

          IF fk_column_count = mapped_column_count AND fk_column_count > 0 THEN
            where_clause := where_clause || format(
              ' AND ((%s) OR EXISTS (SELECT 1 FROM %I.%I r WHERE %s))',
              null_checks,
              fk.ref_schema,
              fk.ref_table,
              ref_matches
            );
          END IF;
        END LOOP;

        EXECUTE format(
          'INSERT INTO app.%I (%s) OVERRIDING SYSTEM VALUE SELECT %s FROM public.%I p WHERE %s ON CONFLICT DO NOTHING',
          target_table,
          insert_columns,
          select_columns,
          target_table,
          where_clause
        );
      END LOOP;
    END $$;
    """


def _mem0_sql() -> str:
    return f"""
    CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

    DO $$
    DECLARE
      target_table text;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(MEM0_TABLES)}
      LOOP
        IF to_regclass(format('public.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        EXECUTE format(
          'CREATE TABLE IF NOT EXISTS app.%I (LIKE public.%I INCLUDING ALL)',
          target_table,
          target_table
        );
        EXECUTE format(
          'INSERT INTO app.%I SELECT * FROM public.%I ON CONFLICT DO NOTHING',
          target_table,
          target_table
        );
      END LOOP;
    END $$;
    """


def _retired_memory_sql() -> str:
    return f"""
    DO $$
    DECLARE
      target_table text;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(RETIRED_MEMORY_TABLES)}
      LOOP
        IF to_regclass(format('app.%I', target_table)) IS NULL THEN
          CONTINUE;
        END IF;

        EXECUTE format(
          'CREATE TABLE IF NOT EXISTS {BACKUP_SCHEMA}.app_%I (LIKE app.%I INCLUDING ALL)',
          target_table,
          target_table
        );
        EXECUTE format(
          'INSERT INTO {BACKUP_SCHEMA}.app_%I SELECT * FROM app.%I ON CONFLICT DO NOTHING',
          target_table,
          target_table
        );
        EXECUTE format('DROP TABLE app.%I CASCADE', target_table);
      END LOOP;
    END $$;
    """


def _reset_sequences_sql() -> str:
    return """
    DO $$
    DECLARE
      seq record;
    BEGIN
      FOR seq IN
        SELECT
          n.nspname AS sequence_schema,
          s.relname AS sequence_name,
          tn.nspname AS table_schema,
          t.relname AS table_name,
          a.attname AS column_name
        FROM pg_class s
        JOIN pg_namespace n ON n.oid = s.relnamespace
        JOIN pg_depend d ON d.objid = s.oid AND d.deptype IN ('a', 'i')
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_namespace tn ON tn.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE s.relkind = 'S'
          AND tn.nspname = 'app'
      LOOP
        EXECUTE format(
          'SELECT setval(%L, COALESCE((SELECT max(%I) FROM %I.%I), 0) + 1, false)',
          format('%I.%I', seq.sequence_schema, seq.sequence_name),
          seq.column_name,
          seq.table_schema,
          seq.table_name
        );
      END LOOP;
    END $$;
    """


def _drop_public_sql() -> str:
    return f"""
    DO $$
    DECLARE
      target_table text;
    BEGIN
      FOREACH target_table IN ARRAY {_pg_array(PUBLIC_TABLES_TO_BACKUP_AND_DROP)}
      LOOP
        IF to_regclass(format('public.%I', target_table)) IS NOT NULL THEN
          EXECUTE format('DROP TABLE public.%I CASCADE', target_table);
        END IF;
      END LOOP;
    END $$;

    DROP SCHEMA IF EXISTS public CASCADE;
    """


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, extensions")
    _assert_app_revision()
    op.execute(_preflight_sql())
    op.execute(_backup_sql())
    op.execute(_merge_sql())
    op.execute(_mem0_sql())
    op.execute(_retired_memory_sql())
    op.execute(_reset_sequences_sql())
    op.execute(_drop_public_sql())


def downgrade() -> None:
    raise RuntimeError(
        "0022_consolidate_public_schema_into_app is intentionally irreversible. "
        f"Restore from {BACKUP_SCHEMA} manually if rollback is required."
    )
