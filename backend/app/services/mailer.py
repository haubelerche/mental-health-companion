from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MailerError(RuntimeError):
    pass


def _require_smtp_config() -> tuple[str, int, str, str, str, str, bool, bool]:
    settings = get_settings()
    host = settings.smtp_host.strip()
    username = settings.smtp_username.strip()
    password = settings.smtp_password
    from_email = settings.smtp_from_email.strip()
    from_name = settings.smtp_from_name.strip() or "Serene"
    if not host or not from_email:
        raise MailerError("SMTP chưa được cấu hình đầy đủ")
    return (
        host,
        settings.smtp_port,
        username,
        password,
        from_email,
        from_name,
        settings.smtp_starttls,
        settings.smtp_use_ssl,
    )


def send_html_email(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    host, port, username, password, from_email, from_name, starttls, use_ssl = _require_smtp_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            logger.debug(f"Sending email via SMTP_SSL to {to_email} (host={host}:{port})")
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
            logger.info(f"Email sent successfully to {to_email}")
            return

        logger.debug(f"Sending email via SMTP to {to_email} (host={host}:{port}, starttls={starttls})")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            if starttls:
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        logger.info(f"Email sent successfully to {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        logger.exception(f"SMTP auth failed for {username}@{host}:{port}: {e}")
        raise MailerError(f"SMTP authentication failed: {e}")
    except smtplib.SMTPException as e:
        logger.exception(f"SMTP error sending email to {to_email}: {e}")
        raise MailerError(f"SMTP error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error sending email to {to_email}: {e}")
        raise MailerError(f"Email delivery failed: {e}")
