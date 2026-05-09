"""
File: python/profile_service.py
Purpose: ProfileService — read/write user profiles with Redis cache (30s TTL)
         and Postgres JSONB backend. Handles concurrent writes via optimistic
         concurrency (version field). Gracefully degrades if Redis is unavailable.
Dependencies: asyncpg, redis-py (async), pydantic v2, jsonschema
Version: 2.0 | Last updated: 2026-04-14
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from app.services.utils import get_now, local_date_utc7

import asyncpg
import jsonschema
import redis.asyncio as aioredis
from pydantic import BaseModel, Field, field_validator
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic v2 Models
# ---------------------------------------------------------------------------


class Bio(BaseModel):
    """User bio — no PII, initials/nickname only."""

    display_name_hint: str | None = None
    age_range: str | None = None
    role: str | None = None
    language: str = "vi"
    timezone: str | None = "Asia/Ho_Chi_Minh"


class Traits(BaseModel):
    """Long-term communication and preference traits."""

    communication_style: str | None = None
    preferred_tone: str | None = None
    response_length_pref: str | None = None
    openness_to_exercise: float | None = None
    openness_to_journaling: float | None = None


class ClinicalSnapshot(BaseModel):
    """Denormalized copy of clinical_profiles — internal only, never expose to FE."""

    phq9_score: int | None = None
    gad7_score: int | None = None
    phq9_coverage: dict[str, bool] = Field(default_factory=dict)
    gad7_coverage: dict[str, bool] = Field(default_factory=dict)
    crisis_level: int = 0
    last_scored_at: datetime | None = None
    trend_7d: str | None = None

    @field_validator("phq9_score")
    @classmethod
    def validate_phq9(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 27):
            raise ValueError("phq9_score must be 0–27")
        return v

    @field_validator("gad7_score")
    @classmethod
    def validate_gad7(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 21):
            raise ValueError("gad7_score must be 0–21")
        return v

    @field_validator("crisis_level")
    @classmethod
    def validate_crisis(cls, v: int) -> int:
        if not (0 <= v <= 5):
            raise ValueError("crisis_level must be 0–5")
        return v


class SessionSummary(BaseModel):
    """One session summary entry stored in profile.session_summaries[]."""

    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    turn_count: int = 1
    summary: str = Field(max_length=500)
    summary_embedding_ref: str | None = None
    dominant_emotion: str | None = None
    key_triggers: list[str] = Field(default_factory=list)
    resources_suggested: list[str] = Field(default_factory=list)
    resources_engaged: list[str] = Field(default_factory=list)
    sos_triggered: bool = False
    crisis_level_peak: int = 0


class TriggerTag(BaseModel):
    """Aggregated trigger occurrence data."""

    count: int = 1
    last_seen: datetime = Field(default_factory=get_now)
    avg_intensity: float | None = None


class CopingEntry(BaseModel):
    """One coping action record in coping_history."""

    action: str
    resource_id: str | None = None
    tried_count: int = 1
    self_reported_effective: int = 0
    last_tried: str | None = None  # ISO date string


class Goal(BaseModel):
    goal_id: str
    text: str
    set_at: datetime
    status: str = "active"
    completed_at: datetime | None = None


class SafetyFlags(BaseModel):
    ever_sos_triggered: bool = False
    last_sos_at: datetime | None = None
    admin_reviewed: bool = False
    do_not_suggest_topics: list[str] = Field(default_factory=list)


class Stats(BaseModel):
    total_sessions: int = 0
    total_messages_user: int = 0
    avg_session_length_turns: float | None = None
    days_active_last_30: int = 0
    streak_days: int = 0


class Meta(BaseModel):
    last_rollup_at: datetime | None = None
    next_rollup_at: datetime | None = None
    pii_masked: bool = True
    weekly_note_content: str | None = None
    weekly_note_generated_at: datetime | None = None


class UserProfile(BaseModel):
    """Full user profile object. Maps to user_profiles.profile JSONB column."""

    schema_version: str = "v1"
    bio: Bio = Field(default_factory=Bio)
    traits: Traits = Field(default_factory=Traits)
    clinical_snapshot: ClinicalSnapshot = Field(default_factory=ClinicalSnapshot)
    session_summaries: list[SessionSummary] = Field(default_factory=list)
    trigger_tags: dict[str, TriggerTag] = Field(default_factory=dict)
    coping_history: list[CopingEntry] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)
    safety_flags: SafetyFlags = Field(default_factory=SafetyFlags)
    stats: Stats = Field(default_factory=Stats)
    meta: Meta = Field(default_factory=Meta)

    # Max 50 summaries in hot profile (FIFO)
    MAX_SUMMARIES: int = 50

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# ProfileService
# ---------------------------------------------------------------------------

_PROFILE_JSON_SCHEMA: dict | None = None


def _load_json_schema() -> dict:
    """Load and cache JSON Schema from schema/user_profile_schema.json."""
    global _PROFILE_JSON_SCHEMA
    if _PROFILE_JSON_SCHEMA is None:
        import pathlib
        schema_path = pathlib.Path(__file__).parent.parent / "data" / "user_profile_schema.json"
        with open(schema_path) as f:
            _PROFILE_JSON_SCHEMA = json.load(f)
    return _PROFILE_JSON_SCHEMA


class ProfileService:
    """
    Service for reading and writing user profiles.

    Cache strategy:
      - Redis key: profile:{user_id} (TTL 30s)
      - On cache miss: load from Postgres, repopulate cache
      - On Redis failure: fall through to Postgres (graceful degradation)
      - On write: invalidate Redis key immediately

    Concurrency:
      - Uses optimistic concurrency via `version` column.
      - On conflict (version mismatch): retry up to 3 times with fresh read.
    """

    CACHE_TTL = 30  # seconds
    MAX_RETRY = 3

    def __init__(self, pg_pool: asyncpg.Pool, redis_client: aioredis.Redis | None) -> None:
        self._pg = pg_pool
        self._redis = redis_client

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def get_profile(self, user_id: str) -> UserProfile:
        """
        Return UserProfile for user_id.
        Reads from Redis cache (30s TTL), falls back to Postgres on miss/error.
        """
        # Try cache first
        cached = await self._cache_get(user_id)
        if cached is not None:
            return UserProfile.model_validate_json(cached)

        # Load from Postgres
        profile = await self._load_from_postgres(user_id)
        await self._cache_set(user_id, profile)
        return profile

    async def create_profile(self, user_id: str) -> UserProfile:
        """
        Create a new empty profile row for user_id (called at signup).
        Raises ValueError if profile already exists.
        """
        profile = UserProfile()
        profile_json = profile.model_dump_json()

        async with self._pg.acquire() as conn:
            await self._set_rls_context(conn, user_id, role="service")
            try:
                await conn.execute(
                    """
                    INSERT INTO user_profiles
                        (user_id, version, schema_version, profile,
                         current_crisis_level, summary_count)
                    VALUES ($1, 1, 'v1', $2::jsonb, 0, 0)
                    """,
                    user_id,
                    profile_json,
                )
            except asyncpg.UniqueViolationError:
                raise ValueError(f"Profile already exists for user_id={user_id}")

        await self._cache_set(user_id, profile)
        return profile

    async def update_traits(self, user_id: str, traits: dict[str, Any]) -> None:
        """
        Partially update profile.traits using JSONB merge.
        Handles optimistic concurrency — retries on version conflict.
        """
        for attempt in range(self.MAX_RETRY):
            async with self._pg.acquire() as conn:
                await self._set_rls_context(conn, user_id, role="service")
                row = await conn.fetchrow(
                    "SELECT version FROM user_profiles WHERE user_id = $1 FOR UPDATE",
                    user_id,
                )
                if row is None:
                    raise LookupError(f"Profile not found for user_id={user_id}")

                current_version = row["version"]
                result = await conn.execute(
                    """
                    UPDATE user_profiles
                    SET profile = jsonb_set(profile, '{traits}',
                                    COALESCE(profile->'traits', '{}') || $1::jsonb),
                        version = version + 1,
                        updated_at = NOW()
                    WHERE user_id = $2 AND version = $3
                    """,
                    json.dumps(traits),
                    user_id,
                    current_version,
                )
                if result == "UPDATE 1":
                    await self.invalidate_cache(user_id)
                    return

            logger.warning("Trait update version conflict for %s, retry %d", user_id, attempt + 1)

        raise RuntimeError(f"Failed to update traits after {self.MAX_RETRY} retries for {user_id}")

    async def append_session_summary(
        self, user_id: str, summary: SessionSummary
    ) -> list[dict]:
        """
        Append a SessionSummary to profile.session_summaries[].
        Maintains FIFO cap of 50. Overflow items returned for archiving.

        Returns: list of overflow summary dicts that caller should INSERT
                 into session_summaries_archive.
        """
        summary_dict = json.loads(summary.model_dump_json())
        overflow: list[dict] = []

        for attempt in range(self.MAX_RETRY):
            async with self._pg.acquire() as conn:
                await self._set_rls_context(conn, user_id, role="service")
                row = await conn.fetchrow(
                    "SELECT version, profile FROM user_profiles WHERE user_id = $1 FOR UPDATE",
                    user_id,
                )
                if row is None:
                    raise LookupError(f"Profile not found: {user_id}")

                current_version = row["version"]
                current_profile = json.loads(row["profile"])
                summaries: list = current_profile.get("session_summaries", [])

                # Prepend new summary (newest first)
                summaries.insert(0, summary_dict)

                # Extract overflow (entries beyond cap)
                if len(summaries) > UserProfile.MAX_SUMMARIES:
                    overflow = summaries[UserProfile.MAX_SUMMARIES:]
                    summaries = summaries[: UserProfile.MAX_SUMMARIES]

                current_profile["session_summaries"] = summaries
                new_count = len(summaries)

                result = await conn.execute(
                    """
                    UPDATE user_profiles
                    SET profile = $1::jsonb,
                        summary_count = $2,
                        version = version + 1,
                        updated_at = NOW()
                    WHERE user_id = $3 AND version = $4
                    """,
                    json.dumps(current_profile),
                    new_count,
                    user_id,
                    current_version,
                )
                if result == "UPDATE 1":
                    await self.invalidate_cache(user_id)
                    return overflow

        raise RuntimeError(f"Failed to append session summary after {self.MAX_RETRY} retries")

    async def increment_trigger_tag(
        self, user_id: str, tag: str, intensity: float
    ) -> None:
        """
        Increment trigger_tags[tag].count and update avg_intensity.
        Uses atomic JSONB update (no version field conflict). Retries on
        transient Postgres errors; raises LookupError if no profile row exists.
        """
        if not (0.0 <= intensity <= 1.0):
            raise ValueError(f"intensity must be 0.0–1.0, got {intensity}")

        now_iso = get_now().isoformat()

        for attempt in range(self.MAX_RETRY):
            try:
                async with self._pg.acquire() as conn:
                    await self._set_rls_context(conn, user_id, role="service")
                    result = await conn.execute(
                        """
                        UPDATE user_profiles
                        SET profile = jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    profile,
                                    ARRAY['trigger_tags', $2, 'count'],
                                    (COALESCE(
                                        (profile->'trigger_tags'->$2->>'count')::int, 0
                                    ) + 1)::text::jsonb
                                ),
                                ARRAY['trigger_tags', $2, 'last_seen'],
                                to_jsonb($3::text)
                            ),
                            ARRAY['trigger_tags', $2, 'avg_intensity'],
                            (
                                (COALESCE((profile->'trigger_tags'->$2->>'avg_intensity')::numeric, 0)
                                 * COALESCE((profile->'trigger_tags'->$2->>'count')::int, 0)
                                 + $4::numeric)
                                / (COALESCE((profile->'trigger_tags'->$2->>'count')::int, 0) + 1)
                            )::text::jsonb
                        ),
                        updated_at = NOW()
                        WHERE user_id = $1
                        """,
                        user_id, tag, now_iso, intensity,
                    )
            except asyncpg.exceptions.PostgresError as exc:
                if attempt + 1 >= self.MAX_RETRY:
                    raise
                logger.warning(
                    "increment_trigger_tag: transient DB error for %s (attempt %d/%d): %s",
                    user_id,
                    attempt + 1,
                    self.MAX_RETRY,
                    exc,
                )
                continue

            if result == "UPDATE 1":
                await self.invalidate_cache(user_id)
                return
            raise LookupError(f"Profile not found: {user_id}")

    async def record_coping_attempt(
        self, user_id: str, action: str, resource_id: str | None, effective: bool
    ) -> None:
        """
        Upsert coping_history entry for action. Increments tried_count and
        self_reported_effective if effective=True.
        """
        for attempt in range(self.MAX_RETRY):
            async with self._pg.acquire() as conn:
                await self._set_rls_context(conn, user_id, role="service")
                row = await conn.fetchrow(
                    "SELECT version, profile FROM user_profiles WHERE user_id = $1 FOR UPDATE",
                    user_id,
                )
                if row is None:
                    raise LookupError(f"Profile not found: {user_id}")

                current_version = row["version"]
                profile = json.loads(row["profile"])
                history: list = profile.get("coping_history", [])

                today = local_date_utc7().isoformat()
                entry = next((e for e in history if e["action"] == action), None)

                if entry is None:
                    history.append({
                        "action": action,
                        "resource_id": resource_id,
                        "tried_count": 1,
                        "self_reported_effective": 1 if effective else 0,
                        "last_tried": today,
                    })
                else:
                    entry["tried_count"] += 1
                    if effective:
                        entry["self_reported_effective"] = entry.get("self_reported_effective", 0) + 1
                    entry["last_tried"] = today

                profile["coping_history"] = history
                result = await conn.execute(
                    """
                    UPDATE user_profiles
                    SET profile = $1::jsonb, version = version + 1, updated_at = NOW()
                    WHERE user_id = $2 AND version = $3
                    """,
                    json.dumps(profile), user_id, current_version,
                )
                if result == "UPDATE 1":
                    await self.invalidate_cache(user_id)
                    return

        raise RuntimeError(f"Failed to record coping attempt after {self.MAX_RETRY} retries")

    async def snapshot(self, user_id: str, reason: str) -> int:
        """
        Write current profile to user_profile_snapshots.
        Returns snapshot_id of created row.
        """
        allowed_reasons = {
            "session_end", "weekly_rollup", "crisis_event",
            "trait_update", "manual", "migration",
        }
        if reason not in allowed_reasons:
            raise ValueError(f"Invalid snapshot reason: {reason}")

        async with self._pg.acquire() as conn:
            await self._set_rls_context(conn, user_id, role="service")
            row = await conn.fetchrow(
                "SELECT version, profile FROM user_profiles WHERE user_id = $1",
                user_id,
            )
            if row is None:
                raise LookupError(f"Profile not found: {user_id}")

            snapshot_id = await conn.fetchval(
                """
                INSERT INTO user_profile_snapshots (user_id, version, profile, reason)
                VALUES ($1, $2, $3::jsonb, $4)
                ON CONFLICT (user_id, version) DO NOTHING
                RETURNING snapshot_id
                """,
                user_id, row["version"], row["profile"], reason,
            )
        return snapshot_id

    async def invalidate_cache(self, user_id: str) -> None:
        """Remove profile from Redis cache. No-op if Redis unavailable."""
        if self._redis is None:
            return
        try:
            await self._redis.delete(self._cache_key(user_id))
        except RedisError as exc:
            logger.warning("Redis cache invalidation failed for %s: %s", user_id, exc)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _cache_key(user_id: str) -> str:
        return f"profile:{user_id}"

    async def _cache_get(self, user_id: str) -> str | None:
        if self._redis is None:
            return None
        try:
            return await self._redis.get(self._cache_key(user_id))
        except RedisError as exc:
            logger.warning("Redis cache read failed for %s: %s", user_id, exc)
            return None

    async def _cache_set(self, user_id: str, profile: UserProfile) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.setex(
                self._cache_key(user_id),
                self.CACHE_TTL,
                profile.model_dump_json(),
            )
        except RedisError as exc:
            logger.warning("Redis cache write failed for %s: %s", user_id, exc)

    async def _load_from_postgres(self, user_id: str) -> UserProfile:
        async with self._pg.acquire() as conn:
            await self._set_rls_context(conn, user_id, role="service")
            row = await conn.fetchrow(
                "SELECT profile FROM user_profiles WHERE user_id = $1",
                user_id,
            )
        if row is None:
            raise LookupError(f"Profile not found for user_id={user_id}")
        return UserProfile.model_validate(json.loads(row["profile"]))

    @staticmethod
    async def _set_rls_context(
        conn: asyncpg.Connection, user_id: str, role: str = "app"
    ) -> None:
        """Set session vars for RLS policies (consistent with DB_SCHEMA v1.2)."""
        await conn.execute(
            "SET LOCAL app.current_user_id = $1; SET LOCAL app.current_role = $2",
            user_id, role,
        )

    def validate_profile_json(self, profile_dict: dict) -> None:
        """Validate profile dict against JSON Schema draft-07. Raises jsonschema.ValidationError."""
        schema = _load_json_schema()
        jsonschema.validate(instance=profile_dict, schema=schema)
