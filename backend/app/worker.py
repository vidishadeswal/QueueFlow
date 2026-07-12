import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import async_session
from app.core.email import EmailSendError, send_reminder_email
from app.core.heartbeat import record_heartbeat
from app.core.logging_config import configure_logging, get_logger
from app.core.metrics import (
    COUNTER_DEAD_LETTERED,
    COUNTER_FAILED,
    COUNTER_SENT,
    increment,
    track_send_latency,
)
from app.core.queue import REMINDER_QUEUE_KEY
from app.core.redis import redis_client
from app.models import Business, Contact, Reminder
from app.models.reminder import ReminderStatus

configure_logging()
logger = get_logger("worker")


async def process_reminder(reminder_id: str) -> None:
    async with async_session() as session:
        reminder = await session.get(Reminder, uuid.UUID(reminder_id))
        if reminder is None or reminder.status != ReminderStatus.queued:
            return

        contact = await session.get(Contact, reminder.contact_id)
        business = await session.get(Business, reminder.business_id)

        # Mark + commit before the send so a crash mid-send still leaves a claimed_at
        # for the reaper to find. This is the moment processing actually starts, as
        # opposed to when the scheduler merely queued the job in Redis.
        reminder.claimed_at = datetime.now(timezone.utc)
        await session.commit()

        try:
            async with track_send_latency(redis_client):
                await send_reminder_email(
                    to_email=contact.email,
                    to_name=contact.name,
                    subject=f"Reminder from {business.name}",
                    message=reminder.message,
                )
            reminder.status = ReminderStatus.sent
            reminder.sent_at = datetime.now(timezone.utc)
            reminder.last_error = None
            reminder.claimed_at = None
            await increment(redis_client, COUNTER_SENT)
            logger.info("reminder_sent", extra={"reminder_id": reminder_id, "contact_email": contact.email})
        except EmailSendError as exc:
            reminder.retry_count += 1
            reminder.last_error = str(exc)[:500]
            reminder.claimed_at = None

            if reminder.retry_count > len(settings.retry_backoff_minutes):
                reminder.status = ReminderStatus.dead_letter
                await increment(redis_client, COUNTER_DEAD_LETTERED)
                logger.warning(
                    "reminder_dead_lettered",
                    extra={"reminder_id": reminder_id, "attempts": reminder.retry_count},
                )
            else:
                backoff_minutes = settings.retry_backoff_minutes[reminder.retry_count - 1]
                reminder.status = ReminderStatus.pending
                reminder.send_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                await increment(redis_client, COUNTER_FAILED)
                logger.warning(
                    "reminder_send_failed",
                    extra={
                        "reminder_id": reminder_id,
                        "attempt": reminder.retry_count,
                        "retry_in_minutes": backoff_minutes,
                    },
                )

        await session.commit()


async def run_forever() -> None:
    logger.info("worker_started")
    while True:
        await record_heartbeat(redis_client)
        result = await redis_client.brpop(REMINDER_QUEUE_KEY, timeout=5)
        if result is None:
            continue
        _, reminder_id = result
        try:
            await process_reminder(reminder_id)
        except Exception:
            logger.exception("worker_unhandled_error", extra={"reminder_id": reminder_id})


if __name__ == "__main__":
    asyncio.run(run_forever())
