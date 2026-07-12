import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import async_session
from app.core.email import EmailSendError, send_reminder_email
from app.core.heartbeat import record_heartbeat
from app.core.queue import REMINDER_QUEUE_KEY
from app.core.redis import redis_client
from app.models import Business, Contact, Reminder
from app.models.reminder import ReminderStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


async def process_reminder(reminder_id: str) -> None:
    async with async_session() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        if reminder is None or reminder.status != ReminderStatus.queued:
            return

        contact = await session.get(Contact, reminder.contact_id)
        business = await session.get(Business, reminder.business_id)

        try:
            await send_reminder_email(
                to_email=contact.email,
                to_name=contact.name,
                subject=f"Reminder from {business.name}",
                message=reminder.message,
            )
            reminder.status = ReminderStatus.sent
            reminder.sent_at = datetime.now(timezone.utc)
            reminder.last_error = None
            logger.info("Sent reminder %s to %s", reminder_id, contact.email)
        except EmailSendError as exc:
            reminder.retry_count += 1
            reminder.last_error = str(exc)[:500]

            if reminder.retry_count > len(settings.retry_backoff_minutes):
                reminder.status = ReminderStatus.dead_letter
                logger.warning(
                    "Reminder %s moved to dead letter queue after %s attempts",
                    reminder_id,
                    reminder.retry_count,
                )
            else:
                backoff_minutes = settings.retry_backoff_minutes[reminder.retry_count - 1]
                reminder.status = ReminderStatus.pending
                reminder.send_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                logger.warning(
                    "Reminder %s failed (attempt %s), retrying in %s minute(s)",
                    reminder_id,
                    reminder.retry_count,
                    backoff_minutes,
                )

        await session.commit()


async def run_forever() -> None:
    logger.info("Worker started, waiting for jobs")
    while True:
        await record_heartbeat(redis_client)
        result = await redis_client.brpop(REMINDER_QUEUE_KEY, timeout=5)
        if result is None:
            continue
        _, reminder_id = result
        try:
            await process_reminder(reminder_id)
        except Exception:
            logger.exception("Unhandled error processing reminder %s", reminder_id)


if __name__ == "__main__":
    asyncio.run(run_forever())
