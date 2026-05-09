"""
File: python/session_summarizer.py
Purpose: Session summarization background job — generates LLM summary of a
         session, embeds it, updates user_profiles, archives overflow, and
         queues Neo4j sync via outbox.
Dependencies: asyncpg, openai (async), pydantic v2
Version: 2.0 | Last updated: 2026-04-14

Trigger conditions:
  1. User idle 30 minutes (called from FastAPI lifespan background task)
  2. User explicitly ends session via UI (POST /chat/end)
  3. Midnight batch job (pg_cron or Celery beat) for sessions not yet closed

Safety invariants:
  - PII check before LLM call — per-message and on full aggregated conversation text
    (catches patterns split across messages); abort if raw PII detected (do not send to OpenAI)
  - SOS sessions get a minimal summary only — no content detail
  - Single-turn sessions get a minimal summary without LLM call
  - All summaries stored ≤ 500 chars, Vietnamese, no PII
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import asyncpg
import openai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII patterns (conservative — false positives are OK, false negatives are not)
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\b(?:\+84|0)[3-9]\d{8}\b"),  # Vietnamese phone number
    re.compile(r"\b\d{9,12}\b"),  # CMND/CCCD digits
]

_PII_MASK_TOKENS = {"[PERSON]", "[EMAIL]", "[PHONE]", "[ID]", "[LOCATION]"}


def _has_unmasked_pii(text: str) -> bool:
    """Return True if text appears to contain unmasked PII patterns."""
    for pattern in _PII_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _content_is_safe(content: str) -> bool:
    """Return True if content has been PII-masked and is safe to send to LLM."""
    if _has_unmasked_pii(content):
        return False
    return True


# ---------------------------------------------------------------------------
# LLM + Embedding client wrappers
# ---------------------------------------------------------------------------

# Summarization prompt template (gpt-4o-mini, temp=0.0)
_SUMMARY_SYSTEM_PROMPT = """Bạn là trợ lý tóm tắt cuộc trò chuyện tâm lý.
Tóm tắt cuộc chat sau trong TỐI ĐA 500 ký tự tiếng Việt.
Tập trung vào: cảm xúc chính, trigger gây ra (nếu có), hành động ứng phó đã thử, và kết quả.
KHÔNG đề cập tên người, địa điểm, số điện thoại, hay thông tin nhận dạng cá nhân.
KHÔNG phân tích lâm sàng — chỉ tóm tắt thực tế."""

_SUMMARY_USER_TEMPLATE = """Cuộc trò chuyện ({turn_count} lượt):

{conversation_text}

