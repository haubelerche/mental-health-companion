"""Run: DATABASE_URL=<supabase_url> python backend/scripts/verify_db_schema.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sqlalchemy as sa

from app.core.config import get_settings

REQUIRED_TABLES = [
    "users",
    "user_identities",
    "refresh_tokens",
    "email_verification_tokens",
    "password_reset_tokens",
    "conversations",
    "messages",
    "mood_checkins",
    "resources",
    "bookmarks",
    "play_events",
    "mem0_memories",
    "session_summaries_archive",
    "user_profiles",
    "user_profile_snapshots",
    "clinical_profiles",
    "risk_inference_log",
    "session_risk_snapshots",
    "crisis_logs",
    "analyst_signals",
    "insight_hypotheses",
    "sync_outbox",
    "admin_audit_log",
    "heart_wallets",
    "heart_reward_events",
    "heart_spend_events",
    "streak_states",
    "nutrition_meal_checkins",
    "persona_unlock_states",
    "reward_store_items",
    "user_inventory_items",
    "knowledge_packs",
    "knowledge_cards",
    "user_knowledge_progress",
    "user_notifications",
    "user_notification_preferences",
]

REQUIRED_COLUMNS = {
    "sync_outbox": {
        "outbox_id",
        "user_id",
        "event_type",
        "payload",
        "status",
        "retry_count",
        "error_message",
        "created_at",
        "processing_started_at",
        "processed_at",
    },
    "clinical_profiles": {
        "profile_id",
        "user_id",
        "phq9_score",
        "gad7_score",
        "crisis_level",
        "score_source",
        "last_scored_at",
    },
    "risk_inference_log": {
        "log_id",
        "user_id",
        "session_id",
        "inferred_signal",
        "score",
        "detail",
        "created_at",
    },
    "session_risk_snapshots": {
        "snapshot_id",
        "session_id",
        "user_id",
        "risk_score",
        "intent_severity",
        "intent_immediacy",
        "crisis_mode",
        "escalation_flag",
        "components",
        "source",
        "created_at",
    },
    "insight_hypotheses": {
        "insight_id",
        "user_id",
        "hypothesis_type",
        "title",
        "user_safe_summary",
        "internal_rationale",
        "evidence_count",
        "severity_band",
        "display_allowed",
        "status",
    },
    "heart_wallets": {"user_id", "balance", "lifetime_earned", "lifetime_spent"},
    "knowledge_cards": {"card_id", "pack_id", "title", "content_markdown", "order_index"},
}


def main() -> None:
    settings = get_settings()
    db_url = settings.normalized_database_url()
    if "sqlite" in db_url:
        print("ERROR: DATABASE_URL is SQLite/local, not Supabase/PostgreSQL")
        sys.exit(1)

    engine = sa.create_engine(
        db_url,
        connect_args={"options": "-c search_path=app,extensions", "connect_timeout": 10},
    )
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SET search_path TO app, extensions"))
            print(f"OK: connected: {db_url[:50]}...")

            result = conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'app' ORDER BY table_name"
                )
            )
            existing = {row[0] for row in result}
            print(f"\nTables in app schema ({len(existing)}):")
            for table in sorted(existing):
                marker = "OK" if table in REQUIRED_TABLES else "EXTRA"
                print(f"  {marker} {table}")

            public_schema_exists = conn.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name='public')")
            ).scalar()
            if public_schema_exists:
                print("\nERROR: public schema still exists; canonical database must use only app plus extension/system schemas")
                sys.exit(1)

            missing = set(REQUIRED_TABLES) - existing
            if missing:
                print(f"\nERROR: missing tables in Supabase ({len(missing)}):")
                for table in sorted(missing):
                    print(f"  MISSING {table}")
                sys.exit(1)
            print("\nOK: all required tables exist")

            cols = conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='app' AND table_name='messages' ORDER BY column_name"
                )
            )
            msg_cols = {row[0] for row in cols}
            print(f"\nmessages columns: {sorted(msg_cols)}")
            if "assistant_tone" not in msg_cols:
                print("  ERROR: messages.assistant_tone is missing")
            if "tone_cam_xuc" in msg_cols:
                print("  WARNING: legacy messages.tone_cam_xuc still exists")

            for table_name, required_cols in REQUIRED_COLUMNS.items():
                cols_result = conn.execute(
                    sa.text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='app' AND table_name=:table_name"
                    ),
                    {"table_name": table_name},
                )
                present_cols = {row[0] for row in cols_result}
                missing_cols = required_cols - present_cols
                if missing_cols:
                    print(f"\nERROR: app.{table_name} missing columns: {sorted(missing_cols)}")
                    sys.exit(1)
                if table_name == "sync_outbox" and "attempts" in present_cols:
                    print("\nERROR: legacy app.sync_outbox.attempts exists; canonical column is retry_count")
                    sys.exit(1)

            mood_cols_result = conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='app' AND table_name='mood_checkins'"
                )
            )
            mood_cols = {row[0] for row in mood_cols_result}
            if "time_bucket" not in mood_cols:
                print("  ERROR: app.mood_checkins.time_bucket is missing")
                sys.exit(1)

            profile_cols_result = conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='app' AND table_name='user_profiles'"
                )
            )
            profile_cols = {row[0] for row in profile_cols_result}
            required_profile_cols = {
                "user_id",
                "version",
                "schema_version",
                "profile",
                "last_active_session_id",
                "summary_count",
                "updated_at",
            }
            missing_profile_cols = required_profile_cols - profile_cols
            if missing_profile_cols:
                print(f"\nERROR: app.user_profiles missing columns: {sorted(missing_profile_cols)}")
                sys.exit(1)

            profile_schema_result = conn.execute(
                sa.text(
                    "SELECT table_schema FROM information_schema.tables "
                    "WHERE table_name='user_profiles' ORDER BY table_schema"
                )
            )
            profile_schemas = [row[0] for row in profile_schema_result]
            print(f"\nuser_profiles schemas: {profile_schemas}")
            if "public" in profile_schemas:
                print("ERROR: public.user_profiles exists; canonical runtime must use only app.")
                sys.exit(1)

            feature_schema_result = conn.execute(
                sa.text(
                    "SELECT table_name, table_schema FROM information_schema.tables "
                    "WHERE table_name = ANY(:feature_tables) "
                    "ORDER BY table_name, table_schema"
                ),
                {"feature_tables": REQUIRED_TABLES},
            )
            feature_schemas: dict[str, set[str]] = {}
            for table_name, table_schema in feature_schema_result:
                feature_schemas.setdefault(table_name, set()).add(table_schema)
            missing_app_features = [
                table for table in REQUIRED_TABLES if table not in feature_schemas or "app" not in feature_schemas[table]
            ]
            if missing_app_features:
                print(f"\nERROR: required tables missing from app schema: {sorted(missing_app_features)}")
                sys.exit(1)
    except Exception as exc:
        print(f"ERROR: connection or schema check failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
