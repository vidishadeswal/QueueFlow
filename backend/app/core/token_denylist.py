from redis.asyncio import Redis

DENYLIST_PREFIX = "revoked_token:"


async def revoke_token(redis: Redis, jti: str, ttl_seconds: int) -> None:
    if ttl_seconds > 0:
        await redis.set(f"{DENYLIST_PREFIX}{jti}", "1", ex=ttl_seconds)


async def is_token_revoked(redis: Redis, jti: str) -> bool:
    return await redis.exists(f"{DENYLIST_PREFIX}{jti}") == 1
