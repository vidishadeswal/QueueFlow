import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.queue import enqueue_reminder
from app.core.redis import redis_client
from app.models import Reminder
from app.models.reminder import ReminderStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scheduler")


async def dispatch_due_reminders() -> int:
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                select(Reminder)
                .where(Reminder.status == ReminderStatus.pending, Reminder.send_at <= datetime.now(timezone.utc))
                .with_for_update(skip_locked=True)
            )
            due_reminders = result.scalars().all()

            for reminder in due_reminders:
                await enqueue_reminder(redis_client, str(reminder.id))
                reminder.status = ReminderStatus.queued

        return len(due_reminders)


async def run_forever() -> None:
    logger.info("Scheduler started, polling every %ss", settings.scheduler_poll_interval_seconds)
    while True:
        try:
            count = await dispatch_due_reminders()
            if count:
                logger.info("Queued %s reminder(s)", count)
        except Exception:
            logger.exception("Error while dispatching reminders")
        await asyncio.sleep(settings.scheduler_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
