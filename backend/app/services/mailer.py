import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("uvicorn.error")


def send_email(to: str, subject: str, body: str) -> None:
    """Send an email. With MAIL_BACKEND=console the message is printed to the API log instead."""
    if settings.mail_backend != "smtp":
        log.info("EMAIL (console backend)\n  to: %s\n  subject: %s\n\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
