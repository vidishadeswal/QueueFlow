from redis.asyncio import Redis

REMINDER_QUEUE_KEY = "reminders:queue"


async def enqueue_reminder(redis: Redis, reminder_id: str) -> None:
    await redis.lpush(REMINDER_QUEUE_KEY, reminder_id)


async def queue_length(redis: Redis) -> int:
    return await redis.llen(REMINDER_QUEUE_KEY)
