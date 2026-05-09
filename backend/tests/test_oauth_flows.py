import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.services.db.session import Base, get_engine, get_session_factory
from app.services.db.models import User


from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

@pytest.fixture(scope="module")
def test_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    
    from app.api.v1.routers.auth import get_db
    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_db
    try:
        yield SessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.asyncio
async def test_google_callback_creates_user_and_redirects(monkeypatch, test_db):
    unique = uuid.uuid4().hex[:8]
    email = f"oauth_test_{unique}@example.com"

    async def fake_exchange(code: str):
        return {"access_token": "tok"}

    async def fake_userinfo(access_token: str):
        return {"id": "g-" + unique, "email": email, "verified_email": True, "name": "OAuth Test", "picture": None}

    def fake_pop(state: str):
        return {"return_to": "http://127.0.0.1:5173/auth/callback"}

    monkeypatch.setattr("app.services.oauth_client.exchange_google_code", fake_exchange)
    monkeypatch.setattr("app.services.oauth_client.get_google_userinfo", fake_userinfo)
    monkeypatch.setattr("app.services.oauth_state.pop_oauth_state", fake_pop)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/v1/auth/oauth/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "http://127.0.0.1:5173/auth/callback"

    # verify user created in DB
    db = test_db()
    try:
        row = db.scalar(select(User).where(User.email == email))
        assert row is not None
        assert row.is_active
    finally:
        db.close()


@pytest.mark.asyncio
async def test_google_callback_missing_email_redirects_to_frontend_prompt(monkeypatch):
    unique = uuid.uuid4().hex[:8]

    async def fake_exchange(code: str):
        return {"access_token": "tok"}

    async def fake_userinfo(access_token: str):
        return {"id": "g-" + unique, "name": "No Email", "picture": None}

    def fake_pop(state: str):
        return {"return_to": "http://127.0.0.1:5173/auth/callback"}

    monkeypatch.setattr("app.services.oauth_client.exchange_google_code", fake_exchange)
    monkeypatch.setattr("app.services.oauth_client.get_google_userinfo", fake_userinfo)
    monkeypatch.setattr("app.services.oauth_state.pop_oauth_state", fake_pop)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/v1/auth/oauth/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "oauth_missing_email=1" in resp.headers.get("location")


@pytest.mark.asyncio
async def test_facebook_callback_creates_user_when_email_present(monkeypatch, test_db):
    unique = uuid.uuid4().hex[:8]
    email = f"fb_test_{unique}@example.com"

    async def fake_exchange(code: str):
        return {"access_token": "tok"}

    async def fake_userinfo(access_token: str):
        return {"id": "fb-" + unique, "email": email, "name": "FB Test", "picture": None}

    def fake_pop(state: str):
        return {"return_to": "http://127.0.0.1:5173/auth/callback"}

    monkeypatch.setattr("app.services.oauth_client.exchange_facebook_code", fake_exchange)
    monkeypatch.setattr("app.services.oauth_client.get_facebook_userinfo", fake_userinfo)
    monkeypatch.setattr("app.services.oauth_state.pop_oauth_state", fake_pop)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/v1/auth/oauth/facebook/callback?code=abc&state=xyz", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "http://127.0.0.1:5173/auth/callback"

    db = test_db()
    try:
        row = db.scalar(select(User).where(User.email == email))
        assert row is not None
        assert row.is_active
    finally:
        db.close()
