# OAuth API (Google & Facebook)

This document describes the OAuth endpoints exposed by the backend and how the frontend should interact with them.

## Overview
- Providers supported: Google, Facebook
- Flow: Frontend initiates OAuth by redirecting user to backend `/auth/oauth/{provider}/start`, backend generates `state` (stored server-side or signed) and redirects to provider. Provider returns to backend callback `/auth/oauth/{provider}/callback` which resolves identity, links/creates user, issues auth cookies, and redirects back to frontend.

## Endpoints

- `GET /auth/oauth/google/start?return_to=<frontend_url>`
  - Query params:
    - `return_to` (optional): frontend URL to redirect after successful auth (defaults to configured `FRONTEND_AUTH_REDIRECT_URL`).
  - Response: Redirects user to Google's OAuth consent screen.

- `GET /auth/oauth/google/callback?code=...&state=...`
  - Backend validates `state`, exchanges `code` for token, fetches userinfo.
  - Behavior:
    - If provider email is verified and matches existing user: links account and logs in that user.
    - If provider email is verified and no existing user: auto-creates a user, marks email verified, links identity, logs in.
    - If provider does not provide a verified email: does NOT auto-create — redirects to frontend with `?oauth_missing_email=1&provider=google` so the frontend can ask user to link or provide an email.
  - On success: backend issues auth cookies (`access_token`, `refresh_token`, `csrf_token`) and redirects to `return_to`.

- `GET /auth/oauth/facebook/start?return_to=<frontend_url>`
  - Same semantics as Google start.

- `GET /auth/oauth/facebook/callback?code=...&state=...`
  - Facebook may not return an email. If email present, behavior mirrors Google.
  - If email is missing or untrusted: backend redirects to `return_to?oauth_missing_email=1&provider=facebook`.

## Frontend integration notes

- Start flow: call backend `/auth/oauth/{provider}/start?return_to=<url>` in a top-level navigation (not XHR) so browser follows provider redirects.
- After provider consent and backend processing, the backend redirects the browser back to `return_to` and sets auth cookies. The frontend should detect successful login by checking `GET /auth/me` or by reading the URL parameters.
- Missing email: if redirected with `oauth_missing_email=1`, prompt user to either enter an email to link or to sign-in with an existing account to link the OAuth provider.
- CSRF / cookies: backend sets `HttpOnly` cookies for `access_token` and `refresh_token` and a non-HttpOnly `csrf_token` cookie. Use existing auth flow (`/auth/me`, `/auth/refresh`) after redirect.

## Example

1. Frontend opens: `GET https://api.example.com/auth/oauth/google/start?return_to=https://app.example.com/auth/callback`
2. User completes Google consent, Google redirects to backend callback.
3. Backend issues cookies and redirects to `https://app.example.com/auth/callback`.
4. Frontend calls `GET /v1/auth/me` to verify login and fetch user info.

## Security considerations

- `state` is short-lived and stored server-side (Redis) or signed; it prevents CSRF and replay attacks.
- Only auto-link when provider email is verified.
- For Facebook (or other providers that omit email), require explicit linking or manual email verification before granting account.
