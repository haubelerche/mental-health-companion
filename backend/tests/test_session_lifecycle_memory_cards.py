from types import SimpleNamespace

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.memory.service import apply_user_action
from app.services.db.models import (
    Conversation,
    MemoryCard,
    MemoryCardAuditEvent,
    Message,
    SessionSummaryArchive,
    User,
    UserProfile,
)
from app.services.session_lifecycle import SessionLifecycleService
from app.services.session_lifecycle import backfill_missing_canonical_memory_for_user


def _db(monkeypatch):
    from app.services import session_lifecycle

    monkeypatch.setattr(
        session_lifecycle,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="",
            openai_model_analyst="gpt-test",
            llm_timeout_seconds=1,
            memory_mem0_write_enabled=False,
            memory_card_auto_active=False,
        ),
    )
    monkeypatch.setattr(session_lifecycle, "record_analyst_signal", lambda *_args, **_kwargs: "sig_test")
    monkeypatch.setattr(session_lifecycle, "upsert_insight_hypothesis", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(session_lifecycle, "cache_delete", lambda *_args, **_kwargs: None)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    for table in (
        User.__table__,
        Conversation.__table__,
        Message.__table__,
        UserProfile.__table__,
        MemoryCard.__table__,
        MemoryCardAuditEvent.__table__,
    ):
        table.create(engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS session_summaries_archive (
                archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR NOT NULL,
                session_id VARCHAR,
                summary JSON NOT NULL,
                session_started_at DATETIME,
                dominant_emotion VARCHAR,
                sos_triggered BOOLEAN NOT NULL DEFAULT 0,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        ))
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    session.add(User(user_id="usr_1", display_name="Minh", email="m@example.com", password_hash="x"))
    session.add(Conversation(session_id="sess_1", user_id="usr_1", message_count=2))
    session.add(Message(message_id="m1", session_id="sess_1", user_id="usr_1", role="user", content="Tôi đang stress vì deadline."))
    session.add(Message(message_id="m2", session_id="sess_1", user_id="usr_1", role="assistant", content="Mình nghe cậu."))
    session.commit()
    return session


def test_close_session_writes_archive_and_pending_memory_card(monkeypatch):
    db = _db(monkeypatch)

    result = SessionLifecycleService(db).close_session(user_id="usr_1", session_id="sess_1", reason="new_session")

    assert result.summarized is True
    assert result.archive_created is True
    assert result.memory_cards_total >= 1
    archive = db.scalar(select(SessionSummaryArchive).where(SessionSummaryArchive.session_id == "sess_1"))
    assert archive is not None
    card = db.scalar(select(MemoryCard).where(MemoryCard.source_session_id == "sess_1"))
    assert card is not None
    assert card.status == "pending_user_review"
    assert card.user_id == "usr_1"
    assert "Tóm tắt phiên" not in card.title
    assert "Tín hiệu cảm xúc" not in card.content
    assert card.content.startswith(("Bạn", "Gần đây", "Serene"))


def test_close_session_is_idempotent(monkeypatch):
    db = _db(monkeypatch)

    first = SessionLifecycleService(db).close_session(user_id="usr_1", session_id="sess_1", reason="explicit_end")
    second = SessionLifecycleService(db).close_session(user_id="usr_1", session_id="sess_1", reason="explicit_end")

    assert first.memory_cards_total == second.memory_cards_total
    assert db.query(MemoryCard).filter(MemoryCard.source_session_id == "sess_1").count() == first.memory_cards_total
    assert db.query(SessionSummaryArchive).filter(SessionSummaryArchive.session_id == "sess_1").count() == 1


def test_memory_card_keep_edit_delete_writes_audit(monkeypatch):
    db = _db(monkeypatch)
    SessionLifecycleService(db).close_session(user_id="usr_1", session_id="sess_1", reason="explicit_end")
    card = db.scalar(select(MemoryCard).where(MemoryCard.source_session_id == "sess_1"))

    apply_user_action(db, "usr_1", card.card_id, "keep")
    apply_user_action(db, "usr_1", card.card_id, "edit", new_content="Deadline công việc là nguồn áp lực đáng chú ý.")
    apply_user_action(db, "usr_1", card.card_id, "delete")
    db.commit()

    assert card.status == "deleted_by_user"
    assert db.query(MemoryCardAuditEvent).filter(MemoryCardAuditEvent.memory_card_id == card.card_id).count() == 3


def test_backfill_repairs_old_summarized_session_without_cards(monkeypatch):
    db = _db(monkeypatch)
    conv = db.scalar(select(Conversation).where(Conversation.session_id == "sess_1"))
    conv.summarized_at = conv.last_message_at
    conv.anonymous_summary = {"summary_text": "Người dùng đang stress vì deadline công việc."}
    db.commit()

    result = backfill_missing_canonical_memory_for_user(db, user_id="usr_1", limit=5)

    assert result["sessions_repaired"] == 1
    assert result["archives_created"] == 1
    assert result["cards_created"] >= 1
    assert db.query(SessionSummaryArchive).filter(SessionSummaryArchive.session_id == "sess_1").count() == 1
    assert db.query(MemoryCard).filter(MemoryCard.source_session_id == "sess_1").count() >= 1
    card = db.scalar(select(MemoryCard).where(MemoryCard.source_session_id == "sess_1"))
    assert card is not None
    assert "Tóm tắt phiên" not in card.title
    assert "Tín hiệu cảm xúc" not in card.content
