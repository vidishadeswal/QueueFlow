import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.appointments import get_owned_appointment
from app.api.deps import get_current_business
from app.core.database import get_db
from app.core.idempotency import IdempotencyConflict, claim_idempotency_key, complete_idempotency_key, release_idempotency_key
from app.core.redis import redis_client
from app.models.business import Business
from app.models.reminder import Reminder, ReminderStatus
from app.schemas.pagination import Page
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])


async def get_owned_reminder(reminder_id: uuid.UUID, db: AsyncSession, business: Business) -> Reminder:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None or reminder.business_id != business.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    if idempotency_key:
        try:
            cached_id = await claim_idempotency_key(redis_client, business.id, idempotency_key)
        except IdempotencyConflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A request with this Idempotency-Key is already being processed",
            )
        if cached_id is not None:
            return await get_owned_reminder(uuid.UUID(cached_id), db, business)

    try:
        appointment = await get_owned_appointment(payload.appointment_id, db, business)
        reminder = Reminder(
            business_id=business.id,
            contact_id=appointment.contact_id,
            **payload.model_dump(),
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
    except Exception:
        if idempotency_key:
            await release_idempotency_key(redis_client, business.id, idempotency_key)
        raise

    if idempotency_key:
        await complete_idempotency_key(redis_client, business.id, idempotency_key, str(reminder.id))

    return reminder


@router.get("", response_model=Page[ReminderOut])
async def list_reminders(
    status_filter: ReminderStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    base_query = select(Reminder).where(Reminder.business_id == business.id)
    if status_filter is not None:
        base_query = base_query.where(Reminder.status == status_filter)
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    result = await db.scalars(base_query.order_by(Reminder.send_at).limit(limit).offset(offset))
    return Page(items=list(result), total=total, limit=limit, offset=offset)


@router.get("/{reminder_id}", response_model=ReminderOut)
async def get_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    return await get_owned_reminder(reminder_id, db, business)


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    reminder = await get_owned_reminder(reminder_id, db, business)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.post("/{reminder_id}/retry", response_model=ReminderOut)
async def retry_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    reminder = await get_owned_reminder(reminder_id, db, business)
    if reminder.status != ReminderStatus.dead_letter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only dead-lettered reminders can be manually retried",
        )

    reminder.status = ReminderStatus.pending
    reminder.retry_count = 0
    reminder.last_error = None
    reminder.send_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    reminder = await get_owned_reminder(reminder_id, db, business)
    await db.delete(reminder)
    await db.commit()
