from __future__ import annotations

from typing import Any

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.core.config import get_settings


async def exchange_google_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    token_url = "https://oauth2.googleapis.com/token"
    async with AsyncOAuth2Client(settings.google_client_id, settings.google_client_secret) as client:
        token = await client.fetch_token(token_url, code=code, redirect_uri=settings.google_redirect_uri)
    return token


async def get_google_userinfo(access_token: str) -> dict[str, Any]:
    async with AsyncOAuth2Client(token={"access_token": access_token, "token_type": "Bearer"}) as client:
        resp = await client.get("https://www.googleapis.com/oauth2/v2/userinfo")
        resp.raise_for_status()
        return resp.json()


async def exchange_facebook_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    token_url = "https://graph.facebook.com/v17.0/oauth/access_token"
    async with AsyncOAuth2Client(settings.facebook_client_id, settings.facebook_client_secret) as client:
        token = await client.fetch_token(
            token_url,
            code=code,
            redirect_uri=settings.facebook_redirect_uri,
        )
    return token


async def get_facebook_userinfo(access_token: str) -> dict[str, Any]:
    async with AsyncOAuth2Client(token={"access_token": access_token, "token_type": "Bearer"}) as client:
        # Request email, name, id, picture
        resp = await client.get("https://graph.facebook.com/me", params={"fields": "id,name,email,picture"})
        resp.raise_for_status()
        data = resp.json()
        # Normalize picture field
        pic = data.get("picture")
        if isinstance(pic, dict):
            data["picture"] = pic.get("data", {}).get("url")
        return data
