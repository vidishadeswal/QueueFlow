import asyncio
import random

import httpx

from app.core.config import settings
from app.core.delivery import DeliverySendError

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSendError(DeliverySendError):
    pass


async def send_reminder_email(to_email: str, to_name: str, subject: str, message: str) -> None:
    if settings.email_dry_run:
        # Simulates network latency without calling Brevo or spending real send quota.
        # Used for load testing the queue/worker/DB pipeline in isolation.
        await asyncio.sleep(random.uniform(0.02, 0.08))
        return

    if not settings.brevo_api_key or not settings.brevo_sender_email:
        raise EmailSendError("Brevo credentials are not configured")

    payload = {
        "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": f"<p>{message}</p>",
    }
    headers = {"api-key": settings.brevo_api_key, "content-type": "application/json"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(BREVO_SEND_URL, json=payload, headers=headers)

    if response.status_code >= 400:
        raise EmailSendError(f"Brevo returned {response.status_code}: {response.text}")
