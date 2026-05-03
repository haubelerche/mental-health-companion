from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.services.db.models import User, UserProfile
from app.services.db.session import Base, get_db
from app.main import app


@pytest.fixture
def onboarding_test_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    user_id = f"usr_{uuid4().hex[:10]}"
    db = SessionLocal()
    db.add(
        User(
            user_id=user_id,
            display_name="Onboarding User",
            email=f"onboard_{uuid4().hex[:10]}@example.com",
            password_hash="hashed",
            disclaimer_accepted=True,
            is_active=True,
            policy_acknowledged_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.close()

    def override_db():
        db_session = SessionLocal()
        try:
            yield db_session
        finally:
            db_session.close()

    def override_user():
        db_session = SessionLocal()
        try:
            user = db_session.scalar(select(User).where(User.user_id == user_id))
            assert user is not None
            return user
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    try:
        yield SessionLocal, user_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_onboarding_complete_persists_profile(onboarding_test_db):
    SessionLocal, user_id = onboarding_test_db

    with TestClient(app) as client:
        response = client.post(
            "/v1/onboarding/complete",
            json={
                "disclaimer_accepted": True,
                "nickname": "An",
                "age_group": "18_24",
                "emotional_state": "difficult_recently",
                "primary_concern": "career_study",
                "support_level": "good",
                "stress_level": 3,
                "wake_time": "07:30",
                "bed_time": "22:30",
                "practice_ids": ["breathing", "journaling", "better_sleep"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["completed"] is True

    db = SessionLocal()
    try:
        row = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        assert row is not None
        onboarding = dict((row.profile or {}).get("onboarding") or {})
        assert onboarding["nickname"] == "An"
        assert onboarding["stress_level"] == 3
        assert onboarding["skipped"] is False
        assert onboarding["completed_at"]
        assert (row.profile or {}).get("goals") == ["breathing", "journaling", "better_sleep"]
    finally:
        db.close()


def test_onboarding_state_after_skip(onboarding_test_db):
    with TestClient(app) as client:
        skip_response = client.post("/v1/onboarding/skip")
        assert skip_response.status_code == 200

        state_response = client.get("/v1/onboarding/state")

    assert state_response.status_code == 200
    body = state_response.json()
    assert body["success"] is True
    assert body["data"]["completed"] is True
    assert body["data"]["skipped"] is True
    assert body["data"]["profile"]["skipped"] is True
