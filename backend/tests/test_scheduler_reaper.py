import uuid
from datetime import datetime, timedelta, timezone

import app.scheduler as scheduler_module
from app.models.reminder import Reminder, ReminderStatus
from tests.conftest import TestSession
from tests.test_reminders import create_appointment, register_business


async def test_dispatch_leaves_claimed_at_unset_when_queueing(client, monkeypatch):
    monkeypatch.setattr(scheduler_module, "async_session", TestSession)

    token = await register_business(client, "reaper1@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2020-01-01T00:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    count = await scheduler_module.dispatch_due_reminders()
    assert count == 1

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.queued
        # claimed_at is set by the worker when it actually starts processing, not by
        # the scheduler when it queues the job -- see worker.py.
        assert reminder.claimed_at is None


async def test_reaper_ignores_queued_reminders_not_yet_claimed_by_a_worker(client, monkeypatch):
    """A job sitting in Redis waiting for a free worker is not a crash -- it's normal
    backpressure -- so the reaper must not touch it no matter how long it waits."""
    monkeypatch.setattr(scheduler_module, "async_session", TestSession)

    token = await register_business(client, "reaper4@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T00:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        reminder.claimed_at = None
        await session.commit()

    reaped = await scheduler_module.reap_stuck_reminders()
    assert reaped == 0

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.queued


async def test_reaper_requeues_stuck_reminder_past_visibility_timeout(client, monkeypatch):
    monkeypatch.setattr(scheduler_module, "async_session", TestSession)

    token = await register_business(client, "reaper2@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T00:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    # Simulate a worker that claimed the job and then crashed before finishing it.
    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        reminder.claimed_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await session.commit()

    reaped = await scheduler_module.reap_stuck_reminders()
    assert reaped == 1

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.pending
        assert reminder.claimed_at is None


async def test_reaper_leaves_freshly_claimed_reminders_alone(client, monkeypatch):
    monkeypatch.setattr(scheduler_module, "async_session", TestSession)

    token = await register_business(client, "reaper3@testbiz.com")
    headers = {"Authorization": f"Bearer {token}"}
    appointment_id = await create_appointment(client, token)

    created = await client.post(
        "/reminders",
        json={"appointment_id": appointment_id, "message": "test", "send_at": "2030-01-01T00:00:00Z"},
        headers=headers,
    )
    reminder_id = created.json()["id"]

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        reminder.status = ReminderStatus.queued
        reminder.claimed_at = datetime.now(timezone.utc)
        await session.commit()

    reaped = await scheduler_module.reap_stuck_reminders()
    assert reaped == 0

    async with TestSession() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        assert reminder.status == ReminderStatus.queued
