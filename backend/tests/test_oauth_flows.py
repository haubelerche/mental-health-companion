import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.services.db.session import Base, get_engine, get_session_factory
from app.services.db.models import User


@pytest.fixture(scope="module", autouse=True)
def ensure_oauth_schema():
    Base.metadata.create_all(bind=get_engine())
    yield


@pytest.mark.asyncio
async def test_google_callback_creates_user_and_redirects(monkeypatch):
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
    Session = get_session_factory()
    session = Session()
    try:
        row = session.scalar(select(User).where(User.email == email))
        assert row is not None
        assert row.is_active
    finally:
        session.close()


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
async def test_facebook_callback_creates_user_when_email_present(monkeypatch):
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

    Session = get_session_factory()
    session = Session()
    try:
        row = session.scalar(select(User).where(User.email == email))
        assert row is not None
        assert row.is_active
    finally:
        session.close()
