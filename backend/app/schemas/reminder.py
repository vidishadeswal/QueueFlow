import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.reminder import ReminderStatus


class ReminderCreate(BaseModel):
    appointment_id: uuid.UUID
    message: str
    send_at: datetime


class ReminderUpdate(BaseModel):
    message: str | None = None
    send_at: datetime | None = None
    status: ReminderStatus | None = None


class ReminderOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    contact_id: uuid.UUID
    message: str
    send_at: datetime
    status: ReminderStatus
    retry_count: int
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
