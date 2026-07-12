import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class BusinessCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class BusinessOut(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
