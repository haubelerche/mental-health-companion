"""Canonical session-close lifecycle for summaries and memory cards."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.memory.extractor import ExtractionResult, extract_memory_candidates
from app.memory.llm_extractor import extract_memory_candidates_llm
from app.memory.service import create_cards_from_candidates, ensure_memory_card_tables
from app.services.analyst_writer import record_analyst_signal, upsert_insight_hypothesis
from app.services.db.models import Conversation, MemoryCard, Message, SessionSummaryArchive, UserProfile
from app.services.mem0_service import MemoryManager
from app.services.memory_enrichment import apply_to_profile, extract_structured
from app.services.pii_mask import mask_pii
from app.services.redis_client import cache_delete, profile_cache_key
from app.services.utils import get_now

logger = logging.getLogger(__name__)

SessionCloseReason = Literal[
    "new_session",
    "persona_change",
    "explicit_end",
    "idle_timeout",
    "logout",
    "app_backgrounded_best_effort",
    "rotation_timeout",
]


@dataclass(slots=True)
class SessionCloseResult:
    session_id: str
    summarized: bool
    summary: str
    archive_created: bool
    memory_cards_created: int
    memory_cards_total: int
    reason: SessionCloseReason


def _summary_from_profile(profile: dict[str, Any] | None, session_id: str) -> str:
    summaries = list((profile or {}).get("session_summaries") or [])
    for item in reversed(summaries):
        if not isinstance(item, dict):
            continue
        if str(item.get("session_id") or "") != session_id:
            continue
        summary = str(item.get("summary") or item.get("text") or "").strip()
        if summary:
            return summary[:700]
    return ""


def _summarize_session_key_points(transcript: str) -> str:
    cleaned = str(transcript or "").strip()
    if not cleaned:
        return "Phiên trò chuyện đã kết thúc."

    settings = get_settings()
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.llm_timeout_seconds, 8.0))
            resp = client.chat.completions.create(
                model=settings.openai_model_analyst,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tóm tắt ngắn gọn phiên trò chuyện bằng tiếng Việt, tối đa 3 câu. "
                            "Không dùng nhãn phân tích. Không nêu thông tin định danh cá nhân."
                        ),
                    },
                    {"role": "user", "content": cleaned[:3000]},
                ],
            )
            summary = str(resp.choices[0].message.content or "").strip()
            if summary:
                return summary[:700]
        except Exception as exc:
            logger.warning("session summary llm failed: %s", exc)

    compact = " ".join(cleaned.split())
    snippet = (compact[:300] + "...") if len(compact) > 303 else compact
    return f"Phiên trò chuyện đã kết thúc. Nội dung tóm tắt: {snippet}"[:700]


def _deterministic_session_summary(transcript: str) -> str:
    compact = " ".join(str(transcript or "").split()).strip()
    if not compact:
        return "Phiên trò chuyện đã kết thúc."
    snippet = (compact[:300] + "...") if len(compact) > 303 else compact
    return f"Phiên trò chuyện đã kết thúc. Nội dung tóm tắt: {snippet}"[:700]


def _summary_from_conversation(session: Conversation) -> str:
    data = dict(session.anonymous_summary or {})
    for key in ("summary_text", "summary", "text"):
        value = str(data.get(key) or "").strip()
        if value:
            return value[:700]
    return ""


def _archive_payload(summary_text: str, *, reason: str, turn_count: int, created_cards: int) -> dict[str, Any]:
    return {
        "summary_text": summary_text,
        "reason": reason,
        "turn_count": turn_count,
        "memory_cards_created": created_cards,
        "schema_version": "session_summary_v1",
    }


def _extract_candidates(transcript: str, *, session_id: str, summary_text: str) -> ExtractionResult:
    # LLM extraction is tried first; deterministic covers keywords the LLM misses.
    llm_result = extract_memory_candidates_llm(transcript, session_id=session_id)
    det_result = extract_memory_candidates(transcript, session_id=session_id)

    seen: set[tuple[str, str, str]] = set()
    merged: list = []
    for card in list(llm_result.candidate_cards) + list(det_result.candidate_cards):
        key = (card.memory_type, card.subject.lower().strip(), card.predicate.lower().strip())
        if key not in seen:
            seen.add(key)
            merged.append(card)
    return ExtractionResult(candidate_cards=merged)


def _enqueue_mem0_add(user_id: str, messages: list[dict[str, str]]) -> None:
    try:
        MemoryManager.instance().add_session(user_id=user_id, messages=messages)
    except Exception as exc:  # pragma: no cover
        logger.warning("derived mem0 add failed for %s: %s", user_id, exc)


class SessionLifecycleService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def close_session(
        self,
        *,
        user_id: str,
        session_id: str,
        reason: SessionCloseReason = "explicit_end",
    ) -> SessionCloseResult:
        ensure_memory_card_tables(self.db)
        session = self.db.scalar(
            select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if session is None:
            raise ValueError("session not found")

        rows = list(
            self.db.scalars(
                select(Message)
                .where(Message.session_id == session.session_id, Message.user_id == user_id)
                .order_by(Message.created_at.asc())
            ).all()
        )
        turn_count = len(rows)
        user_turn_count = sum(1 for row in rows if row.role == "user")
        assistant_turn_count = sum(1 for row in rows if row.role == "assistant")
        transcript = mask_pii("\n".join(f"{m.role}: {m.content}" for m in rows[-40:]))[:3500]

        prof = self.db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        existing_profile = dict(prof.profile or {}) if prof else {}
        summary_text = _summary_from_profile(existing_profile, session.session_id) or _summarize_session_key_points(transcript)
        if not summary_text.strip():
            summary_text = "Phiên trò chuyện đã kết thúc."

        existing_cards = list(
            self.db.scalars(
                select(MemoryCard).where(
                    MemoryCard.user_id == user_id,
                    MemoryCard.source_session_id == session.session_id,
                    MemoryCard.status != "deleted_by_user",
                )
            ).all()
        )
        archive = self.db.scalar(
            select(SessionSummaryArchive).where(
                SessionSummaryArchive.user_id == user_id,
                SessionSummaryArchive.session_id == session.session_id,
            )
        )

        now = get_now().replace(tzinfo=None)
        archive_created = False
        created_cards_count = 0

        if session.summarized_at is None:
            session.summarized_at = now

        if turn_count <= 0 or user_turn_count <= 0:
            session.anonymous_summary = {
                "summary_text": "Phiên chưa có đủ nội dung để tóm tắt.",
                "reason": reason,
                "turn_count": turn_count,
                "schema_version": "session_summary_v1",
            }
            self.db.flush()
            self.db.commit()
            return SessionCloseResult(
                session_id=session.session_id,
                summarized=False,
                summary=session.anonymous_summary["summary_text"],
                archive_created=False,
                memory_cards_created=0,
                memory_cards_total=len(existing_cards),
                reason=reason,
            )

        settings = get_settings()
        extract = extract_structured(transcript, settings, sos_triggered=any(bool(m.sos_triggered) for m in rows))
        if prof is None:
            prof = UserProfile(user_id=user_id, profile={})
            self.db.add(prof)
            self.db.flush()
        profile_data = apply_to_profile(
            dict(prof.profile or {}),
            extract=extract,
            session_meta={
                "session_id": session.session_id,
                "started_at": session.started_at.isoformat() if session.started_at else now.isoformat(),
                "ended_at": now.isoformat(),
                "turn_count": turn_count,
                "crisis_level_peak": 5 if any(bool(m.sos_triggered) for m in rows) else 0,
            },
            summary_text=summary_text,
        )
        meta = dict(profile_data.get("meta") or {})
        meta["weekly_note_generated_at"] = None
        meta["weekly_note_content"] = None
        profile_data["meta"] = meta
        prof.profile = profile_data
        prof.updated_at = now

        if archive is None:
            archive = SessionSummaryArchive(
                user_id=user_id,
                session_id=session.session_id,
                summary=_archive_payload(summary_text, reason=reason, turn_count=turn_count, created_cards=0),
                session_started_at=session.started_at,
                dominant_emotion=None,
                sos_triggered=any(bool(m.sos_triggered) for m in rows),
            )
            self.db.add(archive)
            archive_created = True

        if not existing_cards and assistant_turn_count > 0:
            cards = create_cards_from_candidates(
                self.db,
                user_id,
                _extract_candidates(transcript, session_id=session.session_id, summary_text=summary_text),
            )
            created_cards_count = sum(1 for card in cards if card not in existing_cards)
            existing_cards = list(
                self.db.scalars(
                    select(MemoryCard).where(
                        MemoryCard.user_id == user_id,
                        MemoryCard.source_session_id == session.session_id,
                        MemoryCard.status != "deleted_by_user",
                    )
                ).all()
            )

        session.anonymous_summary = _archive_payload(
            summary_text,
            reason=reason,
            turn_count=turn_count,
            created_cards=len(existing_cards),
        )
        if archive is not None:
            archive.summary = dict(session.anonymous_summary)

        try:
            sig_id = record_analyst_signal(self.db, user_id=user_id, session_id=session.session_id, extract=extract)
            upsert_insight_hypothesis(self.db, user_id=user_id, extract=extract, signal_id=sig_id, session_id=session.session_id)
        except Exception as exc:
            logger.warning("analyst pipeline at session close failed for %s: %s", user_id, exc)

        cache_delete(profile_cache_key(user_id))
        self.db.flush()
        self.db.commit()

        if get_settings().memory_mem0_write_enabled:
            mem0_messages = [{"role": str(m.role), "content": mask_pii(str(m.content))} for m in rows[-40:]]
            threading.Thread(target=_enqueue_mem0_add, args=(user_id, mem0_messages), daemon=True).start()

        return SessionCloseResult(
            session_id=session.session_id,
            summarized=True,
            summary=summary_text,
            archive_created=archive_created,
            memory_cards_created=created_cards_count,
            memory_cards_total=len(existing_cards),
            reason=reason,
        )


def backfill_missing_canonical_memory_for_user(
    db: Session,
    *,
    user_id: str,
    limit: int = 10,
) -> dict[str, int]:
    """Repair old summarized sessions that predate canonical memory_cards.

    This is deterministic and does not call an LLM. It is intended for local/dev
    read-repair and for recovering sessions previously summarized into mem0 only.
    """
    ensure_memory_card_tables(db)
    sessions = list(
        db.scalars(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
                Conversation.message_count > 0,
            )
            .order_by(Conversation.last_message_at.desc())
            .limit(max(1, min(int(limit), 50)))
        ).all()
    )
    repaired_sessions = 0
    archives_created = 0
    cards_created = 0
    now = get_now().replace(tzinfo=None)
    prof = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    profile_data = dict(prof.profile or {}) if prof else {}

    for session in sessions:
        existing_card_count = db.scalar(
            select(MemoryCard.card_id)
            .where(
                MemoryCard.user_id == user_id,
                MemoryCard.source_session_id == session.session_id,
                MemoryCard.status != "deleted_by_user",
            )
            .limit(1)
        )
        existing_archive = db.scalar(
            select(SessionSummaryArchive.archive_id).where(
                SessionSummaryArchive.user_id == user_id,
                SessionSummaryArchive.session_id == session.session_id,
            )
        )
        if existing_card_count and existing_archive:
            continue

        rows = list(
            db.scalars(
                select(Message)
                .where(Message.session_id == session.session_id, Message.user_id == user_id)
                .order_by(Message.created_at.asc())
            ).all()
        )
        if not rows or not any(row.role == "user" for row in rows) or not any(row.role == "assistant" for row in rows):
            continue

        transcript = mask_pii("\n".join(f"{m.role}: {m.content}" for m in rows[-40:]))[:3500]
        summary_text = (
            _summary_from_conversation(session)
            or _summary_from_profile(profile_data, session.session_id)
            or _deterministic_session_summary(transcript)
        )
        if not summary_text.strip():
            continue

        if existing_archive is None:
            db.add(
                SessionSummaryArchive(
                    user_id=user_id,
                    session_id=session.session_id,
                    summary=_archive_payload(
                        summary_text,
                        reason="canonical_backfill",
                        turn_count=len(rows),
                        created_cards=0,
                    ),
                    session_started_at=session.started_at,
                    dominant_emotion=None,
                    sos_triggered=any(bool(m.sos_triggered) for m in rows),
                )
            )
            archives_created += 1

        if not existing_card_count:
            cards = create_cards_from_candidates(
                db,
                user_id,
                _extract_candidates(transcript, session_id=session.session_id, summary_text=summary_text),
            )
            cards_created += len(cards)

        if session.summarized_at is None:
            session.summarized_at = now
        repaired_sessions += 1

    if repaired_sessions:
        db.commit()
        cache_delete(profile_cache_key(user_id))
    return {
        "sessions_checked": len(sessions),
        "sessions_repaired": repaired_sessions,
        "archives_created": archives_created,
        "cards_created": cards_created,
    }
