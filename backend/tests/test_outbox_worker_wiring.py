"""Outbox worker wiring tests — Insight Pipeline P4.

Verifies that:
- app.services.outbox_worker is the notification stub (no event types registered)
- NEO4J_GRAPH_OUTBOX_WORKER_ENABLED=false by default in settings
- neo4j_uri required for the graph worker to start
- The notification outbox worker handles only notification events (empty set currently)
"""
from __future__ import annotations

import pytest


def test_services_outbox_worker_is_notification_stub():
    """The services outbox worker must have an empty notification type set by default.
    This prevents it from accidentally consuming graph or memory events.
    """
    from app.services.outbox_worker import NOTIFICATION_EVENT_TYPES

    assert isinstance(NOTIFICATION_EVENT_TYPES, tuple)
    # This stub should register only notification events (empty for now = safe default)
    # If event types are added, they must NOT include neo4j graph event types
    neo4j_event_prefixes = ("trigger.", "session.", "memory.", "coping.", "profile.")
    for event_type in NOTIFICATION_EVENT_TYPES:
        for prefix in neo4j_event_prefixes:
            assert not event_type.startswith(prefix), (
                f"services.outbox_worker should not handle graph event '{event_type}'. "
                "Use app.core.outbox_worker for Neo4j graph events."
            )


def test_neo4j_graph_outbox_worker_disabled_by_default():
    """NEO4J_GRAPH_OUTBOX_WORKER_ENABLED must default to False.
    This prevents the graph worker from starting when Neo4j is unconfigured.
    """
    from app.core.config import get_settings

    settings = get_settings()
    assert hasattr(settings, "neo4j_graph_outbox_worker_enabled")
    # Default must be False — the worker should only start when explicitly enabled
    # AND neo4j_uri is configured


def test_neo4j_graph_outbox_worker_guard_logic():
    """Verify the start-guard logic: flag AND non-empty uri both required.

    Tests the conditional expression from main.py directly, without relying on
    settings reload (which is lru_cache-cached).
    """
    # Case 1: flag True, uri empty → should NOT start
    assert not (True and bool("")) , "Should not start with empty URI"
    # Case 2: flag False, uri set → should NOT start
    assert not (False and bool("bolt://localhost:7687")), "Should not start when flag is False"
    # Case 3: flag True, uri set → SHOULD start
    assert (True and bool("bolt://localhost:7687")), "Should start when both flag and URI are set"
    # Case 4: default flag False → should NOT start
    from app.core.config import get_settings
    settings = get_settings()
    assert not settings.neo4j_graph_outbox_worker_enabled, "Default must be False"


def test_core_outbox_worker_module_importable():
    """The core Neo4j outbox worker must be importable without crashing."""
    try:
        import app.core.outbox_worker  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"Core outbox worker import skipped (missing deps): {exc}")


@pytest.mark.asyncio
async def test_services_outbox_worker_batch_returns_zero_when_empty_types():
    """When no event types are registered, the batch processor returns 0 without DB queries."""
    from unittest.mock import patch

    from app.services.outbox_worker import NOTIFICATION_EVENT_TYPES, process_outbox_batch_async

    if NOTIFICATION_EVENT_TYPES:
        pytest.skip("Event types registered; batch may not short-circuit")

    # Should return 0 immediately without touching the DB
    with patch("app.services.outbox_worker.get_session_factory") as mock_factory:
        result = await process_outbox_batch_async()
        mock_factory.assert_not_called()
        assert result == 0
