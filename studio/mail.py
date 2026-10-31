"""Email backend that sends through Brevo's HTTP API.

Render's free plan blocks SMTP ports, so normal Gmail SMTP can't be used
there. Every Django email (bookings, password resets, invites) goes through
this backend when BREVO_API_KEY is set.
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except (urllib.error.URLError, OSError, ValueError) as exc:
                log.warning("Brevo email to %s failed: %s", message.to, exc)
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        name, address = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        payload = {
            "sender": {"name": name or settings.SITE_NAME, "email": address},
            "to": [{"email": a} for a in message.to],
            "subject": message.subject,
            "textContent": message.body,
        }
        if message.cc:
            payload["cc"] = [{"email": a} for a in message.cc]
        if message.bcc:
            payload["bcc"] = [{"email": a} for a in message.bcc]
        if message.reply_to:
            payload["replyTo"] = {"email": parseaddr(message.reply_to[0])[1]}
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["htmlContent"] = content
        request = urllib.request.Request(
            BREVO_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
            if not 200 <= response.status < 300:
                raise ValueError(f"Brevo answered {response.status}")
