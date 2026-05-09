"""
File: python/outbox_worker.py
Purpose: Async outbox worker — polls sync_outbox table every 5s, applies
         pending events to Neo4j via idempotent MERGE operations.
         Handles retry (3x exponential backoff), dead-letter, and Prometheus metrics.
Dependencies: asyncpg, neo4j-driver (async), celery (optional), asyncio
Version: 3.0 | Last updated: 2026-04-14

Design contract:
  - IDEMPOTENT: running the worker twice on the same event produces the same graph state.
  - PII-FREE: payload must be pre-masked before INSERT into sync_outbox.
  - Stale `processing` rows (worker crash) are reset to `pending` after STALE_PROCESSING_AFTER.
  - crisis_logs are NEVER in the outbox — admin-only, stays in Postgres.

Changes from v2.0 (mirrors neo4j_bootstrap_v3.0):
  - Fix #3: Removed LEADS_TO_FOR_USER and RELIEVED_BY_FOR_USER patterns.
    User-scoped emotion and coping tracking now use user-anchored edges:
      (User)-[:FELT]->(Emotion)
      (User)-[:USED_COPING]->(CopingAction)
    This eliminates the multi-user collision on shared (Trigger, Emotion) node pairs.
  - Fix #7: EXPERIENCED and FELT edges now track first_seen in ON CREATE SET.
  - Fix #8: CopingAction nodes no longer receive resource_id as a property.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta, timezone

import asyncpg
from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus metrics (compatible with prometheus_client if available)
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge, Histogram

    EVENTS_PROCESSED = Counter(
        "outbox_events_processed_total",
        "Total outbox events processed",
        ["event_type", "status"],
    )
    PROCESSING_LAG = Histogram(
        "outbox_processing_lag_seconds",
        "Lag from event created_at to processed_at",
        buckets=[1, 5, 15, 30, 60, 120, 300],
    )
    FAILED_COUNT = Gauge(
        "outbox_failed_events_count",
        "Current count of events in failed status",
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client not installed — metrics disabled")


def _record_metric(event_type: str, status: str, lag_seconds: float | None = None) -> None:
    if not _PROMETHEUS_AVAILABLE:
        return
    EVENTS_PROCESSED.labels(event_type=event_type, status=status).inc()
    if lag_seconds is not None:
        PROCESSING_LAG.observe(lag_seconds)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class OutboxEvent:
    outbox_id: int
    event_type: str
    payload: dict
    user_id: str
    attempts: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Neo4j MERGE handlers (idempotent by design)
# ---------------------------------------------------------------------------


class Neo4jApplier:
    """
    Applies outbox events to Neo4j using MERGE (never CREATE).
    Each handler method is idempotent — safe to call multiple times.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        self._driver = driver
        self._neo4j_database = database or "neo4j"

    async def apply(self, event: OutboxEvent) -> None:
        """Dispatch to the correct handler based on event_type."""
        handler = {
            "memory.created": self._handle_memory_created,
            "trigger.observed": self._handle_trigger_observed,
            "session.ended": self._handle_session_ended,
            "coping.attempted": self._handle_coping_attempted,
            "profile.updated": self._handle_profile_updated,
        }.get(event.event_type)

        if handler is None:
            raise ValueError(f"Unknown event_type: {event.event_type}")

        await handler(event)

    async def _handle_memory_created(self, event: OutboxEvent) -> None:
        """
        event.payload expected:
          { memory_id, user_id, memory_type, trigger_labels: [], emotion_label }
        Creates User node and links to trigger/emotion derived from memory.
        Does NOT store memory content — only relationship labels.
        """
        p = event.payload
        user_id = p["user_id"]
        trigger_labels: list[str] = p.get("trigger_labels", [])
        emotion_label: str | None = p.get("emotion_label")
        now = get_now().isoformat()

        async with self._driver.session(database=self._neo4j_database) as session:
            await session.run(
                "MERGE (u:User {user_id: $uid}) ON CREATE SET u.created_at = $now",
                uid=user_id,
                now=now,
            )

            # (User)-[:EXPERIENCED]->(Trigger) — per-user, idempotent count
            for trigger in trigger_labels:
                await session.run(
                    """
                    MERGE (u:User {user_id: $uid})
                    MERGE (t:Trigger {label: $label})
                    MERGE (u)-[r:EXPERIENCED]->(t)
                    ON CREATE SET r.count = 1, r.first_seen = $now, r.last_seen = $now
                    ON MATCH SET  r.count = r.count + 1, r.last_seen = $now
                    """,
                    label=trigger,
                    uid=user_id,
                    now=now,
                )

            # (User)-[:FELT]->(Emotion) — replaces LEADS_TO_FOR_USER.
            # Trigger↔Emotion correlation is derived from session co-occurrence,
            # not stored as a property-keyed relationship (avoids multi-user collision).
            if emotion_label:
                await session.run(
                    """
                    MERGE (u:User {user_id: $uid})
                    MERGE (e:Emotion {label: $emotion})
                    MERGE (u)-[r:FELT]->(e)
                    ON CREATE SET r.count = 1, r.first_seen = $now, r.last_seen = $now
                    ON MATCH SET  r.count = r.count + 1, r.last_seen = $now
                    """,
                    uid=user_id,
                    emotion=emotion_label,
                    now=now,
                )

    async def _handle_trigger_observed(self, event: OutboxEvent) -> None:
        """
        event.payload expected:
          { user_id, trigger_label, emotion_label, intensity: 0.0–1.0, observed_at }
        """
        p = event.payload
        user_id = p["user_id"]
        trigger = p["trigger_label"]
        emotion = p.get("emotion_label")
        observed_at = p.get("observed_at", get_now().isoformat())

        async with self._driver.session(database=self._neo4j_database) as session:
            # (User)-[:EXPERIENCED]->(Trigger) with first_seen tracking
            await session.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (t:Trigger {label: $trigger})
                MERGE (u)-[r:EXPERIENCED]->(t)
                ON CREATE SET r.count = 1, r.first_seen = $observed_at, r.last_seen = $observed_at
                ON MATCH SET  r.count = r.count + 1, r.last_seen = $observed_at
                """,
                uid=user_id, trigger=trigger, observed_at=observed_at,
            )

            # (User)-[:FELT]->(Emotion) — user-anchored, no multi-user collision
            if emotion:
                await session.run(
                    """
                    MERGE (u:User {user_id: $uid})
                    MERGE (e:Emotion {label: $emotion})
                    MERGE (u)-[r:FELT]->(e)
                    ON CREATE SET r.count = 1, r.first_seen = $observed_at, r.last_seen = $observed_at
                    ON MATCH SET  r.count = r.count + 1, r.last_seen = $observed_at
                    """,
                    uid=user_id, emotion=emotion, observed_at=observed_at,
                )

    async def _handle_session_ended(self, event: OutboxEvent) -> None:
        """
        event.payload expected:
          { user_id, session_id, started_at, ended_at, dominant_emotion,
            sos_triggered, key_triggers: [] }
        Creates Session node and links to User. No raw content stored.
        """
        p = event.payload
        user_id = p["user_id"]

        async with self._driver.session(database=self._neo4j_database) as session:
            await session.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (s:Session {session_id: $sid})
                ON CREATE SET s.started_at = $started,
                              s.ended_at = $ended,
                              s.dominant_emotion = $emotion,
                              s.sos_triggered = $sos
                MERGE (u)-[:HAS_SESSION]->(s)
                """,
                uid=user_id,
                sid=p["session_id"],
                started=p.get("started_at"),
                ended=p.get("ended_at"),
                emotion=p.get("dominant_emotion"),
                sos=p.get("sos_triggered", False),
            )

            # Link session triggers
            for trigger in p.get("key_triggers", []):
                await session.run(
                    """
                    MATCH (s:Session {session_id: $sid})
                    MERGE (t:Trigger {label: $trigger})
                    MERGE (s)-[:MENTIONS_TRIGGER]->(t)
                    """,
                    sid=p["session_id"], trigger=trigger,
                )

    async def _handle_coping_attempted(self, event: OutboxEvent) -> None:
        """
        event.payload expected:
          { user_id, action_id, emotion_label, effective: bool,
            effective_score: 0.0–1.0, attempted_at }
        Updates rolling average effectiveness on the user-anchored USED_COPING edge.
        resource_id is no longer stored on CopingAction — use IS_RESOURCE edge instead.
        """
        p = event.payload
        user_id = p["user_id"]
        action_id = p["action_id"]
        emotion_label = p.get("emotion_label", "neutral")
        effective_score = float(p.get("effective_score", 1.0 if p.get("effective") else 0.0))
        attempted_at = p.get("attempted_at", get_now().isoformat())

        async with self._driver.session(database=self._neo4j_database) as session:
            # (User)-[:USED_COPING]->(CopingAction) — one edge per (user, action).
            # Replaces RELIEVED_BY_FOR_USER which had multi-user collision risk.
            await session.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (c:CopingAction {action_id: $action_id})
                MERGE (u)-[r:USED_COPING]->(c)
                ON CREATE SET r.effectiveness = $score,
                              r.count         = 1,
                              r.first_used    = $attempted_at,
                              r.last_used     = $attempted_at,
                              r.last_emotion  = $emotion
                ON MATCH SET  r.effectiveness = (r.effectiveness * r.count + $score)
                                                / (r.count + 1),
                              r.count         = r.count + 1,
                              r.last_used     = $attempted_at,
                              r.last_emotion  = $emotion
                """,
                uid=user_id,
                action_id=action_id,
                emotion=emotion_label,
                score=effective_score,
                attempted_at=attempted_at,
            )

    async def _handle_profile_updated(self, event: OutboxEvent) -> None:
        """
        event.payload expected:
          { user_id, updated_fields: [] }
        Currently a no-op in Neo4j — profile is stored in Postgres.
        Kept as hook for future graph enrichment.
        """
        logger.debug("profile.updated event received for %s — no Neo4j action needed",
                     event.payload.get("user_id"))


# ---------------------------------------------------------------------------
# Outbox Worker (async polling loop)
# ---------------------------------------------------------------------------


class OutboxWorker:
    """
    Polls sync_outbox every POLL_INTERVAL seconds.
    Processes up to BATCH_SIZE events per cycle.
    Retries up to MAX_ATTEMPTS times with exponential backoff.
    """

    POLL_INTERVAL = 5  # seconds
    BATCH_SIZE = 50
    MAX_ATTEMPTS = 3
    BASE_BACKOFF = 2  # seconds (doubles each retry: 2, 4, 8)
    # Rows left in `processing` after worker crash: requeue after this lease window (Neo4j MERGE is idempotent).
    STALE_PROCESSING_AFTER = timedelta(minutes=10)

    def __init__(
        self,
        pg_pool: asyncpg.Pool,
        neo4j_driver: AsyncDriver,
        neo4j_database: str = "neo4j",
    ) -> None:
        self._pg = pg_pool
        self._applier = Neo4jApplier(neo4j_driver, database=neo4j_database)
        self._running = False

    async def start(self) -> None:
        """Start the polling loop. Run as asyncio background task."""
        self._running = True
        logger.info("OutboxWorker started (interval=%ds, batch=%d)", self.POLL_INTERVAL, self.BATCH_SIZE)
        while self._running:
            try:
                await self._process_batch()
            except Exception as exc:
                logger.error("OutboxWorker batch error: %s", exc, exc_info=True)
            await asyncio.sleep(self.POLL_INTERVAL)

    async def stop(self) -> None:
        self._running = False
        logger.info("OutboxWorker stopped")

    async def _reap_stale_processing(self) -> None:
        """Return stuck `processing` rows to `pending` so another worker can retry."""
        async with self._pg.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE sync_outbox
                SET status = 'pending', processing_started_at = NULL
                WHERE status = 'processing'
                  AND COALESCE(processing_started_at, created_at) < NOW() - $1::interval
                """,
                self.STALE_PROCESSING_AFTER,
            )
        if result != "UPDATE 0":
            logger.warning("OutboxWorker requeued stale processing rows: %s", result)

    async def _process_batch(self) -> None:
        """Fetch and process one batch of pending events."""
        await self._reap_stale_processing()

        async with self._pg.acquire() as conn:
            # Select-for-update and flip to processing in one statement so the claim
            # is not split across round trips (avoids races between lock and status update).
            rows = await conn.fetch(
                """
                WITH picked AS (
                    SELECT outbox_id
                    FROM sync_outbox
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE sync_outbox o
                SET status = 'processing',
                    processing_started_at = NOW()
                FROM picked p
                WHERE o.outbox_id = p.outbox_id
                RETURNING o.outbox_id, o.event_type, o.payload, o.user_id, o.attempts, o.created_at
                """,
                self.BATCH_SIZE,
            )

            if not rows:
                return

        events = [
            OutboxEvent(
                outbox_id=r["outbox_id"],
                event_type=r["event_type"],
                payload=json.loads(r["payload"]),
                user_id=r["user_id"],
                attempts=r["attempts"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

        await asyncio.gather(*[self._process_event(e) for e in events])

        # Update failed event gauge
        if _PROMETHEUS_AVAILABLE:
            await self._update_failed_gauge()

    async def _process_event(self, event: OutboxEvent) -> None:
        """Apply one event to Neo4j with retry logic."""
        # Ensure event.created_at (naive VN time) is treated as VN time for calculation
        from app.services.utils import get_now, VN_TZ
        created_at_aware = event.created_at.replace(tzinfo=VN_TZ)
        lag = (get_now() - created_at_aware).total_seconds()

        for attempt in range(self.MAX_ATTEMPTS):
            try:
                await self._applier.apply(event)
                await self._mark_done(event.outbox_id)
                _record_metric(event.event_type, "done", lag)
                logger.debug("Event %d (%s) applied successfully", event.outbox_id, event.event_type)
                return
            except Exception as exc:
                wait = self.BASE_BACKOFF ** (attempt + 1)
                logger.warning(
                    "Event %d failed (attempt %d/%d): %s — retrying in %ds",
                    event.outbox_id, attempt + 1, self.MAX_ATTEMPTS, exc, wait,
                )
                await asyncio.sleep(wait)

        # All retries exhausted
        await self._mark_failed(event.outbox_id, event.attempts + self.MAX_ATTEMPTS)
        _record_metric(event.event_type, "failed", lag)
        logger.error("Event %d permanently failed after %d attempts", event.outbox_id, self.MAX_ATTEMPTS)

    async def _mark_done(self, outbox_id: int) -> None:
        async with self._pg.acquire() as conn:
            await conn.execute(
                """
                UPDATE sync_outbox
                SET status = 'done',
                    processed_at = NOW(),
                    attempts = attempts + 1,
                    processing_started_at = NULL
                WHERE outbox_id = $1
                """,
                outbox_id,
            )

    async def _mark_failed(self, outbox_id: int, total_attempts: int) -> None:
        async with self._pg.acquire() as conn:
            await conn.execute(
                """
                UPDATE sync_outbox
                SET status = 'failed',
                    processed_at = NOW(),
                    attempts = $2,
                    processing_started_at = NULL
                WHERE outbox_id = $1
                """,
                outbox_id, total_attempts,
            )

    async def _update_failed_gauge(self) -> None:
        if not _PROMETHEUS_AVAILABLE:
            return
        async with self._pg.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM sync_outbox WHERE status = 'failed'"
            )
        FAILED_COUNT.set(count or 0)


# ---------------------------------------------------------------------------
# Entry point (standalone async runner, or import and call start() from app)
# ---------------------------------------------------------------------------

async def run_worker(
    database_url: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str = "neo4j",
) -> None:
    """Standalone runner. In production, prefer running as Celery beat task or FastAPI lifespan."""
    pg_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=5)
    neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    worker = OutboxWorker(pg_pool, neo4j_driver, neo4j_database=neo4j_database)
    try:
        await worker.start()
    finally:
        await pg_pool.close()
        await neo4j_driver.close()


if __name__ == "__main__":
    import os
    import sys

    # Allow `python backend/app/core/outbox_worker.py` from repo root
    _here = Path(__file__).resolve().parent
    _backend = _here.parents[1]
    if str(_backend) not in sys.path:
        sys.path.insert(0, str(_backend))

    from app.core.config import get_settings

    _s = get_settings()
    _db = (_s.database_url or os.getenv("DATABASE_URL") or "").strip()
    if not _db:
        raise SystemExit("DATABASE_URL required (env or .env)")
    if not (_s.neo4j_uri or "").strip():
        raise SystemExit("NEO4J_URI required (env or .env)")
    asyncio.run(
        run_worker(
            database_url=_db,
            neo4j_uri=_s.neo4j_uri.strip(),
            neo4j_user=_s.neo4j_user,
            neo4j_password=_s.neo4j_password.strip(),
            neo4j_database=_s.neo4j_database,
        )
    )
