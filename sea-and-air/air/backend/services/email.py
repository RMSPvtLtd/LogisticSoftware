"""Emails a rendered quote/invoice PDF to a customer via Resend's REST API
(https://resend.com/docs/api-reference/emails/send-email) -- a single POST,
no SMTP setup. Optional and feature-gated: with no RESEND_API_KEY configured
(config.Settings.resend_api_key), `send_pdf_email` raises EmailNotConfigured
rather than the app refusing to boot -- every other route works fine without
it. See api/quotes.py::email / api/invoices.py::email for the two callers.
"""

import base64

import httpx

from config import get_settings
from utils.errors import EmailNotConfigured, EmailSendFailed

_RESEND_URL = "https://api.resend.com/emails"


def send_pdf_email(*, to_email: str, subject: str, body_text: str, pdf_bytes: bytes, pdf_filename: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise EmailNotConfigured("Email is not configured for this deployment.")

    try:
        response = httpx.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.resend_from_email,
                "to": [to_email],
                "subject": subject,
                "text": body_text,
                "attachments": [
                    {"filename": pdf_filename, "content": base64.b64encode(pdf_bytes).decode("ascii")}
                ],
            },
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Resend's error body names the actual rejection reason (bad
        # sender domain, invalid recipient, ...) -- worth surfacing, but
        # never the raw response verbatim in case it ever echoes back
        # anything sensitive from the request.
        raise EmailSendFailed(f"The email provider rejected the request ({exc.response.status_code}).") from exc
    except httpx.RequestError as exc:
        raise EmailSendFailed("Could not reach the email provider.") from exc
