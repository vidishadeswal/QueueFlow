from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.appointments import router as appointments_router
from app.api.auth import router as auth_router
from app.api.contacts import router as contacts_router
from app.api.reminders import router as reminders_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging_config import configure_logging
from app.core.metrics import get_counters, get_latency_percentiles
from app.core.queue import queue_length
from app.core.redis import redis_client

configure_logging()

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(contacts_router)
app.include_router(appointments_router)
app.include_router(reminders_router)
app.include_router(analytics_router)
app.include_router(ai_router)


@app.get("/health")
async def health():
    status = {"database": "down", "redis": "down"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["database"] = "up"
    except Exception:
        pass

    try:
        await redis_client.ping()
        status["redis"] = "up"
    except Exception:
        pass

    return status


@app.get("/queue/status")
async def queue_status():
    return {"queue_size": await queue_length(redis_client)}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    counters = await get_counters(redis_client)
    latency = await get_latency_percentiles(redis_client)
    queue_size = await queue_length(redis_client)

    lines = [
        "# HELP queueflow_reminders_sent_total Reminders successfully sent",
        "# TYPE queueflow_reminders_sent_total counter",
        f"queueflow_reminders_sent_total {counters['metrics:reminders_sent_total']}",
        "# HELP queueflow_reminders_failed_total Reminder send attempts that failed (before terminal state)",
        "# TYPE queueflow_reminders_failed_total counter",
        f"queueflow_reminders_failed_total {counters['metrics:reminders_failed_total']}",
        "# HELP queueflow_reminders_dead_lettered_total Reminders moved to the dead letter queue",
        "# TYPE queueflow_reminders_dead_lettered_total counter",
        f"queueflow_reminders_dead_lettered_total {counters['metrics:reminders_dead_lettered_total']}",
        "# HELP queueflow_reminders_requeued_after_timeout_total Reminders requeued after a worker "
        "stopped responding (visibility timeout)",
        "# TYPE queueflow_reminders_requeued_after_timeout_total counter",
        f"queueflow_reminders_requeued_after_timeout_total {counters['metrics:reminders_requeued_after_timeout_total']}",
        "# HELP queueflow_queue_size Current number of jobs waiting in the Redis queue",
        "# TYPE queueflow_queue_size gauge",
        f"queueflow_queue_size {queue_size}",
        "# HELP queueflow_send_latency_ms Email send latency in milliseconds (last "
        f"{latency['sample_count']} samples)",
        "# TYPE queueflow_send_latency_ms summary",
        f'queueflow_send_latency_ms{{quantile="0.5"}} {latency["p50_ms"]}',
        f'queueflow_send_latency_ms{{quantile="0.95"}} {latency["p95_ms"]}',
        f'queueflow_send_latency_ms{{quantile="0.99"}} {latency["p99_ms"]}',
    ]
    return "\n".join(lines) + "\n"
