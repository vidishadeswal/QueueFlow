import time
from contextlib import asynccontextmanager

from redis.asyncio import Redis

COUNTER_SENT = "metrics:reminders_sent_total"
COUNTER_FAILED = "metrics:reminders_failed_total"
COUNTER_DEAD_LETTERED = "metrics:reminders_dead_lettered_total"
COUNTER_REQUEUED_AFTER_TIMEOUT = "metrics:reminders_requeued_after_timeout_total"
LATENCY_SAMPLES_KEY = "metrics:send_latency_ms_samples"
MAX_LATENCY_SAMPLES = 1000


async def increment(redis: Redis, key: str) -> None:
    await redis.incr(key)


async def record_send_latency(redis: Redis, duration_ms: float) -> None:
    async with redis.pipeline(transaction=True) as pipe:
        pipe.lpush(LATENCY_SAMPLES_KEY, duration_ms)
        pipe.ltrim(LATENCY_SAMPLES_KEY, 0, MAX_LATENCY_SAMPLES - 1)
        await pipe.execute()


@asynccontextmanager
async def track_send_latency(redis: Redis):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        await record_send_latency(redis, duration_ms)


def percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


async def get_counters(redis: Redis) -> dict[str, int]:
    keys = [COUNTER_SENT, COUNTER_FAILED, COUNTER_DEAD_LETTERED, COUNTER_REQUEUED_AFTER_TIMEOUT]
    values = await redis.mget(keys)
    return {key: int(value) if value else 0 for key, value in zip(keys, values)}


async def get_latency_percentiles(redis: Redis) -> dict[str, float]:
    raw = await redis.lrange(LATENCY_SAMPLES_KEY, 0, -1)
    samples = sorted(float(v) for v in raw)
    return {
        "p50_ms": round(percentile(samples, 50), 2),
        "p95_ms": round(percentile(samples, 95), 2),
        "p99_ms": round(percentile(samples, 99), 2),
        "sample_count": len(samples),
    }
