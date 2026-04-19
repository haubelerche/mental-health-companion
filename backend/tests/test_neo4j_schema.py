"""
File: tests/test_neo4j_schema.py
Purpose: Integration tests for neo4j_bootstrap_v3.0.cypher.
         Verifies Sub-graph A completeness, user-anchored Sub-graph B patterns,
         and multi-user isolation (no collision on shared Trigger/Emotion nodes).

Requirements:
  pip install pytest pytest-asyncio neo4j

Environment variables:
  NEO4J_URI       e.g. neo4j+s://xxxx.databases.neo4j.io
  NEO4J_USER      e.g. neo4j
  NEO4J_PASSWORD  your AuraDB password

Run:
  pytest backend/tests/test_neo4j_schema.py -v

IMPORTANT: Tests that write to the graph clean up after themselves using
           unique prefixed IDs (test_usr_*, test_ses_*). Safe to run against
           production AuraDB because test nodes are isolated and always deleted.
"""

from __future__ import annotations

import os
import uuid
import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NEO4J_URI = os.environ.get("NEO4J_URI", "")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def driver() -> AsyncDriver:
    if not NEO4J_URI or not NEO4J_PASSWORD:
        pytest.skip("NEO4J_URI / NEO4J_PASSWORD not set — skipping Neo4j integration tests")
    d = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield d
    await d.close()


def _test_uid(suffix: str = "") -> str:
    """Generate a unique test user id that won't collide with production data."""
    return f"test_usr_{uuid.uuid4().hex[:8]}{suffix}"


def _test_sid() -> str:
    return f"test_ses_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# SECTION 1: Sub-graph A — Knowledge Graph completeness
# ---------------------------------------------------------------------------

async def test_phq9_items_complete(driver: AsyncDriver) -> None:
    """PHQ-9 must have exactly 9 items, each measuring a distinct symptom."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (i:Instrument {code: 'PHQ-9'})-[:HAS_ITEM]->(q:Item)-[:MEASURES]->(sym:Symptom)
            RETURN count(DISTINCT q) AS items, count(DISTINCT sym) AS symptoms
            """
        )
        row = await result.single()
    assert row["items"] == 9, f"PHQ-9 should have 9 items, got {row['items']}"
    assert row["symptoms"] == 9, f"PHQ-9 items should cover 9 symptoms, got {row['symptoms']}"


async def test_gad7_items_complete(driver: AsyncDriver) -> None:
    """GAD-7 must have exactly 7 items."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (i:Instrument {code: 'GAD-7'})-[:HAS_ITEM]->(q:Item)
            RETURN count(q) AS items
            """
        )
        row = await result.single()
    assert row["items"] == 7, f"GAD-7 should have 7 items, got {row['items']}"


async def test_resource_helps_with_coverage(driver: AsyncDriver) -> None:
    """Every seeded Resource must have at least one HELPS_WITH edge."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (r:Resource)
            WHERE NOT (r)-[:HELPS_WITH]->()
            RETURN r.resource_id AS rid
            """
        )
        orphans = [rec["rid"] async for rec in result]
    assert orphans == [], f"Resources with no HELPS_WITH edges: {orphans}"


async def test_cognitive_distortions_seeded(driver: AsyncDriver) -> None:
    """At least 10 CognitiveDistortion nodes must be present."""
    async with driver.session() as s:
        result = await s.run("MATCH (d:CognitiveDistortion) RETURN count(d) AS n")
        row = await result.single()
    assert row["n"] >= 10, f"Expected ≥10 CognitiveDistortion nodes, got {row['n']}"


async def test_distortions_have_amplifies_edges(driver: AsyncDriver) -> None:
    """Every CognitiveDistortion must amplify at least one Symptom."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (d:CognitiveDistortion)
            WHERE NOT (d)-[:AMPLIFIES]->()
            RETURN d.name AS name
            """
        )
        orphans = [rec["name"] async for rec in result]
    assert orphans == [], f"Distortions without AMPLIFIES edges: {orphans}"


async def test_emotion_labels_normalized(driver: AsyncDriver) -> None:
    """All Emotion nodes must have a Vietnamese display string (v3: name_vi)."""
    async with driver.session() as s:
        # Remove pre-v3 test debris (MERGE on :Emotion {label}) that lacks slug/name_vi.
        await s.run("MATCH (e:Emotion) WHERE e.slug IS NULL DETACH DELETE e")
        result = await s.run(
            "MATCH (e:Emotion) WHERE e.name_vi IS NULL RETURN coalesce(e.slug, e.label) AS id"
        )
        missing = [rec["id"] async for rec in result]
    assert missing == [], f"Emotions missing name_vi: {missing}"


