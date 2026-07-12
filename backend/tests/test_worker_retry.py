import uuid
from unittest.mock import AsyncMock, patch

import app.worker as worker_module
from app.core.email import EmailSendError
from app.models.reminder import Reminder, ReminderStatus
from tests.conftest import TestSession
from tests.test_reminders import create_appointment, register_business


async def test_worker_retries_with_backoff_then_dead_letters(client, monkeypatch):
    monkeypatch.setattr(worker_module, "async_session", TestSession)

    token = await register_business(client, "worker1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    with patch.object(worker_module, "send_reminder_email", new=AsyncMock(side_effect=EmailSendError("boom"))):
        expected = [
            (1, ReminderStatus.pending, 1),
            (2, ReminderStatus.pending, 5),
            (3, ReminderStatus.pending, 15),
            (4, ReminderStatus.dead_letter, None),
        ]

        for attempt, expected_status, _backoff_minutes in expected:
            async with TestSession() as session:
                reminder = await session.get(Reminder, uuid.UUID(reminder_id))
                reminder.status = ReminderStatus.queued
                await session.commit()

            await worker_module.process_reminder(reminder_id)

            async with TestSession() as session:
                reminder = await session.get(Reminder, uuid.UUID(reminder_id))
                assert reminder.status == expected_status, f"attempt {attempt}"
                assert reminder.retry_count == attempt


async def test_worker_marks_sent_on_success(client, monkeypatch):
    monkeypatch.setattr(worker_module, "async_session", TestSession)

    token = await register_business(client, "worker2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T09:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        await session.commit()

    with patch.object(worker_module, "send_reminder_email", new=AsyncMock(return_value=None)):
        await worker_module.process_reminder(reminder_id)

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.sent
        assert reminder.sent_at is not None
