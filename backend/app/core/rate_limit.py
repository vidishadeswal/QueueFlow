from fastapi import HTTPException, Request, status

from app.core.redis import redis_client


def rate_limiter(prefix: str, limit: int, window_seconds: int):
    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{prefix}:{client_ip}"

        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window_seconds)

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return dependency
