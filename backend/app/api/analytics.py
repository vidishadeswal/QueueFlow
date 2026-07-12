from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_business
from app.core.database import get_db
from app.core.heartbeat import is_worker_healthy
from app.core.queue import queue_length
from app.core.redis import redis_client
from app.models.business import Business
from app.models.reminder import Reminder, ReminderStatus
from app.schemas.analytics import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    now = datetime.now(timezone.utc)
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

    counts = (
        await db.execute(
            select(
                func.count(case((Reminder.send_at.between(today_start, today_end), 1))),
                func.count(case((Reminder.status == ReminderStatus.failed, 1))),
                func.count(case((Reminder.status == ReminderStatus.dead_letter, 1))),
                func.count(
                    case((and_(Reminder.status == ReminderStatus.pending, Reminder.send_at > now), 1))
                ),
                func.count(case((Reminder.status == ReminderStatus.sent, 1))),
                func.avg(Reminder.retry_count),
            ).where(Reminder.business_id == business.id)
        )
    ).one()

    today_reminders, failed_reminders, dead_letter_reminders, upcoming_reminders, sent_reminders, avg_retry_count = counts

    terminal_total = sent_reminders + failed_reminders + dead_letter_reminders
    delivery_rate = (sent_reminders / terminal_total * 100) if terminal_total > 0 else None

    return AnalyticsSummary(
        today_reminders=today_reminders,
        failed_reminders=failed_reminders,
        dead_letter_reminders=dead_letter_reminders,
        upcoming_reminders=upcoming_reminders,
        delivery_rate=round(delivery_rate, 1) if delivery_rate is not None else None,
        avg_retry_count=round(float(avg_retry_count or 0), 2),
        queue_size=await queue_length(redis_client),
        worker_healthy=await is_worker_healthy(redis_client),
    )
