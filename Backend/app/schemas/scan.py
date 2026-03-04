"""Schémas scan."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ScanCreate(BaseModel):
    repository_url: str | None = None
    upload_path: str | None = None
    language: str | None = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    repository_url: str | None = None
    upload_path: str | None = None
    language: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ScanList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
