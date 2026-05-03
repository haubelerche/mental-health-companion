"""Tests for heart wallet, reward grant, idempotency, and streak engine.

Uses in-memory SQLite via SQLAlchemy so no real DB is needed.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.services.db.models import (
    HeartRewardEvent,
    HeartWallet,
    MoodCheckin,
    StreakState,
    User,
)
from app.services.db.session import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # SQLite doesn't enforce FK by default
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            user_id="usr_test",
            display_name="Test",
            email="t@test.com",
            password_hash="x",
            is_active=True,
        )
        session.add(user)
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# HeartWallet / grant_hearts
# ---------------------------------------------------------------------------

def test_grant_hearts_creates_wallet_and_event(db):
    from app.hearts.service import grant_hearts

    result = grant_hearts(
        db,
        user_id="usr_test",
        amount=10,
        event_type="daily_mood_checkin_completed",
        source_tab="checkin",
        idempotency_key="mood_checkin:usr_test:2026-05-01",
    )
    db.commit()

    assert result["granted"] is True
    assert result["amount"] == 10
    assert result["new_balance"] == 10

    wallet = db.get(HeartWallet, "usr_test")
    assert wallet.balance == 10
    assert wallet.lifetime_earned == 10


def test_grant_hearts_idempotent_returns_already_claimed(db):
    from app.hearts.service import grant_hearts

    idem = "mood_checkin:usr_test:2026-05-01"
    grant_hearts(db, user_id="usr_test", amount=10, event_type="daily_mood_checkin_completed",
                 source_tab="checkin", idempotency_key=idem)
    db.commit()

    result2 = grant_hearts(db, user_id="usr_test", amount=10, event_type="daily_mood_checkin_completed",
                           source_tab="checkin", idempotency_key=idem)
    assert result2["granted"] is False
    assert result2["reason"] == "already_claimed"
    assert result2["amount"] == 0

    wallet = db.get(HeartWallet, "usr_test")
    assert wallet.balance == 10  # not doubled


def test_get_balance_returns_zero_for_no_wallet(db):
    from app.hearts.service import get_balance
    assert get_balance(db, "usr_test") == 0


def test_grant_hearts_accumulates_across_events(db):
    from app.hearts.service import grant_hearts

    grant_hearts(db, user_id="usr_test", amount=10, event_type="event_a", source_tab="t",
                 idempotency_key="key_a")
    grant_hearts(db, user_id="usr_test", amount=5, event_type="event_b", source_tab="t",
                 idempotency_key="key_b")
    db.commit()

    from app.hearts.service import get_balance
    assert get_balance(db, "usr_test") == 15


# ---------------------------------------------------------------------------
# Streak engine
# ---------------------------------------------------------------------------

def test_streak_increments_on_consecutive_days(db):
    from app.hearts.streaks import update_mood_streak

    d0 = date(2026, 5, 1)
    r1 = update_mood_streak(db, user_id="usr_test", checkin_date=d0)
    assert r1["current"] == 1
    assert r1["bonus_granted"] is False

    r2 = update_mood_streak(db, user_id="usr_test", checkin_date=d0 + timedelta(days=1))
    assert r2["current"] == 2


def test_streak_resets_on_gap(db):
    from app.hearts.streaks import update_mood_streak

    d0 = date(2026, 5, 1)
    update_mood_streak(db, user_id="usr_test", checkin_date=d0)
    update_mood_streak(db, user_id="usr_test", checkin_date=d0 + timedelta(days=1))
    db.commit()

    r = update_mood_streak(db, user_id="usr_test", checkin_date=d0 + timedelta(days=3))
    assert r["current"] == 1  # gap → reset


def test_7day_streak_grants_bonus(db):
    from app.hearts.streaks import update_mood_streak

    d0 = date(2026, 5, 1)
    for i in range(7):
        r = update_mood_streak(db, user_id="usr_test", checkin_date=d0 + timedelta(days=i))
    db.commit()

    assert r["current"] == 7
    assert r["bonus_granted"] is True
    assert r["bonus_amount"] == 20

    from app.hearts.service import get_balance
    assert get_balance(db, "usr_test") == 20


def test_same_day_checkin_no_double_streak(db):
    from app.hearts.streaks import update_mood_streak

    d = date(2026, 5, 1)
    update_mood_streak(db, user_id="usr_test", checkin_date=d)
    r2 = update_mood_streak(db, user_id="usr_test", checkin_date=d)
    assert r2["current"] == 1  # not incremented twice
