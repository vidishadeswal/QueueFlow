import httpx

from app.core.delivery import DeliverySendError


class WebhookSendError(DeliverySendError):
    pass


async def send_reminder_webhook(
    webhook_url: str,
    reminder_id: str,
    business_name: str,
    contact_name: str,
    contact_email: str,
    message: str,
) -> None:
    if not webhook_url:
        raise WebhookSendError("Business has no webhook_url configured")

    payload = {
        "event": "reminder.due",
        "reminder_id": reminder_id,
        "business_name": business_name,
        "contact": {"name": contact_name, "email": contact_email},
        "message": message,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook_url, json=payload)
    except httpx.HTTPError as exc:
        raise WebhookSendError(f"Could not reach webhook: {exc}") from exc

    if response.status_code >= 400:
        raise WebhookSendError(f"Webhook returned {response.status_code}: {response.text[:200]}")
