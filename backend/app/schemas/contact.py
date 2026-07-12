import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class ContactOut(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    phone: str | None
    created_at: datetime

    class Config:
        from_attributes = True
