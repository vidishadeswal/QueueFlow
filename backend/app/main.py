from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.appointments import router as appointments_router
from app.api.auth import router as auth_router
from app.api.contacts import router as contacts_router
from app.api.reminders import router as reminders_router
from app.core.config import settings
from app.core.database import engine
from app.core.queue import queue_length
from app.core.redis import redis_client

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
