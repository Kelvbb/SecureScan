"""Schémas utilisateur et auth."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Inscription : email + mot de passe (jamais stocké en clair)."""

    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    role: str = "user"


class UserLogin(BaseModel):
    """Connexion : email + mot de passe."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Réponse API : pas de mot de passe."""

    id: UUID
    email: str
    full_name: str | None
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
