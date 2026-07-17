from redis.asyncio import Redis

IDEMPOTENCY_KEY_PREFIX = "idempotency:"
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60
PROCESSING_SENTINEL = "processing"


class IdempotencyConflict(Exception):
    pass


def _redis_key(business_id, key: str) -> str:
    return f"{IDEMPOTENCY_KEY_PREFIX}{business_id}:{key}"


async def claim_idempotency_key(redis: Redis, business_id, key: str) -> str | None:
    """Atomically claims `key` for this business. Returns None if newly claimed
    (caller should proceed), or the previously-stored reminder id if this key
    already completed. Raises IdempotencyConflict if another request with the
    same key is still being processed."""
    redis_key = _redis_key(business_id, key)
    claimed = await redis.set(redis_key, PROCESSING_SENTINEL, nx=True, ex=IDEMPOTENCY_TTL_SECONDS)
    if claimed:
        return None

    existing = await redis.get(redis_key)
    if existing == PROCESSING_SENTINEL:
        raise IdempotencyConflict()
    return existing


async def complete_idempotency_key(redis: Redis, business_id, key: str, reminder_id: str) -> None:
    await redis.set(_redis_key(business_id, key), reminder_id, ex=IDEMPOTENCY_TTL_SECONDS)


async def release_idempotency_key(redis: Redis, business_id, key: str) -> None:
    await redis.delete(_redis_key(business_id, key))