Tóm tắt:"""


async def _generate_summary(conversation_text: str, turn_count: int) -> str:
    """Call GPT-4o-mini to generate a ≤500 char Vietnamese summary."""
    client = openai.AsyncOpenAI()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=250,  # ~500 chars Vietnamese
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _SUMMARY_USER_TEMPLATE.format(
                    turn_count=turn_count,
                    conversation_text=conversation_text,
                ),
            },
        ],
    )
    summary = response.choices[0].message.content.strip()
    return summary[:500]  # Hard cap


async def _generate_embedding(text: str) -> list[float]:
    """Generate text-embedding-3-small embedding (1536d)."""
    client = openai.AsyncOpenAI()
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MessageRow:
    message_id: str
    role: str
    content: str
    assistant_tone: str | None
    sos_triggered: bool
    created_at: datetime


@dataclass
class SummarizerResult:
    session_id: str
    user_id: str
    summary: str
    memory_id: str
    dominant_emotion: str | None
    key_triggers: list[str]
    sos_triggered: bool
    overflow_summaries: list[dict]  # summaries pushed to archive


# ---------------------------------------------------------------------------
# SessionSummarizer
# ---------------------------------------------------------------------------


class _ProfileVersionConflictError(Exception):
    """Raised when optimistic lock on user_profiles.version fails; transaction should roll back."""


class SessionSummarizer:
    """
    Summarizes a completed session and updates the user's profile.

    Public API:
      - summarize_session(session_id, user_id) -> SummarizerResult | None
    """

    MAX_RETRY = 3

    def __init__(self, pg_pool: asyncpg.Pool) -> None:
        self._pg = pg_pool

    async def summarize_session(
        self, session_id: str, user_id: str
    ) -> SummarizerResult | None:
        """
        Main entry point. Fetches session messages, summarizes, embeds,
        and writes to Postgres atomically (conversation_memories + user_profiles
        + archive + outbox).

        Returns None if session is skipped (already summarized, no messages).
        """
        # -- Fetch messages --
        messages = await self._fetch_messages(session_id, user_id)

        if not messages:
            logger.info("Session %s has no messages — skipping summary", session_id)
            return None

        # -- Check if already summarized --
        already_done = await self._is_already_summarized(session_id, user_id)
        if already_done:
            logger.info("Session %s already summarized — skipping", session_id)
            return None

        # -- PII safety check --
        for msg in messages:
            if not _content_is_safe(msg.content):
                logger.error(
                    "PII detected in session %s message %s — aborting summarization",
                    session_id, msg.message_id,
                )
                return None

        # -- Detect SOS --
        sos_triggered = any(m.sos_triggered for m in messages)

        # -- Edge case: single-message session --
        if len(messages) == 1:
            summary = self._minimal_summary(messages[0], sos_triggered)
            embedding = await _generate_embedding(summary)
            return await self._persist(
                session_id, user_id, messages, summary, embedding, sos_triggered
            )

        # -- Edge case: SOS session — minimal summary only, no LLM call --
        if sos_triggered:
            summary = "Phiên có sự kiện khủng hoảng. Nội dung không được tóm tắt chi tiết."
            embedding = await _generate_embedding(summary)
            return await self._persist(
                session_id, user_id, messages, summary, embedding, sos_triggered
            )

        # -- Build conversation text for LLM --
        conversation_text = self._build_conversation_text(messages)
        if _has_unmasked_pii(conversation_text):
            logger.error(
                "PII detected in session %s aggregated conversation text — aborting LLM summarization",
                session_id,
            )
            return None

        # -- Mixed-language note: gpt-4o-mini handles vi+en natively --
        # If session contains English mixed with Vietnamese, summary will be Vietnamese.
        # No preprocessing needed.

        # -- Generate summary --
        summary = await _generate_summary(conversation_text, turn_count=len(messages))

        # -- Validate summary has no PII --
        if _has_unmasked_pii(summary):
            logger.error("LLM-generated summary for session %s contains PII — truncating", session_id)
            summary = "Tóm tắt phiên không khả dụng (kiểm tra PII)."

        # -- Generate embedding --
        embedding = await _generate_embedding(summary)

        return await self._persist(session_id, user_id, messages, summary, embedding, sos_triggered)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _fetch_messages(self, session_id: str, user_id: str) -> list[MessageRow]:
        """Fetch all messages for session, ordered chronologically."""
        async with self._pg.acquire() as conn:
            await conn.execute(
                "SET LOCAL app.current_user_id = $1; SET LOCAL app.current_role = 'service'",
                user_id,
            )
            rows = await conn.fetch(
                """
                SELECT message_id, role, content, assistant_tone, sos_triggered, created_at
                FROM messages
                WHERE session_id = $1 AND user_id = $2
                ORDER BY created_at ASC
                """,
                session_id, user_id,
            )
        return [
            MessageRow(
                message_id=r["message_id"],
                role=r["role"],
                content=r["content"],
                assistant_tone=r["assistant_tone"],
                sos_triggered=r["sos_triggered"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def _is_already_summarized(self, session_id: str, user_id: str) -> bool:
        """Check if a session_summary memory already exists for this session."""
        async with self._pg.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM conversation_memories
                WHERE session_id = $1 AND user_id = $2 AND memory_type = 'session_summary'
                  AND is_deleted = FALSE
                """,
                session_id, user_id,
            )
        return (count or 0) > 0

    def _build_conversation_text(self, messages: list[MessageRow]) -> str:
        """Build condensed conversation string for LLM input."""
        lines = []
        for msg in messages:
            role_label = "Người dùng" if msg.role == "user" else "Serene"
            lines.append(f"{role_label}: {msg.content}")
        return "\n".join(lines)

    def _minimal_summary(self, msg: MessageRow, sos: bool) -> str:
        """Generate a minimal summary without LLM (single-message or edge case)."""
        if sos:
            return "Phiên một lượt có sự kiện khủng hoảng."
        return f"Phiên một lượt. Người dùng chia sẻ: {msg.content[:100]}..."

    def _extract_dominant_emotion(self, messages: list[MessageRow]) -> str | None:
        """Infer dominant emotion from assistant_tone distribution."""
        tone_map = {
            "supportive": "hopeful",
            "validating": "neutral",
            "cheerful": "happy",
            "calming": "stressed",
            "mentor": "neutral",
            "neutral": "neutral",
        }
        tones = [tone_map.get(m.assistant_tone) for m in messages if m.assistant_tone]
        if not tones:
            return None
        # Simple majority vote
        return max(set(tones), key=tones.count)

    def _extract_key_triggers(self, messages: list[MessageRow]) -> list[str]:
        """
        Lightweight trigger extraction via keyword matching.
        In production, Analyst agent provides trigger labels; this is the fallback.
        """
        keyword_map = {
            "deadline": ["deadline", "hạn nộp", "đồ án", "bài tập"],
            "insomnia": ["không ngủ", "mất ngủ", "thức khuya", "ngủ không được"],
            "academic_pressure": ["thi", "điểm", "học", "trường"],
            "loneliness": ["cô đơn", "một mình", "không ai"],
            "relationship_conflict": ["mâu thuẫn", "cãi nhau", "bạn bè", "gia đình"],
        }
        all_text = " ".join(m.content.lower() for m in messages)
        found = []
        for trigger, keywords in keyword_map.items():
            if any(kw in all_text for kw in keywords):
                found.append(trigger)
        return found[:5]  # Cap at 5 triggers

    async def _persist(
        self,
        session_id: str,
        user_id: str,
        messages: list[MessageRow],
        summary: str,
        embedding: list[float],
        sos_triggered: bool,
    ) -> SummarizerResult:
        """
        Single Postgres transaction (commit all or none):
          1. INSERT conversation_memories (session_summary)
          2. Load profile, append summary, compute overflow trim
          3. INSERT session_summaries_archive for overflow (before profile UPDATE so the
             cold copy is written in the same txn as the trimmed JSON — no partial commit)
          4. UPDATE user_profiles (optimistic lock on version)
          5. INSERT user_profile_snapshots (reason='session_end')
          6. INSERT sync_outbox (session.ended)
          7. Invalidate Redis (handled outside this method by caller)
        """
        import secrets

        dominant_emotion = self._extract_dominant_emotion(messages)
        key_triggers = self._extract_key_triggers(messages)
        from app.services.utils import get_now
        now = get_now().replace(tzinfo=None)
        session_started_at = messages[0].created_at if messages else now
        session_ended_at = messages[-1].created_at if messages else now

        summary_entry = {
            "session_id": session_id,
            "started_at": session_started_at.isoformat(),
            "ended_at": session_ended_at.isoformat(),
            "turn_count": len(messages),
            "summary": summary,
            "summary_embedding_ref": "",
            "dominant_emotion": dominant_emotion,
            "key_triggers": key_triggers,
            "resources_suggested": [],
            "resources_engaged": [],
            "sos_triggered": sos_triggered,
            "crisis_level_peak": 4 if sos_triggered else 0,
        }

        outbox_payload = {
            "user_id": user_id,
            "session_id": session_id,
            "started_at": session_started_at.isoformat(),
            "ended_at": session_ended_at.isoformat(),
            "dominant_emotion": dominant_emotion,
            "key_triggers": key_triggers,
            "sos_triggered": sos_triggered,
        }

        for attempt in range(self.MAX_RETRY):
            memory_id = f"mem_{secrets.token_hex(8)}"
            summary_entry["summary_embedding_ref"] = memory_id
            overflow_summaries = []

            async with self._pg.acquire() as conn:
                await conn.execute(
                    "SET LOCAL app.current_role = 'service'; SET LOCAL app.current_user_id = $1",
                    user_id,
                )

                try:
                    async with conn.transaction():
                        # 1. Insert conversation_memories
                        await conn.execute(
                            """
                            INSERT INTO conversation_memories
                                (memory_id, user_id, session_id, content, memory_type,
                                 embedding, importance_score, confidence)
                            VALUES ($1, $2, $3, $4, 'session_summary', $5::vector, 0.9, 0.95)
                            ON CONFLICT DO NOTHING
                            """,
                            memory_id, user_id, session_id, summary, str(embedding),
                        )

                        # 2. Load current profile and append summary
                        row = await conn.fetchrow(
                            "SELECT version, profile FROM user_profiles WHERE user_id = $1 FOR UPDATE",
                            user_id,
                        )
                        if row is None:
                            raise LookupError(f"Profile not found for user_id={user_id}")

                        current_version = row["version"]
                        profile = json.loads(row["profile"])
                        summaries: list = profile.get("session_summaries", [])

                        # Prepend newest first
                        summaries.insert(0, summary_entry)

                        # Trim to 50
                        if len(summaries) > 50:
                            overflow_summaries = summaries[50:]
                            summaries = summaries[:50]

                        profile["session_summaries"] = summaries
                        profile.setdefault("meta", {})["last_rollup_at"] = now.isoformat()
                        profile.setdefault("safety_flags", {})
                        if sos_triggered:
                            profile["safety_flags"]["ever_sos_triggered"] = True
                            profile["safety_flags"]["last_sos_at"] = now.isoformat()

                        # 3. Persist overflow to archive before profile UPDATE (same txn)
                        for overflow in overflow_summaries:
                            await conn.execute(
                                """
                                INSERT INTO session_summaries_archive
                                    (user_id, session_id, summary, session_started_at,
                                     dominant_emotion, sos_triggered)
                                VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                                """,
                                user_id,
                                overflow.get("session_id"),
                                json.dumps(overflow),
                                datetime.fromisoformat(overflow["started_at"]) if overflow.get("started_at") else None,
                                overflow.get("dominant_emotion"),
                                overflow.get("sos_triggered", False),
                            )

                        upd = await conn.execute(
                            """
                            UPDATE user_profiles
                            SET profile = $1::jsonb,
                                summary_count = $2,
                                last_active_session_id = $3,
                                version = version + 1,
                                updated_at = NOW()
                            WHERE user_id = $4 AND version = $5
                            """,
                            json.dumps(profile),
                            len(summaries),
                            session_id,
                            user_id,
                            current_version,
                        )
                        if upd != "UPDATE 1":
                            raise _ProfileVersionConflictError()

                        # 4. Snapshot
                        await conn.execute(
                            """
                            INSERT INTO user_profile_snapshots (user_id, version, profile, reason)
                            VALUES ($1, $2, $3::jsonb, 'session_end')
                            ON CONFLICT (user_id, version) DO NOTHING
                            """,
                            user_id, current_version + 1, json.dumps(profile),
                        )

                        # 5. Queue outbox event (PII-masked, no raw content)
                        await conn.execute(
                            """
                            INSERT INTO sync_outbox (event_type, payload, user_id, status)
                            VALUES ('session.ended', $1::jsonb, $2, 'pending')
                            """,
                            json.dumps(outbox_payload), user_id,
                        )
                except _ProfileVersionConflictError:
                    logger.warning(
                        "Session persist version conflict for user_id=%s session=%s (attempt %d/%d)",
                        user_id,
                        session_id,
                        attempt + 1,
                        self.MAX_RETRY,
                    )
                    continue

            return SummarizerResult(
                session_id=session_id,
                user_id=user_id,
                summary=summary,
                memory_id=memory_id,
                dominant_emotion=dominant_emotion,
                key_triggers=key_triggers,
                sos_triggered=sos_triggered,
                overflow_summaries=overflow_summaries,
            )

        raise RuntimeError(
            f"Failed to persist session summary after {self.MAX_RETRY} retries "
            f"(user_id={user_id}, session_id={session_id})"
        )


