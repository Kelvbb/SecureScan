from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ScanCreate(BaseModel):
    repository_url: str | None = None
    upload_path: str | None = None
    user_id: UUID


class ScanResponse(BaseModel):
    id: UUID
    user_id: UUID
    repository_url: str | None
    upload_path: str | None
    language: str | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanList(BaseModel):
    id: UUID
    status: str
    language: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
