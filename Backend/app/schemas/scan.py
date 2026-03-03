"""Schémas scan."""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class ScanCreate(BaseModel):
    user_id: UUID
    repository_url: str | None = None
    upload_path: str | None = None
    language: str | None = None


class ScanResponse(BaseModel):
    id: UUID
    user_id: UUID
    repository_url: str | None = None
    upload_path: str | None = None
    language: str | None = None
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScanList(BaseModel):
    id: UUID
    user_id: UUID
    repository_url: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
