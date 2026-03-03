"""Schémas scan."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScanCreate(BaseModel):
    pass


class ScanResponse(BaseModel):
    pass


class ScanList(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
