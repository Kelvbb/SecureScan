"""Schémas user — squelette."""

from pydantic import BaseModel


class UserCreate(BaseModel):
    pass


class UserResponse(BaseModel):
    pass
