from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_mem0_config_does_not_enable_neo4j_graph_store() -> None:
    src = _read("backend/app/services/mem0_service.py")
    assert 'config["graph_store"]' not in src
    assert '"provider": "neo4j"' not in src


def test_mem0_pgvector_uses_app_schema() -> None:
    src = _read("backend/app/services/mem0_service.py")
    assert 'MEM0_COLLECTION_NAME = f"{MEM0_SCHEMA}.mem0_memories"' in src
    assert '"collection_name": MEM0_COLLECTION_NAME' in src
    assert "search_path={MEM0_SCHEMA},extensions" in src


def test_public_schema_cleanup_drops_public_schema() -> None:
    src = _read("backend/alembic/versions/0022_consolidate_public_schema_into_app.py")
    assert "DROP SCHEMA IF EXISTS public CASCADE" in src
    assert "DROP TABLE public.%I CASCADE" in src
    assert 'BACKUP_SCHEMA = "schema_cleanup_backup_20260509"' in src


def test_memory_schema_keeps_only_active_memory_tables() -> None:
    migration = _read("backend/alembic/versions/0022_consolidate_public_schema_into_app.py")
    retirement = _read("backend/alembic/versions/0023_retire_memory_cards.py")
    verify = _read("backend/scripts/verify_db_schema.py")
    models = _read("backend/app/services/db/models.py")

    assert '"mem0_memories"' in migration
    assert '"memory_cards"' in retirement
    assert '"memory_card_audit_events"' in retirement
    assert "DROP TABLE app.{table} CASCADE" in retirement
    assert "RETIRED_MEMORY_TABLES" in migration
    assert '"conversation_memories"' in migration
    assert '"mem0_memories_entities"' in migration
    assert '"mem0migrations"' in migration

    required_tables = verify.split("REQUIRED_COLUMNS", 1)[0]
    assert '"mem0_memories"' in required_tables
    assert '"memory_cards"' not in required_tables
    assert '"memory_card_audit_events"' not in required_tables
    assert '"conversation_memories"' not in required_tables
    assert "class ConversationMemory" not in models
    assert "class MemoryCard" not in models


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
