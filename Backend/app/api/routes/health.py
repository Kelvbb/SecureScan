"""Route health — squelette."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health_check():
    pass
