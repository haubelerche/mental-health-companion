import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from app.main import app
from app.services.db.session import get_db

@pytest.fixture(scope="function")
def mock_db():
    db = MagicMock(spec=Session)
    # Mock behavior to simulate a new user flow
    db.scalar.return_value = None
    db.get.return_value = None
    db.add.return_value = None
    db.commit.return_value = None
    db.flush.return_value = None
    
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_google_callback_flow_without_db_write(monkeypatch, mock_db):
    """
    Verifies the OAuth flow (code exchange, userinfo retrieval, redirect)
    WITHOUT actually creating a user in any database.
    """
    unique = uuid.uuid4().hex[:8]
    email = f"oauth_test_{unique}@example.com"

    async def fake_exchange(code: str):
        return {"access_token": "tok"}

    async def fake_userinfo(access_token: str):
        return {
            "id": "g-" + unique, 
            "email": email, 
            "verified_email": True, 
            "name": f"Pytest User {unique}", 
            "picture": None
        }

    def fake_pop(state: str):
        return {"return_to": "http://127.0.0.1:5173/auth/callback"}

    monkeypatch.setattr("app.services.oauth_client.exchange_google_code", fake_exchange)
    monkeypatch.setattr("app.services.oauth_client.get_google_userinfo", fake_userinfo)
    monkeypatch.setattr("app.services.oauth_state.pop_oauth_state", fake_pop)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/v1/auth/oauth/google/callback?code=abc&state=xyz", follow_redirects=False)
    
    # Verify redirect happens as expected
    assert resp.status_code in (302, 307)
    assert resp.headers.get("location") == "http://127.0.0.1:5173/auth/callback"

    # Verify that the DB was told to add a user (but we don't actually save it)
    assert mock_db.add.called
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_google_callback_missing_email_redirects_to_frontend_prompt(monkeypatch, mock_db):
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
async def test_facebook_callback_flow_without_db_write(monkeypatch, mock_db):
    unique = uuid.uuid4().hex[:8]
    email = f"fb_test_{unique}@example.com"

    async def fake_exchange(code: str):
        return {"access_token": "tok"}

    async def fake_userinfo(access_token: str):
        return {"id": "fb-" + unique, "email": email, "name": f"Pytest User FB {unique}", "picture": None}

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
    
    # Verify that the DB was told to add a user (but we don't actually save it)
    assert mock_db.add.called
    assert mock_db.commit.called
