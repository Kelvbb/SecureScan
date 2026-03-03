"""Routes users — squelette."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    pass


@router.get("/{user_id}")
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    pass
