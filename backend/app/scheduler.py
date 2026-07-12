import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.logging_config import configure_logging, get_logger
from app.core.metrics import COUNTER_REQUEUED_AFTER_TIMEOUT, increment
from app.core.queue import enqueue_reminder
from app.core.redis import redis_client
from app.models import Reminder
from app.models.reminder import ReminderStatus

configure_logging()
logger = get_logger("scheduler")


async def dispatch_due_reminders() -> int:
    # Commit the status='queued' transition to Postgres *before* publishing to
    # Redis. Publishing first (the original approach) lets a worker in another
    # process pop the job and look it up in Postgres before this transaction
    # commits -- it would still see status='pending', no-op via the guard clause
    # in worker.py, and the job is lost for good since its Redis entry is already
    # gone. Committing first guarantees the row is visible before any worker can
    # possibly see it.
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(Reminder)
                .where(Reminder.status == ReminderStatus.pending, Reminder.send_at <= datetime.now(timezone.utc))
                .with_for_update(skip_locked=True)
            )
            due_reminders = result.scalars().all()
            reminder_ids = [str(reminder.id) for reminder in due_reminders]

            for reminder in due_reminders:
                reminder.status = ReminderStatus.queued
                # claimed_at is left unset here on purpose: it marks when a worker
                # actually starts processing (set in worker.py), not when the job
                # entered the Redis queue. Otherwise jobs merely waiting their turn
                # behind a busy worker look identical to a crashed worker's
                # abandoned job, and the reaper below requeues them by mistake.

    for reminder_id in reminder_ids:
        await enqueue_reminder(redis_client, reminder_id)

    return len(reminder_ids)


async def reap_stuck_reminders() -> int:
    """Requeue reminders stuck in 'queued' past the visibility timeout.

    Covers the case where a worker claimed a job and crashed before finishing it —
    without this, that reminder would sit in 'queued' forever and never be retried.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.visibility_timeout_seconds)

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(Reminder)
                .where(Reminder.status == ReminderStatus.queued, Reminder.claimed_at < cutoff)
                .with_for_update(skip_locked=True)
            )
            stuck = result.scalars().all()

            for reminder in stuck:
                reminder.status = ReminderStatus.pending
                reminder.claimed_at = None

        return len(stuck)


async def run_forever() -> None:
    logger.info(
        "scheduler_started",
        extra={"poll_interval_seconds": settings.scheduler_poll_interval_seconds},
    )
    while True:
        try:
            count = await dispatch_due_reminders()
            if count:
                logger.info("reminders_queued", extra={"count": count})

            reaped = await reap_stuck_reminders()
            if reaped:
                for _ in range(reaped):
                    await increment(redis_client, COUNTER_REQUEUED_AFTER_TIMEOUT)
                logger.warning(
                    "reminders_reaped_after_timeout",
                    extra={"count": reaped, "visibility_timeout_seconds": settings.visibility_timeout_seconds},
                )
        except Exception:
            logger.exception("scheduler_loop_error")
        await asyncio.sleep(settings.scheduler_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
