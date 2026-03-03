"""Routes owasp — squelette."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter()


@router.get("")
def list_owasp_categories(db: Session = Depends(get_db)):
    pass