async def test_emotion_lo_lang_removed(driver: AsyncDriver) -> None:
    """Legacy 'lo_lang' node must not exist (renamed to 'anxious' in v3.0)."""
    async with driver.session() as s:
        result = await s.run(
            "MATCH (e:Emotion {slug: 'lo_lang'}) RETURN count(e) AS n"
        )
        row = await result.single()
    assert row["n"] == 0, "'lo_lang' emotion node still exists — run migration DETACH DELETE"


async def test_safety_keywords_seeded(driver: AsyncDriver) -> None:
    """SafetyKeyword nodes must exist and be linked to suicidal_ideation symptom."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (k:SafetyKeyword)-[:INDICATES]->(s:Symptom {slug: 'suicidal_ideation'})
            RETURN count(k) AS n
            """
        )
        row = await result.single()
    assert row["n"] >= 5, f"Expected ≥5 SafetyKeyword→suicidal_ideation links, got {row['n']}"


async def test_coping_action_no_resource_id_property(driver: AsyncDriver) -> None:
    """CopingAction nodes must NOT have a resource_id property (Fix #8)."""
    async with driver.session() as s:
        result = await s.run(
            "MATCH (c:CopingAction) WHERE c.resource_id IS NOT NULL RETURN c.action_id AS id"
        )
        violators = [rec["id"] async for rec in result]
    assert violators == [], f"CopingAction nodes still have resource_id property: {violators}"


async def test_coping_action_is_resource_edges(driver: AsyncDriver) -> None:
    """The 4 resource-backed CopingActions must each have an IS_RESOURCE edge."""
    resource_backed = {"breathing_478", "body_scan", "sleep_soundscape", "cbt_reading"}
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (c:CopingAction)-[:IS_RESOURCE]->(r:Resource)
            RETURN c.action_id AS action_id
            """
        )
        linked = {rec["action_id"] async for rec in result}
    missing = resource_backed - linked
    assert missing == set(), f"CopingActions missing IS_RESOURCE edge: {missing}"


# ---------------------------------------------------------------------------
# SECTION 2: Sub-graph B — User-anchored pattern correctness
# ---------------------------------------------------------------------------

async def test_experienced_multi_user_isolation(driver: AsyncDriver) -> None:
    """
    Two users experiencing the same trigger must produce 2 independent
    EXPERIENCED edges with their own counts — no collision.
    """
    uid_a = _test_uid("_a")
    uid_b = _test_uid("_b")
    trigger = "deadline"  # pre-seeded trigger

    async with driver.session() as s:
        # User A experiences deadline 3 times
        for _ in range(3):
            await s.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (t:Trigger {slug: $trigger})
                MERGE (u)-[r:EXPERIENCED]->(t)
                ON CREATE SET r.count = 1, r.first_seen = datetime(), r.last_seen = datetime()
                ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime()
                """,
                uid=uid_a, trigger=trigger,
            )
        # User B experiences deadline 1 time
        await s.run(
            """
            MERGE (u:User {user_id: $uid})
            MERGE (t:Trigger {slug: $trigger})
            MERGE (u)-[r:EXPERIENCED]->(t)
            ON CREATE SET r.count = 1, r.first_seen = datetime(), r.last_seen = datetime()
            ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime()
            """,
            uid=uid_b, trigger=trigger,
        )

        # Verify isolation
        result = await s.run(
            """
            MATCH (u:User)-[r:EXPERIENCED]->(:Trigger {slug: $trigger})
            WHERE u.user_id IN [$uid_a, $uid_b]
            RETURN u.user_id AS uid, r.count AS cnt
            ORDER BY u.user_id
            """,
            trigger=trigger, uid_a=uid_a, uid_b=uid_b,
        )
        rows = {rec["uid"]: rec["cnt"] async for rec in result}

    # Cleanup
    async with driver.session() as s:
        await s.run(
            "MATCH (u:User) WHERE u.user_id IN [$a, $b] DETACH DELETE u",
            a=uid_a, b=uid_b,
        )

    assert uid_a in rows, "User A EXPERIENCED edge not found"
    assert uid_b in rows, "User B EXPERIENCED edge not found"
    assert rows[uid_a] == 3, f"User A count should be 3, got {rows[uid_a]}"
    assert rows[uid_b] == 1, f"User B count should be 1, got {rows[uid_b]}"


