import uuid

from pydantic import BaseModel


class DraftReminderRequest(BaseModel):
    appointment_id: uuid.UUID
    tone: str | None = None
    custom_prompt: str | None = None


class DraftReminderResponse(BaseModel):
    message: str
