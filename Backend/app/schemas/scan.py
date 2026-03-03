"""Schémas scan."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScanCreate(BaseModel):
    pass


class ScanResponse(BaseModel):
    pass


class ScanList(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
