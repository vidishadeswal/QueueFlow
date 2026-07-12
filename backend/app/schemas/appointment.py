import uuid
from datetime import datetime

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    contact_id: uuid.UUID
    title: str
    scheduled_at: datetime
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None
    notes: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    title: str
    scheduled_at: datetime
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
