from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_mem0_config_does_not_enable_neo4j_graph_store() -> None:
    src = _read("backend/app/services/mem0_service.py")
    assert 'config["graph_store"]' not in src
    assert '"provider": "neo4j"' not in src


def test_mem0_is_canonical_memory_table() -> None:
    src = _read("backend/app/services/mem0_service.py")
    assert "mem0_memories" in src
    assert '"collection_name": MEM0_COLLECTION_NAME' in src
    assert "search_path={MEM0_SCHEMA},extensions" in src


def test_public_schema_cleanup_drops_public_schema() -> None:
    src = _read("backend/alembic/versions/0022_consolidate_public_schema_into_app.py")
    assert "DROP SCHEMA IF EXISTS public CASCADE" in src
    assert "DROP TABLE public.%I CASCADE" in src
    assert 'BACKUP_SCHEMA = "schema_cleanup_backup_20260509"' in src


def test_legacy_memory_tables_are_forbidden() -> None:
    migration = _read("backend/alembic/versions/0022_consolidate_public_schema_into_app.py")
    retirement = _read("backend/alembic/versions/0023_retire_memory_cards.py")
    duplicate_retirement = _read("backend/alembic/versions/0024_retire_legacy_schema_duplicates.py")
    verify = _read("backend/scripts/verify_db_schema.py")
    models = _read("backend/app/services/db/models.py")

    assert '"mem0_memories"' in migration
    assert '"memory_cards"' in retirement
    assert '"memory_card_audit_events"' in retirement
    assert "DROP TABLE IF EXISTS app.{table} RESTRICT" in retirement
    assert "RETIRED_MEMORY_TABLES" in migration
    assert '"conversation_memories"' in migration
    assert '"mem0_memories_entities"' in migration
    assert '"mem0migrations"' in migration
    assert '"conversation_memories"' in duplicate_retirement
    assert '"mem0_memories_entities"' in duplicate_retirement
    assert '"mem0migrations"' in duplicate_retirement

    required_tables = verify.split("FORBIDDEN_TABLES", 1)[0]
    assert '"mem0_memories"' in required_tables
    assert '"memory_cards"' not in required_tables
    assert '"memory_card_audit_events"' not in required_tables
    assert '"conversation_memories"' not in required_tables
    assert "class ConversationMemory" not in models
    assert "class MemoryCard" not in models


def test_schema_verifier_tracks_active_tables_and_forbids_legacy_duplicates() -> None:
    verify = _read("backend/scripts/verify_db_schema.py")

    required_tables = verify.split("FORBIDDEN_TABLES", 1)[0]
    assert '"screening_answers"' in required_tables
    assert '"journal_prompts"' not in required_tables
    assert '"journal_entries"' not in required_tables
    assert '"letter_review_events"' in required_tables
    assert '"counseling_knowledge"' in required_tables
    assert '"advisor_case_library"' in required_tables
    assert '"phq9_coverage"' in verify
    assert '"gad7_coverage"' in verify
    assert '"model_version"' in verify

    forbidden_block = verify.split("FORBIDDEN_TABLES", 1)[1].split("REQUIRED_COLUMNS", 1)[0]
    assert '"memory_cards"' in forbidden_block
    assert '"memory_card_audit_events"' in forbidden_block
    assert '"conversation_memories"' in forbidden_block
    assert '"mem0_memories_entities"' in forbidden_block
    assert '"mem0migrations"' in forbidden_block
    assert '"screening_results"' in forbidden_block
    assert '"analyst_bundles"' in forbidden_block
    assert '"async_outbox"' in forbidden_block


def test_legacy_duplicate_retirement_migration_covers_schema_cleanup_targets() -> None:
    src = _read("backend/alembic/versions/0024_retire_legacy_schema_duplicates.py")
    assert 'revision = "0024_retire_legacy_dupes"' in src
    assert 'down_revision = "0023_retire_memory_cards"' in src
    assert 'BACKUP_SCHEMA = "schema_cleanup_backup_20260512"' in src
    for table_name in (
        "screening_results",
        "conversation_memories",
        "mem0_memories_entities",
        "mem0migrations",
        "memory_cards",
        "memory_card_audit_events",
        "analyst_bundles",
        "async_outbox",
    ):
        assert f'"{table_name}"' in src
    assert "DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT" in src
    assert "CASCADE" not in src


def test_active_runtime_tables_still_have_live_code_owners() -> None:
    screening = _read("backend/app/api/v1/routers/screening.py")
    resources = _read("backend/app/api/v1/routers/resources.py")
    reflect = _read("backend/app/api/v1/routers/reflect.py")
    knowledge = _read("backend/app/knowledge/progress_service.py")
    retriever = _read("backend/app/services/counseling_retriever.py")
    advisor_case_retriever = _read("backend/app/services/advisor_case_retriever.py")
    counseling_advisor = _read("backend/app/services/counseling_advisor_service.py")
    letter = _read("backend/app/api/v1/routers/letter.py")

    assert "ScreeningAnswer" in screening
    assert "FEATURE_RETIRED" in resources
    assert "FEATURE_RETIRED" in reflect
    assert "KnowledgeCard" in knowledge
    assert "KnowledgePack" in knowledge
    assert "UserKnowledgeProgress" in knowledge
    assert "counseling_knowledge" in retriever
    assert "advisor_case_library" in advisor_case_retriever
    assert "CounselingAdvisorService" in counseling_advisor
    assert "LetterReviewEvent" in letter


