from __future__ import annotations

from urllib.parse import quote

from app.core.config import get_settings
from app.services.mailer import send_html_email


def _join_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def build_verify_link(token: str) -> str:
    settings = get_settings()
    encoded = quote(token, safe="")
    return _join_url(settings.backend_public_base_url, f"{settings.api_prefix}/auth/verify-email?token={encoded}")


def build_reset_link(token: str) -> str:
    settings = get_settings()
    encoded = quote(token, safe="")
    return f"{settings.frontend_reset_password_url}?token={encoded}"


def send_verification_email(to_email: str, display_name: str, token: str) -> None:
    settings = get_settings()
    verify_link = build_verify_link(token)
    subject = "Xac nhan email dang ky Serene"
    text = (
        f"Chao {display_name},\n\n"
        "Cam on ban da dang ky Serene. Vui long xac nhan email bang lien ket duoi day:\n"
        f"{verify_link}\n\n"
        f"Lien ket co hieu luc trong {settings.auth_email_verify_ttl_minutes} phut."
    )
    html = (
        f"<p>Chao {display_name},</p>"
        "<p>Cam on ban da dang ky Serene. Vui long xac nhan email bang lien ket duoi day:</p>"
        f"<p><a href=\"{verify_link}\">Xac nhan tai khoan</a></p>"
        f"<p>Lien ket co hieu luc trong {settings.auth_email_verify_ttl_minutes} phut.</p>"
    )
    send_html_email(to_email=to_email, subject=subject, html_body=html, text_body=text)


def send_password_reset_email(to_email: str, display_name: str, token: str) -> None:
    settings = get_settings()
    reset_link = build_reset_link(token)
    subject = "Dat lai mat khau Serene"
    text = (
        f"Chao {display_name},\n\n"
        "Ban vua yeu cau dat lai mat khau. Vui long mo lien ket duoi day:\n"
        f"{reset_link}\n\n"
        f"Lien ket co hieu luc trong {settings.auth_password_reset_ttl_minutes} phut."
    )
    html = (
        f"<p>Chao {display_name},</p>"
        "<p>Ban vua yeu cau dat lai mat khau. Vui long mo lien ket duoi day:</p>"
        f"<p><a href=\"{reset_link}\">Dat lai mat khau</a></p>"
        f"<p>Lien ket co hieu luc trong {settings.auth_password_reset_ttl_minutes} phut.</p>"
    )
    send_html_email(to_email=to_email, subject=subject, html_body=html, text_body=text)