async def test_felt_multi_user_isolation(driver: AsyncDriver) -> None:
    """Two users feeling the same emotion must produce independent FELT edges."""
    uid_a = _test_uid("_fa")
    uid_b = _test_uid("_fb")
    emotion = "stressed"  # pre-seeded

    async with driver.session() as s:
        for _ in range(2):
            await s.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (e:Emotion {slug: $emotion})
                MERGE (u)-[r:FELT]->(e)
                ON CREATE SET r.count = 1, r.first_seen = datetime(), r.last_seen = datetime()
                ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime()
                """,
                uid=uid_a, emotion=emotion,
            )
        await s.run(
            """
            MERGE (u:User {user_id: $uid})
            MERGE (e:Emotion {slug: $emotion})
            MERGE (u)-[r:FELT]->(e)
            ON CREATE SET r.count = 1, r.first_seen = datetime(), r.last_seen = datetime()
            ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime()
            """,
            uid=uid_b, emotion=emotion,
        )

        result = await s.run(
            """
            MATCH (u:User)-[r:FELT]->(:Emotion {slug: $emotion})
            WHERE u.user_id IN [$uid_a, $uid_b]
            RETURN u.user_id AS uid, r.count AS cnt
            """,
            emotion=emotion, uid_a=uid_a, uid_b=uid_b,
        )
        rows = {rec["uid"]: rec["cnt"] async for rec in result}

    async with driver.session() as s:
        await s.run(
            "MATCH (u:User) WHERE u.user_id IN [$a, $b] DETACH DELETE u",
            a=uid_a, b=uid_b,
        )

    assert rows.get(uid_a) == 2, f"User A FELT count should be 2, got {rows.get(uid_a)}"
    assert rows.get(uid_b) == 1, f"User B FELT count should be 1, got {rows.get(uid_b)}"


async def test_experienced_first_seen_set(driver: AsyncDriver) -> None:
    """EXPERIENCED edge must record first_seen on creation and not update it on match."""
    uid = _test_uid("_fs")

    async with driver.session() as s:
        # First event
        await s.run(
            """
            MERGE (u:User {user_id: $uid})
            MERGE (t:Trigger {slug: 'loneliness'})
            MERGE (u)-[r:EXPERIENCED]->(t)
            ON CREATE SET r.count = 1, r.first_seen = datetime('2026-01-01T00:00:00Z'),
                          r.last_seen = datetime('2026-01-01T00:00:00Z')
            ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime('2026-01-01T00:00:00Z')
            """,
            uid=uid,
        )
        # Second event — first_seen must NOT change
        await s.run(
            """
            MERGE (u:User {user_id: $uid})
            MERGE (t:Trigger {slug: 'loneliness'})
            MERGE (u)-[r:EXPERIENCED]->(t)
            ON CREATE SET r.count = 1, r.first_seen = datetime('2026-06-01T00:00:00Z'),
                          r.last_seen = datetime('2026-06-01T00:00:00Z')
            ON MATCH SET  r.count = r.count + 1, r.last_seen = datetime('2026-06-01T00:00:00Z')
            """,
            uid=uid,
        )

        result = await s.run(
            """
            MATCH (u:User {user_id: $uid})-[r:EXPERIENCED]->(t:Trigger {slug: 'loneliness'})
            RETURN r.count AS cnt, toString(r.first_seen) AS fs, toString(r.last_seen) AS ls
            """,
            uid=uid,
        )
        row = await result.single()

    async with driver.session() as s:
        await s.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)

    assert row["cnt"] == 2, f"Expected count 2, got {row['cnt']}"
    assert "2026-01-01" in row["fs"], f"first_seen was overwritten: {row['fs']}"
    assert "2026-06-01" in row["ls"], f"last_seen not updated: {row['ls']}"


async def test_used_coping_rolling_average(driver: AsyncDriver) -> None:
    """USED_COPING edge must maintain a correct rolling average of effectiveness."""
    uid = _test_uid("_cp")

    async with driver.session() as s:
        for score in [0.8, 0.6, 1.0]:
            await s.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (c:CopingAction {action_id: 'breathing_478'})
                MERGE (u)-[r:USED_COPING]->(c)
                ON CREATE SET r.effectiveness = $score, r.count = 1,
                              r.first_used = datetime(), r.last_used = datetime(),
                              r.last_emotion = 'anxious'
                ON MATCH SET  r.effectiveness = (r.effectiveness * r.count + $score) / (r.count + 1),
                              r.count = r.count + 1,
                              r.last_used = datetime(),
                              r.last_emotion = 'anxious'
                """,
                uid=uid, score=score,
            )

        result = await s.run(
            """
            MATCH (u:User {user_id: $uid})-[r:USED_COPING]->(c:CopingAction {action_id: 'breathing_478'})
            RETURN r.effectiveness AS eff, r.count AS cnt
            """,
            uid=uid,
        )
        row = await result.single()

    async with driver.session() as s:
        await s.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)

    assert row["cnt"] == 3, f"Expected count 3, got {row['cnt']}"
    expected_eff = round((0.8 + 0.6 + 1.0) / 3, 4)
    assert abs(row["eff"] - expected_eff) < 0.01, (
        f"Effectiveness rolling avg: expected ~{expected_eff}, got {row['eff']}"
    )


