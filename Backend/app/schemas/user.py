from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "user"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
