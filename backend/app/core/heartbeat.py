from redis.asyncio import Redis

WORKER_HEARTBEAT_KEY = "worker:heartbeat"
HEARTBEAT_TTL_SECONDS = 30


async def record_heartbeat(redis: Redis) -> None:
    await redis.set(WORKER_HEARTBEAT_KEY, "1", ex=HEARTBEAT_TTL_SECONDS)


async def is_worker_healthy(redis: Redis) -> bool:
    return await redis.exists(WORKER_HEARTBEAT_KEY) == 1