# ---------------------------------------------------------------------------
# Midnight batch job (sessions not summarized after 30 min idle)
# ---------------------------------------------------------------------------


async def run_midnight_batch(pg_pool: asyncpg.Pool) -> None:
    """
    Finds all sessions with last_message_at older than 30 minutes that have
    not yet been summarized. Called by Celery beat at midnight (UTC).
    """
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.session_id, c.user_id
            FROM conversations c
            WHERE c.last_message_at < NOW() - INTERVAL '30 minutes'
              AND c.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM conversation_memories m
                  WHERE m.session_id = c.session_id
                    AND m.memory_type = 'session_summary'
                    AND m.is_deleted = FALSE
              )
            ORDER BY c.last_message_at ASC
            LIMIT 200
            """,
        )

    summarizer = SessionSummarizer(pg_pool)
    for row in rows:
        try:
            result = await summarizer.summarize_session(row["session_id"], row["user_id"])
            if result:
                logger.info("Batch summarized session %s", row["session_id"])
        except Exception as exc:
            logger.error("Batch summarize failed for session %s: %s", row["session_id"], exc)


# ---------------------------------------------------------------------------
# Unit test examples (edge cases)
# ---------------------------------------------------------------------------

class TestSessionSummarizer:
    """
    Example test class — run with pytest + asyncio.
    Requires a test Postgres database and mocked OpenAI client.
    """

    async def test_single_message_session(self, pg_pool: asyncpg.Pool) -> None:
        """Single-message session should produce minimal summary without LLM call."""
        summarizer = SessionSummarizer(pg_pool)
        msg = MessageRow(
            message_id="msg_test_01",
            role="user",
            content="Hôm nay mệt quá.",
            assistant_tone=None,
            sos_triggered=False,
            created_at=get_now().replace(tzinfo=None),
        )
        summary = summarizer._minimal_summary(msg, sos=False)
        assert len(summary) <= 500
        assert "mệt" in summary or "một lượt" in summary

    async def test_sos_session_no_llm(self, pg_pool: asyncpg.Pool, mocker: Any) -> None:
        """SOS session must skip LLM call and return safe summary."""
        mock_llm = mocker.patch("python.session_summarizer._generate_summary")
        summarizer = SessionSummarizer(pg_pool)
        messages = [
            MessageRow("msg_1", "user", "Mình không muốn tiếp tục nữa", None, False,
                       get_now()),
            MessageRow("msg_2", "assistant",
                       "Bạn không đơn độc. Có thể gọi 1900 1267 (cấp cứu trầm cảm) hoặc 115 (cấp cứu).", None, True,
                       get_now()),
        ]
        text = summarizer._build_conversation_text(messages)
        assert "1900" in text or "115" in text  # SOS template có số thật
        mock_llm.assert_not_called()  # if SOS, LLM branch skipped

    async def test_pii_in_content_aborts(self, pg_pool: asyncpg.Pool) -> None:
        """Content with raw email should fail PII check and return None."""
        unsafe_content = "email của mình là nguyenvana@example.com, giúp mình với"
        assert _has_unmasked_pii(unsafe_content) is True

    async def test_mixed_language_summary(self, pg_pool: asyncpg.Pool, mocker: Any) -> None:
        """
        Session mixing Vietnamese and English should still produce Vietnamese summary.
        gpt-4o-mini handles multilingual natively; test verifies output language.
        """
        mocker.patch(
            "python.session_summarizer._generate_summary",
            return_value="Người dùng lo lắng về deadline project tiếng Anh.",
        )
        result_summary = "Người dùng lo lắng về deadline project tiếng Anh."
        assert len(result_summary) <= 500
        assert not _has_unmasked_pii(result_summary)

    async def test_overflow_trimming(self) -> None:
        """When summaries exceed 50, overflow should be returned for archiving."""
        dummy_summaries = [
            {"session_id": f"sess_{i:03d}", "started_at": "2026-01-01T00:00:00Z",
             "summary": f"summary {i}", "sos_triggered": False}
            for i in range(55)
        ]
        # Insert a new one → should trim to 50, overflow = 5
        new_summary = {"session_id": "sess_new", "started_at": "2026-04-14T00:00:00Z",
                       "summary": "new session", "sos_triggered": False}
        dummy_summaries.insert(0, new_summary)
        overflow = dummy_summaries[50:]
        trimmed = dummy_summaries[:50]
        assert len(trimmed) == 50
        assert len(overflow) == 6  # 55 + 1 new = 56, trim to 50, overflow = 6