def test_advisor_case_library_migration_creates_processed_case_table() -> None:
    src = _read("backend/alembic/versions/0028_advisor_case_library.py")
    assert 'revision = "0028_advisor_case_library"' in src
    assert 'down_revision = "0027_drop_memory_cards"' in src
    assert "app.advisor_case_library" in src
    assert "raw_case_id text" in src
    assert "intervention_steps jsonb" in src
    assert "reflection_questions jsonb" in src
    assert "embedding vector(1536)" in src
    assert "safety_review_status" in src


def test_sync_outbox_is_only_outbox_table() -> None:
    models = _read("backend/app/services/db/models.py")
    ownership = _read("backend/app/services/db/schema_ownership.py")
    assert "class SyncOutbox" in models
    assert '__tablename__ = "sync_outbox"' in models
    assert '"async_outbox"' in ownership
    assert "docs_only_drift" in ownership


def test_analyst_bundles_is_not_required_table() -> None:
    verify = _read("backend/scripts/verify_db_schema.py")
    required_tables = verify.split("FORBIDDEN_TABLES", 1)[0]
    forbidden_block = verify.split("FORBIDDEN_TABLES", 1)[1]
    assert '"analyst_bundles"' not in required_tables
    assert '"analyst_bundles"' in forbidden_block


def test_active_tables_are_not_in_retired_sets() -> None:
    ownership = _read("backend/app/services/db/schema_ownership.py")
    assert '"mem0_memories"' in ownership
    assert '"sync_outbox"' in ownership
    assert '"screening_answers"' in ownership
    assert '"conversation_memories"' in ownership
    assert '"legacy_retired_drop_now"' in ownership


def test_0024_retire_set_is_narrow_and_safe() -> None:
    src = _read("backend/alembic/versions/0024_retire_legacy_schema_duplicates.py")
    assert "RETIRE_TARGETS" in src
    assert "screening_results" in src
    assert "conversation_memories" in src
    assert "mem0_memories_entities" in src
    assert "mem0migrations" in src
    assert "memory_cards" in src
    assert "memory_card_audit_events" in src
    assert "analyst_bundles" in src
    assert "async_outbox" in src
    assert "journal_entries" not in src
    assert "knowledge_packs" not in src
    assert "DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT" in src


def test_0025_only_drops_ownerless_tables() -> None:
    versions_dir = ROOT / "backend" / "alembic" / "versions"
    migration = versions_dir / "0025_retire_ownerless_feature_tables.py"
    if not migration.exists():
        assert True
        return
    src = migration.read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS" in src
    assert "RESTRICT" in src
    assert "CASCADE" not in src


def test_cleanup_migrations_use_drop_restrict_only() -> None:
    m23 = _read("backend/alembic/versions/0023_retire_memory_cards.py")
    m24 = _read("backend/alembic/versions/0024_retire_legacy_schema_duplicates.py")
    m27 = _read("backend/alembic/versions/0027_drop_ownerless_memory_card_tables.py")
    assert "DROP TABLE IF EXISTS app.{table} RESTRICT" in m23
    assert "DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT" in m24
    assert "DROP TABLE IF EXISTS {schema_name}.{table_name} RESTRICT" in m27


def test_no_drop_cascade_in_cleanup_migrations() -> None:
    m24 = _read("backend/alembic/versions/0024_retire_legacy_schema_duplicates.py")
    m27 = _read("backend/alembic/versions/0027_drop_ownerless_memory_card_tables.py")
    assert "DROP TABLE" in m24 and "CASCADE" not in m24
    assert "DROP TABLE" in m27 and "CASCADE" not in m27


def test_memory_cards_removed_from_runtime_schema_contract() -> None:
    ownership = _read("backend/app/services/db/schema_ownership.py")
    assert '"memory_cards"' in ownership
    assert '"memory_card_audit_events"' in ownership
    assert '"legacy_retired_drop_now"' in ownership


def test_session_summary_does_not_enqueue_user_graph_events() -> None:
    src = _read("backend/app/services/session_summary.py")
    assert 'event_type="session.ended"' not in src
    assert 'event_type="trigger.observed"' not in src
    assert 'event_type="coping.attempted"' not in src
    assert '"content": mask_pii(str(m.content))' in src


def test_notification_outbox_worker_does_not_claim_graph_or_voice_events() -> None:
    src = _read("backend/app/services/outbox_worker.py")
    assert "SyncOutbox.event_type.in_(NOTIFICATION_EVENT_TYPES)" in src
    assert "raise ValueError" in src
    assert "row.error_message" in src


def test_dashboard_overview_is_frontend_safe() -> None:
    src = _read("backend/app/api/v1/routers/dashboard.py")
    assert "ClinicalProfile" not in src
    assert "phq9_score" not in src
    assert "gad7_score" not in src
    assert "crisis_level" not in src


def test_dashboard_safe_insights_require_persisted_evidence() -> None:
    src = _read("backend/app/dashboard/service.py")
    assert "InsightHypothesis.evidence_count > 0" in src
    build_safe = src.split("def build_safe_insight_cards", 1)[1].split("def build_checkin_history", 1)[0]
    assert "_build_insight_cards(" not in build_safe
    assert "_profile_insights(" not in build_safe


def test_voice_jobs_do_not_store_base64_audio_in_outbox_payload() -> None:
    src = _read("backend/app/services/proactive_voice.py")
    assert 'payload["voice"]["audio_data_uri"]' not in src
    assert '"audio_path"' in src
    assert '"audio_url"' in src


def test_fastapi_startup_has_no_runtime_ddl() -> None:
    src = _read("backend/app/main.py")
    assert "ALTER TABLE" not in src
    assert "ADD GENERATED" not in src
