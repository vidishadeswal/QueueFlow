import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contacts import get_owned_contact
from app.api.deps import get_current_business
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.business import Business
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def get_owned_appointment(appointment_id: uuid.UUID, db: AsyncSession, business: Business) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None or appointment.business_id != business.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    await get_owned_contact(payload.contact_id, db, business)

    appointment = Appointment(business_id=business.id, **payload.model_dump())
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    result = await db.scalars(
        select(Appointment).where(Appointment.business_id == business.id).order_by(Appointment.scheduled_at)
    )
    return list(result)


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    return await get_owned_appointment(appointment_id, db, business)


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    appointment = await get_owned_appointment(appointment_id, db, business)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    appointment = await get_owned_appointment(appointment_id, db, business)
    await db.delete(appointment)
    await db.commit()