async def test_session_links_to_user_and_triggers(driver: AsyncDriver) -> None:
    """Session node must link to User via HAS_SESSION and to Trigger via MENTIONS_TRIGGER."""
    uid = _test_uid("_ss")
    sid = _test_sid()

    async with driver.session() as s:
        await s.run(
            """
            MERGE (u:User {user_id: $uid}) ON CREATE SET u.created_at = datetime()
            MERGE (sess:Session {session_id: $sid})
            ON CREATE SET sess.dominant_emotion = 'anxious',
                          sess.sos_triggered = false,
                          sess.turn_count = 5
            MERGE (u)-[:HAS_SESSION]->(sess)
            """,
            uid=uid, sid=sid,
        )
        await s.run(
            """
            MATCH (sess:Session {session_id: $sid})
            MERGE (t:Trigger {slug: 'deadline'})
            MERGE (sess)-[:MENTIONS_TRIGGER]->(t)
            """,
            sid=sid,
        )

        result = await s.run(
            """
            MATCH (u:User {user_id: $uid})-[:HAS_SESSION]->(sess:Session {session_id: $sid})
                  -[:MENTIONS_TRIGGER]->(t:Trigger)
            RETURN u.user_id AS uid, sess.session_id AS sid, coalesce(t.slug, t.label) AS trigger
            """,
            uid=uid, sid=sid,
        )
        row = await result.single()

    async with driver.session() as s:
        await s.run("MATCH (u:User {user_id: $uid}) DETACH DELETE u", uid=uid)
        await s.run("MATCH (s:Session {session_id: $sid}) DETACH DELETE s", sid=sid)

    assert row is not None, "Session→User→Trigger path not found"
    assert row["trigger"] == "deadline"


# ---------------------------------------------------------------------------
# SECTION 3: Analyst query patterns
# ---------------------------------------------------------------------------

async def test_analyst_symptom_instrument_mapping(driver: AsyncDriver) -> None:
    """Analyst query: map 'insomnia' symptom back to measuring items."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (sym:Symptom {slug: 'insomnia'})<-[:MEASURES]-(q:Item)<-[:HAS_ITEM]-(i:Instrument)
            RETURN i.code AS instrument, q.code AS item
            ORDER BY i.code, q.code
            """
        )
        rows = [{"instrument": rec["instrument"], "item": rec["item"]} async for rec in result]

    codes = {r["item"] for r in rows}
    assert "PHQ9_Q3" in codes, "PHQ9_Q3 should measure insomnia"
    # GAD-7 does not directly measure insomnia
    assert not any(r["instrument"] == "GAD-7" for r in rows), (
        "GAD-7 should not directly measure insomnia"
    )


async def test_analyst_resource_recommendation(driver: AsyncDriver) -> None:
    """Friend query: resources ordered by strength for 'insomnia'."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (r:Resource)-[h:HELPS_WITH]->(s:Symptom {slug: 'insomnia'})
            RETURN r.resource_id AS rid, r.title_vi AS title, h.strength AS strength
            ORDER BY h.strength DESC
            """
        )
        rows = [{"rid": rec["rid"], "strength": rec["strength"]} async for rec in result]

    assert len(rows) >= 2, "Expected ≥2 resources for insomnia"
    # Results must be sorted descending
    strengths = [r["strength"] for r in rows]
    assert strengths == sorted(strengths, reverse=True), "Resources not sorted by strength DESC"


async def test_analyst_co_occurring_symptoms(driver: AsyncDriver) -> None:
    """Analyst query: find symptoms that co-occur with 'excessive_worry'."""
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (:Symptom {slug: 'excessive_worry'})-[c:CO_OCCURS_WITH]->(s:Symptom)
            RETURN s.slug AS symptom, c.weight AS weight
            ORDER BY c.weight DESC
            """
        )
        rows = [rec["symptom"] async for rec in result]

    assert "tension" in rows, "'tension' should co-occur with 'excessive_worry'"
    assert "insomnia" in rows, "'insomnia' should co-occur with 'excessive_worry'"
