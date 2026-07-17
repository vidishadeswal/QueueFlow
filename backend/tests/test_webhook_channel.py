import uuid
from unittest.mock import AsyncMock, patch

import app.worker as worker_module
from app.core.webhook import WebhookSendError
from app.models.reminder import Reminder, ReminderStatus
from tests.conftest import TestSession
from tests.test_reminders import create_appointment, register_business


async def test_webhook_reminder_rejected_without_webhook_url_configured(client):
    token = await register_business(client, "webhook1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    response = await client.post(
        "/reminders",
        json={
            "appointment_id": appointment_id,
            "message": "test",
            "send_at": "2030-01-01T09:00:00Z",
            "channel": "webhook",
        },
        headers=headers,
    )
    assert response.status_code == 400


async def test_webhook_url_must_look_like_a_url(client):
    token = await register_business(client, "webhook2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.patch("/auth/me", json={"webhook_url": "not-a-url"}, headers=headers)
    assert response.status_code == 400


async def test_configuring_webhook_url_enables_webhook_reminders(client):
    token = await register_business(client, "webhook3@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    settings_response = await client.patch(
        "/auth/me", json={"webhook_url": "https://example.com/hooks/queueflow"}, headers=headers
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["webhook_url"] == "https://example.com/hooks/queueflow"

    response = await client.post(
        "/reminders",
        json={
            "appointment_id": appointment_id,
            "message": "test",
            "send_at": "2030-01-01T09:00:00Z",
            "channel": "webhook",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["channel"] == "webhook"


async def test_worker_sends_webhook_reminder_via_business_webhook_url(client, monkeypatch):
    monkeypatch.setattr(worker_module, "async_session", TestSession)

    token = await register_business(client, "webhook4@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    await client.patch("/auth/me", json={"webhook_url": "https://example.com/hooks/queueflow"}, headers=headers)

    created = await client.post(
        "/reminders",
        json={
            "appointment_id": appointment_id,
            "message": "test",
            "send_at": "2030-01-01T09:00:00Z",
            "channel": "webhook",
        },
        headers=headers,
    )
    reminder_id = created.json()["id"]

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        await session.commit()

    mock_webhook = AsyncMock(return_value=None)
    with patch.object(worker_module, "send_reminder_webhook", new=mock_webhook):
        await worker_module.process_reminder(reminder_id)

    mock_webhook.assert_awaited_once()
    assert mock_webhook.call_args.kwargs["webhook_url"] == "https://example.com/hooks/queueflow"
    assert mock_webhook.call_args.kwargs["reminder_id"] == reminder_id

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.sent


async def test_worker_retries_failed_webhook_send_same_as_email(client, monkeypatch):
    monkeypatch.setattr(worker_module, "async_session", TestSession)

    token = await register_business(client, "webhook5@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    await client.patch("/auth/me", json={"webhook_url": "https://example.com/hooks/queueflow"}, headers=headers)

    created = await client.post(
        "/reminders",
        json={
            "appointment_id": appointment_id,
            "message": "test",
            "send_at": "2030-01-01T09:00:00Z",
            "channel": "webhook",
        },
        headers=headers,
    )
    reminder_id = created.json()["id"]

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        await session.commit()

    with patch.object(worker_module, "send_reminder_webhook", new=AsyncMock(side_effect=WebhookSendError("boom"))):
        await worker_module.process_reminder(reminder_id)

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.pending
        assert reminder.retry_count == 1
        assert "boom" in reminder.last_error
