from fastapi import Response

from app.core.config import get_settings


def set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    settings = get_settings()
    samesite_val = "none" if settings.cookie_secure else "strict"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_ttl_seconds,
        domain=settings.cookie_domain,
        path="/",
    )
    if refresh_token is not None:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=samesite_val,
            max_age=settings.refresh_token_ttl_days * 24 * 3600,
            domain=settings.cookie_domain,
            path="/v1/auth/refresh",
        )


def set_csrf_cookie(response: Response, csrf_token: str) -> None:
    settings = get_settings()
    samesite_val = "none" if settings.cookie_secure else "strict"
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_ttl_seconds,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    samesite_val = "none" if settings.cookie_secure else "strict"
    for key, path in (("access_token", "/"), ("refresh_token", "/v1/auth/refresh"), ("csrf_token", "/")):
        response.set_cookie(
            key=key,
            value="",
            max_age=0,
            httponly=(key != "csrf_token"),
            secure=settings.cookie_secure,
            samesite=samesite_val,
            domain=settings.cookie_domain,
            path=path,
        )
